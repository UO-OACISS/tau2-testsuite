#!/usr/bin/env python3

import sys
import os
import argparse
import string
import glob
# import profile_diff
import datetime
import json
import fnmatch
import re
#import cgi
import html
import configs
from tests import *
from subprocess import check_output
import subprocess
import shutil
import tempfile

errorsFound = 0
warningsFound = 0
spackEnv=""

# ---------------------------------------------------------------------------
# Profile comparison configuration
# ---------------------------------------------------------------------------

# Threshold (%) for cross-run timing comparison.  Differences above this
# level are reported as soft warnings.  Call count changes are always a hard
# error regardless of threshold.  200% is deliberately high: natural timing
# variance between runs on a loaded shared HPC machine can easily reach 50-100%,
# so a lower threshold produces far too many false warnings.
# Override at runtime with TAU_DIFF_TIMING_THRESHOLD=<float>.
_TIMING_THRESHOLD = float(os.environ.get("TAU_DIFF_TIMING_THRESHOLD", "200.0"))

# Threshold (%) for cross-builder (PDT vs CompInst vs LLVM vs SALT) timing
# comparison within a single run.  PDT instrumentation always adds measurable
# overhead relative to CompInst, so a high threshold avoids persistent false
# positives while still catching egregious regressions.
# Override at runtime with TAU_DIFF_BUILDER_THRESHOLD=<float>.
_BUILDER_THRESHOLD = float(os.environ.get("TAU_DIFF_BUILDER_THRESHOLD", "200.0"))

# Set TAU_UPDATE_BASELINE=1 to force a cache update even when the run had errors.
_FORCE_UPDATE_BASELINE = os.environ.get("TAU_UPDATE_BASELINE", "0").strip() == "1"

# Maximum number of function-diff entries printed per profile comparison.
# Prevents enormous HTML output for large GPU/MPI profiles with many EBS entries.
# Override with TAU_DIFF_MAX_DISPLAY=<int>.
_MAX_DIFF_DISPLAY = int(os.environ.get("TAU_DIFF_MAX_DISPLAY", "25"))

# Module-level cache for the lazily imported tau_diff module.
_tau_diff_module = None

# Enable profile value checking (cross-run baseline comparison, cross-builder
# comparison, and structural invariant checks).  Off by default so that
# unattended automatic runs are not flooded with expected false-positive warnings
# while baselines are still being established.  Set TAU_PROFILE_CHECKS=1, or
# pass --profile-checks to runtests.py, to enable.
_PROFILE_CHECKS = os.environ.get("TAU_PROFILE_CHECKS", "0").strip() == "1"

def printSysInfo(config):
    output("System Config")
    print(config.description)
    # system("env")
    system("hostname")
    system("date")
    system("uname -a")
    system("module list 2>&1", reportError=False)
    _seen_compilers = set()
    for _m in re.finditer(r'(?<![a-zA-Z0-9_])-(?:c\+\+|cc)=(\S+)', config.baseConfig):
        _cc = _m.group(1)
        if _cc not in _seen_compilers:
            _seen_compilers.add(_cc)
            system("which " + _cc, reportError=False)
            system(_cc + " --version", reportError=False)
    _f90m = re.search(r'-fortran=(\S+)', config.f90)
    if _f90m:
        _fc = _f90m.group(1)
        if _fc not in _seen_compilers:
            _seen_compilers.add(_fc)
            system("which " + _fc, reportError=False)
            system(_fc + " --version", reportError=False)
    system("which java")
    if config.f90 == "-fortran=intel":
        systemq("which ifort ; which ifc; which efc")
        systemq("which icc ; which icpc; which ecc ; which ecpc; which icx; which icpx")
        systemq("ifort -V")
        systemq("ifc -V")
        systemq("icc -V")
        systemq("icpc -V")
        systemq("ecc -V")
        systemq("ecpc -V")
        systemq("efc -V")
        systemq("icpx -V")
        systemq("icx -V")

def output(message, headerLevel="3", color="green"):
    if not hasattr(output, "linkDex"):
        output.linkDex = 0
    print("<h"+headerLevel+" id=\"anchor-"+str(output.linkDex)+"\"><font color="+color+">\n" +
          message + "\n</font></h"+headerLevel+">")
    output.linkDex+=1;

def error(message):
    global errorsFound
    errorsFound = errorsFound + 1
    # print "</pre><h1><font color=red>\n BLUNDER: " + message + "\n</font></h1><pre>";
#    print "<h1><font color=red>\n BLUNDER: " + message + "\n</font></h1>";
    output("FEHLER: "+message, "1", "red")

def outputHeader(message):
    output(message, "2", "blue")

def warning(message):
    global warningsFound
    warningsFound = warningsFound + 1
    # print "</pre><h3><font color=darkorange>\n BEWARE: " + message + "\n</font></h3><pre>";
    # print "<h3><font color=darkorange>\n BEWARE: " + message + "\n</font></h3>";
    output("BEWARE: "+message, "3", "darkorange")

def end(code):
    if (errorsFound == 0):
        outputHeader("No Errors!")
    else:
        output("Failure: Encountered %d errors" % errorsFound, "1", "red")
        

    if (warningsFound == 0):
        outputHeader("No Warnings!")
    else:
        warning("Caution: Encountered %d warnings" % warningsFound)
    print("</body>\n</html>\n")  # <PRE>
    sys.exit(errorsFound)

def usage():
    print("Usage: tau_regression.py <configuration> [run_root] [--tests DIR ...]")
    sys.exit(-1)

# System call. Command to be run. Timeout time. Enclose output in details tags? Print error output?
def system(command, timeout=720, details=True, reportError=True, reportTime=True):
    detStart = ""
    detMid = ""
    detEnd = ""
    timeoutStart = ""
    timeCmd = ""
    if(details):
        detStart = "<details><summary>"
        detMid = "</summary>"
        detEnd = "</details>"
    if(timeout > 0):
        timeoutStart = "timeout -s 3 "+str(timeout)+" "
    if(reportTime):
        timeCmd = " time "
    print(detStart+"<b>" + html.escape(os.getcwd() +
                                      "> " + command) + "</b>"+detMid+"<pre>")
    #print(timeCmd+timeoutStart+command)								
    sys.stdout.flush()
    retval = os.system(spackEnv+timeCmd+timeoutStart+command)
    #retval = os.system(command)
    print("</pre>"+detEnd)
    if(reportError):
        if (retval/256 == 124):
            error(command + " timed out ("+str(timeout/60)+" minutes)!")
        elif (retval != 0):
            error(command + " failed! ("+str(retval)+")")
    return retval

# 2 minute system call
def system2Min(command):
    return system(command, 180)

# Quiet system call
def systemq(command):
    return system(command, 0, False, False, False)

# TODO: Must make ebs and tracing mutually exclusive
def getEnvString(config):
    envString = ''
    if not config.passEnv:
        return envString

    # Keep envVars and envVarsExport distinct:
    #   - envVars: static per-config defaults
    #   - envVarsExport: runtime-tracked vars set/unset during test execution
    # For launcher --env forwarding, include both with runtime values taking precedence.
    export_map = dict(getattr(config, 'envVars', {}))
    for x in config.envVarsExport:
        if x in os.environ:
            export_map[x] = os.environ[x]

    for key, value in export_map.items():
        envString += '\'' + str(key) + '=' + str(value) + '\'' + ':'
    return envString

def executeSequential(command, config):
    envString = getEnvString(config)
    if (envString):
        retval = system2Min("time "+config.seqBefore + " --env " +
                            envString + " " + command + " " + config.seqAfter)
    else:
        retval = system2Min("time "+config.seqBefore + " " +
                            command + " " + config.seqAfter)
    return retval

def executeMpi(command, config):
    envString = getEnvString(config)
    # systemq("env")
    if (envString):
        retval = system2Min("time "+config.mpiBefore + " --env " +
                            envString + " " + command + " " + config.mpiAfter)
    else:
        retval = system2Min("time "+config.mpiBefore + " " +
                            command + " " + config.mpiAfter)
    return retval

def chdir(directory):
    print("<b><pre>" + os.getcwd() + "> cd " + directory + "</pre></b>")
    if os.path.exists(directory) and os.path.isdir(directory):
        os.chdir(directory)
        return 0
    error(directory + " not found!")
    return -1

def prependVar(var, directory, config):
    print("<b><pre>" + os.getcwd() + "> " + var +
          "=" + directory + ":$" + var + "</pre></b>")
    env = os.getenv(var)
    config.envVarsExport.add(var)
    if env is not None:
        os.environ[var] = directory + os.pathsep + os.environ[var]
    else:
        os.environ[var] = directory

def prependPath(directory, config):
    print("<b><pre>" + os.getcwd() + "> PATH=" + directory + ":$PATH</pre></b>")
    config.envVarsExport.add("PATH")
    os.environ['PATH'] = directory + os.pathsep + os.environ['PATH']


def applyConfigEnvironment(config):
    """Apply static config.envVars once for the full regression run."""
    env_map = getattr(config, "envVars", {})
    if not env_map:
        return
    print("<details><summary><b>Applying config.envVars</b></summary>")
    for key, value in env_map.items():
        # Use setEnviron so values are visible in HTML and tracked for launcher forwarding.
        setEnviron(str(key), str(value), config)
    print("</details>")


def _get_tau_makefile_path():
    """Return the active TAU_MAKEFILE path when it is set and readable."""
    tau_makefile = os.environ.get(TAUMAKE, "")
    if tau_makefile == "":
        warning("Cannot resolve TAU makefile value: TAU_MAKEFILE is unset")
        return ""
    if not os.path.isfile(tau_makefile):
        warning("Cannot resolve TAU makefile value: missing TAU_MAKEFILE " + tau_makefile)
        return ""
    return tau_makefile


def _strip_makefile_inline_comment(text):
    """Strip inline comments from a makefile assignment value."""
    return re.sub(r'(?<!\\)#.*$', '', text).strip()


def _read_tau_makefile_value(var_name, tau_makefile):
    """Return the final assigned value for var_name from TAU_MAKEFILE.

    Supports '=', ':=', '?=' and '+=' operators and strips trailing comments
    like '#ENDIF##PROFILE#' from assignment values.
    """
    assign_re = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*([:+?]?=)\s*(.*?)\s*$')
    values = {}
    try:
        with open(tau_makefile, "r") as mf:
            for raw in mf:
                line = raw.rstrip('\n')
                if line.lstrip().startswith('#'):
                    continue
                m = assign_re.match(line)
                if not m:
                    continue
                name, op, rhs = m.group(1), m.group(2), _strip_makefile_inline_comment(m.group(3))
                if op == '+=':
                    old = values.get(name, "")
                    values[name] = (old + " " + rhs).strip() if old else rhs
                elif op == '?=':
                    if name not in values or values[name] == "":
                        values[name] = rhs
                else:
                    values[name] = rhs
    except Exception:
        return ""
    return values.get(var_name, "")


def _resolve_tau_python_bindings_dir():
    """Resolve <lib>/bindings-$TAU_CONFIG from the active TAU_MAKEFILE."""
    tau_makefile = _get_tau_makefile_path()
    if tau_makefile == "":
        return ""

    tau_config = _read_tau_makefile_value("TAU_CONFIG", tau_makefile)
    if tau_config == "":
        makefile_name = os.path.basename(tau_makefile)
        if makefile_name.startswith("Makefile.tau-"):
            tau_config = makefile_name[len("Makefile.tau-"):]

    if tau_config == "":
        warning("Cannot resolve TAU Python bindings: TAU_CONFIG not found in " + tau_makefile)
        return ""

    bindings_dir = os.path.join(os.path.dirname(tau_makefile), "bindings" + tau_config)
    if not os.path.isdir(bindings_dir):
        warning("Resolved TAU Python bindings directory does not exist: " + bindings_dir)
    return bindings_dir


def _resolve_dynamic_test_env_value(raw_val, tau_makefile):
    """Resolve special environment tokens used in TestApp.testEnv values.

    Supported formats:
      @@TAU_MAKEFILE:BINDINGS_DIR@@ -> <lib>/bindings-$TAU_CONFIG
      @@TAU_MAKEFILE:VARNAME@@      -> value of VARNAME in TAU_MAKEFILE
    """
    if raw_val.startswith(TAU_DYNAMIC_TOK_PREFIX) and raw_val.endswith(TAU_DYNAMIC_TOK_SUFFIX):
        var_name = raw_val[len(TAU_DYNAMIC_TOK_PREFIX):-len(TAU_DYNAMIC_TOK_SUFFIX)].strip()
        if var_name == "":
            warning("Ignoring empty TAU makefile token in testEnv")
            return ""
        if var_name == "BINDINGS_DIR":
            return _resolve_tau_python_bindings_dir()
        resolved = _read_tau_makefile_value(var_name, tau_makefile)
        if resolved == "":
            warning("TAU makefile variable not found or empty: " + var_name)
        return resolved

    return raw_val


def resolveTestEnvironment(tauTest):
    """Return test-specific environment vars resolved for the current run context."""
    env_map = getattr(tauTest, "testEnv", {})
    if not env_map:
        return {}
    if not isinstance(env_map, dict):
        warning("Ignoring non-dict testEnv for test " + tauTest.buildDir)
        return {}

    tau_makefile = _get_tau_makefile_path()
    if tau_makefile == "":
        return {}

    resolved = {}
    for var, val in env_map.items():
        resolved_val = _resolve_dynamic_test_env_value(str(val), tau_makefile)
        if resolved_val == "":
            continue
        if var == "PYTHONPATH":
            existing = os.environ.get(var, "")
            resolved[var] = resolved_val + (os.pathsep + existing if existing else "")
        else:
            resolved[var] = resolved_val
    return resolved

def buildTAU(config, options):
    output("Building TAU with " + options)
    cdres=chdir(TAU_ROOT)
    if cdres != 0:
        error("TAU_ROOT not found! Aborting!")
        return cdres
    # " " + "-DEBUGPROF" + " " + \ -DDEBUG_LOCK_PROBLEMS \ -DTAU_USE_FAST_THREADID
    retval = system("./configure " + config.baseConfig + " " +
                    config.f90 + " " + options + config.useropt, timeout=1200)
    if retval != 0:
        #error("Error: failed to configure!")
        return retval
    retval = system(config.tauMake + " clean install" + config.makeExtra)
    #system("rm ./"+config.arch+"/lib/libTAU.so")
    #if retval != 0:
        #error("Error: failed to build TAU!")
    return retval


def filter_buildapps(buildapps, test_names):
    """Return a filtered copy of buildapps restricted to the given buildDir names.

    Each TAUConfiguration's .tests list is replaced with only those TestApps
    whose buildDir appears in test_names.  TAUConfigurations with no surviving
    tests are dropped entirely, so their TAU build is also skipped.

    Passing None or an empty list returns buildapps unchanged.
    """
    if not test_names:
        return buildapps
    names = set(test_names)
    result = []
    for tauconf in buildapps:
        tauconf.tests = [t for t in tauconf.tests if t.buildDir in names]
        if tauconf.tests:
            result.append(tauconf)
    return result


def batchBuildTAU(config, testmap):
    if config.build_pdt == True and not os.path.isfile(TAU_ROOT+"/../pdtoolkit/no-build"):
        output("Building pdtoolkit")
        cdres = chdir(TAU_ROOT+"/../pdtoolkit")
        if(cdres != 0):
            error("PDT directory not found! Skipping all TAU builds!")
            return testmap
        retval = system("./configure "+config.pdt_config, timeout=1200)
        if retval != 0:
            error("Error: failed to configure PDT! Skipping all TAU builds!")
            return testmap
        retval = system(config.tauMake)
        if retval != 0:
            error("Error: failed to make PDT! Skipping all TAU builds!")
            return testmap
        retval = system(config.tauMake+" install")
        if retval != 0:
            error("Error: failed to install PDT! Skipping all TAU builds!")
            return testmap

    outputHeader("Building TAU")
    baseOptions = ""

    if(config.pdt != ""):
        if(config.pdt == "-pdt=${TAU_ROOT}/../pdtoolkit"): 
            config.pdt="-pdt="+TAU_ROOT+"/../pdtoolkit"
        baseOptions += " " + config.pdt + " "
    if(config.papi != ""):
        baseOptions += " " + config.papi + " "
    if(config.otf2 != ""):
        baseOptions += " " + config.otf2 + " "
    if(config.libunwind != ""):
        baseOptions += " " + config.libunwind + " "
    baseOptions += " -iowrapper"
    if(config.perfetto):
        baseOptions += " -perfetto"
    if(config.arch != "sunx86_64" and config.name != "aix32" and config.name != "aix64" and config.downloadBFD == True):
        baseOptions += " -bfd=download"

    if(config.cleanBFD):
        config.purge()
        cdres = chdir(TAU_ROOT)
        if cdres != 0:
            error("TAU_ROOT not found! Aborting!")
            return cdres
        retval = system("bash -c \"CC=gcc ./configure -bfd=download -cc=gcc\"")
        if retval != 0:
            #error("Error: failed to configure!")
            return retval
        config.prepare()

    for tauconf in testmap:
        options = baseOptions
        if(mpi in tauconf.arguments and config.mpi != ""):
            options += " " + config.mpi
        if(opari in tauconf.arguments):
            if(config.useOpari == False):
                continue
            options += " " + config.opari
        else:
            if(openmp in tauconf.arguments):
                options += " -openmp -ompt=download"

        if(cuda in tauconf.arguments):
            #            print cuda in tauconf.arguments
            #            print config.cuda != ""
            #            print cuda in tauconf.arguments and config.cuda != ""
            if(config.cuda == ""):
                continue
            options += " " + config.cuda
        if(rocm in tauconf.arguments):
            if(config.rocm == ""):
                continue
            options+= " " + config.rocm
        
        if("level_zero" in tauconf.arguments):
            if(config.level_zero == ""):
                continue
            options += " " + config.level_zero
            if(config.opencl != ""):
                options += " " + config.opencl

        if(phase in tauconf.arguments):
            options += " -PROFILEPHASE"

        if(pthread in tauconf.arguments or (mpi in tauconf.arguments and (not openmp in tauconf.arguments and not opari in tauconf.arguments))):
            options += " -pthread"

        if(vtf in tauconf.arguments):
            options += " -vtf=" + TEST_ROOT + "/vtf3/binaries"

        if(scorep in tauconf.arguments):
            options += " " + config.scorep
        
        if(python in tauconf.arguments and config.python != ""):
            options += " " + config.python

        result = buildTAU(config, options)
        if(result == 0):
            f = open(TAU_ROOT + "/.active_stub", "r")
            stub = f.readline().rstrip()
            f.close()
            tauconf.stub = stub
    outputHeader("TAU Building Complete")
    return testmap

# def checkSILCDump(config, testName):

def checkTraces(config, testName):
    traceFormat = os.environ.get("TAU_TRACE_FORMAT", "").upper()
    res = 0

    if traceFormat == "OTF2":
        output("Checking OTF2 Trace Output")
        missing = []
        empty = []
        for fname in ["traces.def", "traces.otf2"]:
            if not os.path.exists(fname):
                missing.append(fname)
            elif os.path.getsize(fname) == 0:
                empty.append(fname)
        if not os.path.isdir("traces"):
            missing.append("traces/")
        if missing:
            error("OTF2 trace files not created: " + ", ".join(missing))
            res = 1
        if empty:
            error("OTF2 trace files are empty: " + ", ".join(empty))
            res = 1
        # Sanity check: run otf2-print if available
        if res == 0 and systemq("which otf2-print") == 0:
            if system2Min("otf2-print traces.otf2") != 0:
                warning("otf2-print failed on traces.otf2")
        systemq("rm -f traces.def traces.otf2")
        systemq("rm -rf traces")

    elif traceFormat == "PERFETTO":
        output("Checking Perfetto Trace Output")
        if not os.path.exists("tau.perfetto.gz"):
            error("tau.perfetto.gz not created")
            res = 1
        elif os.path.getsize("tau.perfetto.gz") == 0:
            error("tau.perfetto.gz is empty")
            res = 1
        else:
            # Sanity check: verify gzip integrity
            if systemq("gzip -t tau.perfetto.gz") != 0:
                error("tau.perfetto.gz is not a valid gzip file")
                res = 1
        systemq("rm -f tau.perfetto.gz")

    else:
        output("Checking Default (TRC/EDF) Trace Output")
        res = system2Min("tau_treemerge.pl")  # tau_multimerge
        if res != 0:
            return res
        res = system2Min("tau_convert -dump tau.trc tau.edf > " +
                         config.name + testName + ".dump")
        # This needs to remain a warning until the TRACE/IO bug is fixed
        for fname in ["tau.trc", "tau.edf"]:
            if not os.path.exists(fname):
                error("failed to create " + fname)
                res = 1
            elif os.path.getsize(fname) == 0:
                error(fname + " is empty")
                res = 1
        systemq("rm -f *.vpt.gz *.trc *.edf *.dump")

    return res

def checkParaProfDump(config, testName, testType):
    output("Checking paraprof --pack/--dump")
    res = 0
    if os.path.exists("profile.0.0.0") == False:
        dirs = glob.glob("MULTI_*")
        if len(dirs) == 0:
            error("No Profiles!")
        else:
            res = checkMultiParaProfDump(config, testName, testType)
        return res
    system("pprof > \"" + config.name + "." + testName + ".pprof\"")

    now = datetime.datetime.now()
    filename = config.name + "." + testName + \
        "." + now.strftime("%F_%s") + ".ppk"

    res = system("paraprof --pack " + filename)

    loadProfilesToDatabase(config, testName, testType, filename, now)

    systemq("rm -f profile.*")
    system("paraprof --dump " + filename)
    system("pprof > \"" + config.name + "." + testName + ".ppk.pprof\"")
    retval = systemq("diff -s -w \"" + config.name + "." + testName +
                     ".pprof\" \"" + config.name + "." + testName + ".ppk.pprof\"")
    if retval != 0:
        warning("Error: pack->dump differs from original!")
        res = 1
    else:
        output("pack->dump matches original, ok!")
    systemq("rm -f profile.*")
    systemq("rm -f *.ppk")
    systemq("rm -f *.pprof")
    systemq("rm -f tauprofile.xml")
    return res
#    system("scp " + config.name + ".* proton:/tmp/testtau_results")

def checkMultiParaProfDump(config, testName, testType):
    output("Checking multi paraprof --pack/--dump")

    res = 0
    dirs = glob.glob("MULTI_*")
    for directory in dirs:
        cdres = chdir(directory)
        if(cdres != 0):
            error("Directory not found! Aborting!")
            return cdres
        shortname = "../" + config.name + "." + directory + "." + testName
        system("pprof > \"" + shortname + ".pprof\"")
        chdir("..")

    now = datetime.datetime.now()
    filename = config.name + "." + testName + \
        "." + now.strftime("%F_%s") + ".ppk"
    system("paraprof --pack " + filename)

    retval = loadProfilesToDatabase(config, testName, testType, filename, now)
    if retval != 0:
        res = 1
        warning("Error loading profile to database")
    systemq("rm -rf MULTI_*")
    system("paraprof --dump " + filename)

    for directory in dirs:
        cdres = chdir(directory)
        if(cdres != 0):
            error("Directory not found! Aborting!")
            return cdres
        shortname = "../" + config.name + "." + directory + "." + testName
        system("pprof > \"" + shortname + ".ppk.pprof\"")
        retval = systemq("diff -s -w \"" + shortname +
                         ".pprof\" \"" + shortname + ".ppk.pprof\"")
        if retval != 0:
            res = 1
            warning("Error: pack->dump differs from original!")
        else:
            output("pack->dump matches original, ok!")
        chdir("..")
    systemq("rm -rf MULTI_*")
    return res
#    system("scp " + config.name + ".* proton:/tmp/testtau_results")

# def compareProfiles(testName):
#        # now check the function names
#        output("Checking output correctness")
#        #system("pprof -l > functionnames")
#        retval = profile_diff.compare_profdirs(".", TEST_ROOT + "/data/"+selectedConfig+"/"+testName,True)
#        #system("diff -s -w functionnames " + TEST_ROOT + "/data/opari/construct-functionnames")
#        if retval == 0:
#            output("function names matched, ok!")
#        elif retval == 1:
#            warning("Warning: High performance variance!")
#        else:
#            error("Error: invalid profile output")

# ---------------------------------------------------------------------------
# Profile caching and comparison helpers
# ---------------------------------------------------------------------------

def _get_tau_diff():
    """Lazily import the tau_diff module from TAU_ROOT/tools/src/."""
    global _tau_diff_module
    if _tau_diff_module is not None:
        return _tau_diff_module
    tau_diff_src = os.path.join(TAU_ROOT, "tools", "src")
    if tau_diff_src not in sys.path:
        sys.path.insert(0, tau_diff_src)
    try:
        import tau_diff
        _tau_diff_module = tau_diff
    except ImportError:
        warning("Could not import tau_diff from " + tau_diff_src)
    return _tau_diff_module


def _profile_cache_dir():
    """Return the persistent profile-baseline cache directory for this config."""
    return os.path.join(TEST_ROOT, "profile_cache")


def _safe_cache_subdir(testName):
    """Return a filesystem-safe directory name derived from testName."""
    return testName.replace('/', '-').replace(' ', '_')


def saveProfilesToCache(testName, hadNewErrors):
    """Copy current profile.*.*.* files to the persistent cache.

    Skips the update when hadNewErrors is True (and TAU_UPDATE_BASELINE is not
    set) so that broken runs do not overwrite a good baseline.
    Returns the cache subdirectory path whether or not it was updated.
    """
    safe = _safe_cache_subdir(testName)
    cache_dir = os.path.join(_profile_cache_dir(), safe)

    profiles = sorted(glob.glob("profile.*.*.*"))
    if not profiles:
        for md in sorted(glob.glob("MULTI_*")):
            profiles = sorted(glob.glob(os.path.join(md, "profile.*.*.*")))
            if profiles:
                break

    if not profiles:
        return cache_dir

    if hadNewErrors and not _FORCE_UPDATE_BASELINE:
        output("Skipping profile cache update — errors present "
               "(set TAU_UPDATE_BASELINE=1 to force)")
        return cache_dir

    print("<details><summary><b>Saving profile baseline to cache</b></summary><pre>")
    try:
        os.makedirs(cache_dir, exist_ok=True)
        for pf in profiles:
            dest = os.path.join(cache_dir, os.path.basename(pf))
            shutil.copy2(pf, dest)
            print(html.escape("  saved: " + dest))
    except Exception as e:
        print(html.escape("Warning: could not save profile cache: " + str(e)))
    print("</pre></details>")
    return cache_dir


def _is_stochastic_event(func_name):
    """Return True for EBS [SAMPLE] and [CONTEXT] entries.

    These come from TAU's event-based sampling (EBS) and have inherently
    non-deterministic call counts between runs and instrumentation methods;
    they must not be used for zero-tolerance call-count comparisons.
    """
    s = func_name.strip().strip('"')
    return '[SAMPLE]' in s or '[CONTEXT]' in s


# C library I/O / memory / socket functions intercepted by tau_exec -io/-memory.
# TAU's own profile-write code uses these internally, so their call counts are
# non-deterministic (they vary by ±1–4 between runs and between PDT/CompInst).
# These should not trigger call-count hard errors.
_IO_WRAPPER_NAMES = frozenset({
    'write', 'read', 'open', 'close', 'unlink', 'rename', 'stat', 'fstat', 'lstat',
    'fopen', 'fclose', 'fread', 'fwrite', 'fscanf', 'fprintf', 'fflush',
    'ftell', 'fseek', 'rewind',
    'bind', 'connect', 'accept', 'socket', 'send', 'recv',
    'sendto', 'recvfrom', 'getsockname', 'getpeername', 'setsockopt', 'getsockopt',
    'malloc', 'free', 'calloc', 'realloc', 'posix_memalign',
})


def _is_io_wrapper_call(func_name):
    """Return True if func_name is a tau_exec I/O/memory wrapper function,
    or a system library function from an assembly source file.

    tau_exec I/O/memory wrappers have no source-location annotation (no '[{file}]')
    because they are intercepted at the binary level, not instrumented by PDT or
    CompInst.  Their call counts are non-deterministic due to TAU's own profile-
    writing I/O.

    Assembly-source functions (e.g. __tls_get_addr from glibc) are instrumented
    by PDT when debug info is available, but are absent from CompInst profiles.
    Their call counts differ non-deterministically between PDT and CompInst because
    PDT changes the startup code path that triggers TLS initialisation.
    """
    # Assembly source files (.S / .s) — glibc internals like __tls_get_addr.
    if '.S}' in func_name or '.s}' in func_name:
        return True
    # Extract the leaf function from a callpath (part after the last '=>').
    # e.g. "[PTHREAD] pmix_show_help_yylex [{.so} {0,0}] => read()  " has leaf
    # "read()  " even though the parent is source-annotated.
    leaf = func_name.strip('"').split('=>')[-1].strip()
    # If the leaf itself has a source annotation it is PDT/CompInst instrumented
    # code — deterministic, not an I/O wrapper.
    if '[{' in leaf:
        return False
    # Strip parentheses to get the bare function name.
    bare = leaf.strip().rstrip(')').rstrip('(').strip()
    return bare in _IO_WRAPPER_NAMES


def _trim_results_for_display(results, suppress_unique=True, suppress_stochastic=True):
    """Return a filtered, capped copy of compare_profiles results for HTML display.

    suppress_unique: drop "Unique to Profile X" entries (all v1=0 or all v2=0).
        For cross-run comparison these are already caught by the call-count check.
        For cross-builder comparison they are expected due to naming differences.
    suppress_stochastic: drop [SAMPLE]/[CONTEXT] EBS entries; their timing and
        call counts vary non-deterministically between runs and methods.
    Output is hard-capped at _MAX_DIFF_DISPLAY entries; further entries are
    counted and reported as a single suppression notice.
    Returns (trimmed_results_dict, suppressed_count).
    """
    funcs = results['functions']
    if suppress_stochastic:
        funcs = [f for f in funcs if not _is_stochastic_event(f['name'])]
    if suppress_unique:
        funcs = [f for f in funcs
                 if not (all(m['v1'] == 0 for m in f['metrics'].values())
                         or all(m['v2'] == 0 for m in f['metrics'].values()))]
    suppressed = max(0, len(funcs) - _MAX_DIFF_DISPLAY)

    # Filter user_events: TAU stores per-run metadata (PIDs, timestamps, CPU MHz)
    # as uniquely-keyed user events.  Every comparison produces a flood of
    # "pid | 1234567" (Removed) / "pid | 1234568" (New) entries that are always
    # unique between any two profiles and convey no regression signal.
    user_events = results.get('user_events', [])
    if suppress_unique and user_events:
        user_events = [e for e in user_events
                       if not (all(m['v1'] == 0 for m in e['metrics'].values())
                               or all(m['v2'] == 0 for m in e['metrics'].values()))]
    # Filter sysfs hardware metrics: TAU with -iowrapper/-syscall records PCI/NUMA
    # bandwidth and device info by reading sysfs files, storing them as user events
    # named e.g. "Read Bandwidth (MB/s) <file=/sys/bus/pci/devices/...>".
    # On machines with many PCI devices (e.g. ROCm systems) there can be hundreds
    # of entries per comparison, all changing with machine load.  They carry no
    # meaningful regression signal.
    user_events = [e for e in user_events if '<file=' not in e['name']]

    # Clear metadata: CPU MHz, timestamps, PIDs etc. always differ between any
    # two profiles and are not useful regression signal.
    return dict(results,
                functions=funcs[:_MAX_DIFF_DISPLAY],
                user_events=user_events,
                metadata=[]), suppressed


def compareToBaseline(testName):
    """Compare current profile files against the cached baseline from a prior run.

    Call-count differences trigger a hard error (zero tolerance), excluding
    stochastic EBS [SAMPLE]/[CONTEXT] entries.
    Timing differences beyond _TIMING_THRESHOLD trigger a soft warning.
    """
    safe = _safe_cache_subdir(testName)
    cache_dir = os.path.join(_profile_cache_dir(), safe)

    cached = sorted(glob.glob(os.path.join(cache_dir, "profile.*.*.*")))
    if not cached:
        return  # No baseline yet — first run for this test combination.

    current = sorted(glob.glob("profile.*.*.*"))
    if not current:
        for md in sorted(glob.glob("MULTI_*")):
            current = sorted(glob.glob(os.path.join(md, "profile.*.*.*")))
            if current:
                break
    if not current:
        return

    tau_diff = _get_tau_diff()
    if tau_diff is None:
        return

    cached_map = {os.path.basename(f): f for f in cached}
    current_map = {os.path.basename(f): f for f in current}
    common = sorted(set(cached_map) & set(current_map))
    if not common:
        warning("No matching profile filenames between baseline and current run")
        return

    output("Comparing profiles to baseline (timing threshold: "
           + str(_TIMING_THRESHOLD) + "%)")
    call_count_issues = []
    timing_diffs = []

    print("<details><summary><b>Cross-run profile comparison</b></summary><pre>")
    for fname in common:
        try:
            p_old = tau_diff.TauProfile(cached_map[fname])
            p_new = tau_diff.TauProfile(current_map[fname])
        except Exception as e:
            print(html.escape("  Could not parse " + fname + ": " + str(e)))
            continue

        # Zero tolerance: call counts must be identical between runs.
        # Skip [SAMPLE]/[CONTEXT] (non-deterministic EBS), tau_exec I/O
        # wrappers (TAU's own profile-write I/O makes these non-deterministic),
        # OpenMP_Task entries whose call counts are non-deterministic due to
        # work-stealing (tasks may execute on any thread in any order), and
        # [SUMMARY] thread-aggregate entries (non-deterministic with EBS/dynamic
        # OpenMP scheduling).
        for func_name in set(p_old.functions) & set(p_new.functions):
            if (_is_stochastic_event(func_name)
                    or _is_io_wrapper_call(func_name)
                    or 'OpenMP_Task' in func_name
                    or '[SUMMARY]' in func_name):
                continue
            old_calls = p_old.functions[func_name].get("Calls", None)
            new_calls = p_new.functions[func_name].get("Calls", None)
            if (old_calls is not None and new_calls is not None
                    and old_calls != new_calls
                    # Allow ±1 absolute tolerance for small-count measurement
                    # noise (e.g. functions called 10-20 times where one call
                    # lands on a TAU init/finalize boundary differently between
                    # PDT and CompInst instrumentation).
                    and not (abs(old_calls - new_calls) == 1
                             and min(old_calls, new_calls) >= 5)):
                call_count_issues.append(
                    html.escape(func_name.strip('"'))
                    + " (" + str(old_calls) + "->" + str(new_calls) + ")")

        # Soft threshold: timing differences.
        # Trim stochastic/unique entries and cap to _MAX_DIFF_DISPLAY lines.
        results = tau_diff.compare_profiles(p_old, p_new, _TIMING_THRESHOLD, "Incl")
        display_results, suppressed = _trim_results_for_display(results)
        if display_results['functions'] or display_results['user_events']:
            timing_diffs.append(fname)
            print(html.escape(tau_diff.generate_report_string(
                p_old, p_new, display_results, _TIMING_THRESHOLD, "Incl")))
            if suppressed:
                print(html.escape(
                    "  ... " + str(suppressed) + " additional entries suppressed"
                    " (export TAU_DIFF_MAX_DISPLAY=N to show more)"))
    print("</pre></details>")

    if call_count_issues:
        error("Call count changes vs baseline (instrumentation bug?): "
              + "; ".join(call_count_issues[:5]))
    elif timing_diffs:
        warning("Timing differs from baseline by >" + str(_TIMING_THRESHOLD)
                + "% — possible overhead regression in: "
                + ", ".join(timing_diffs))
    else:
        output("Profiles match baseline within threshold.")


def compareBuilderProfiles(builderEntries, context=""):
    """Compare profiles across instrumentation methods for the same (test, exec, env).

    builderEntries: list of (builderName, cacheDir) pairs, one per builder.
    context: human-readable string identifying the test/exec/env combination,
             included in every HTML section header.

    Uses tau_diff's normalize mode to match functions across instrumentation
    styles (PDT vs CompInst): strips return types, file paths, and line info
    to reduce each entry to its bare function name for cross-method pairing.
    Ambiguous matches (overloaded functions sharing a base name) are skipped.
    [SAMPLE] and [CONTEXT] EBS entries are excluded from call-count comparison.
    """
    if len(builderEntries) < 2:
        return
    tau_diff = _get_tau_diff()
    if tau_diff is None:
        return

    ctx_suffix = (" [" + html.escape(context) + "]") if context else ""
    output("Comparing profiles across instrumentation methods"
           + ((" for " + context) if context else ""))
    ref_name, ref_dir = builderEntries[0]

    for cmp_name, cmp_dir in builderEntries[1:]:
        ref_profiles = sorted(glob.glob(os.path.join(ref_dir, "profile.*.*.*")))
        cmp_profiles = sorted(glob.glob(os.path.join(cmp_dir, "profile.*.*.*")))
        if not ref_profiles or not cmp_profiles:
            continue

        ref_map = {os.path.basename(f): f for f in ref_profiles}
        cmp_map = {os.path.basename(f): f for f in cmp_profiles}
        common = sorted(set(ref_map) & set(cmp_map))
        if not common:
            continue

        call_count_issues = []
        timing_diffs = []

        print("<details><summary><b>Cross-builder: "
              + html.escape(ref_name + " vs " + cmp_name)
              + ctx_suffix
              + "</b></summary><pre>")
        for fname in common:
            try:
                p_ref = tau_diff.TauProfile(ref_map[fname])
                p_cmp = tau_diff.TauProfile(cmp_map[fname])
            except Exception as e:
                print(html.escape("  Could not parse " + fname + ": " + str(e)))
                continue

            # Single comparison pass with normalize=True.  results['normalized_matches']
            # contains ALL normalized pairs regardless of timing threshold, so we can
            # derive call-count issues from it without a separate threshold=0 call.
            results = tau_diff.compare_profiles(
                p_ref, p_cmp, _BUILDER_THRESHOLD, "Incl", normalize=True)

            # -- Call-count check (threshold-independent) --
            # 1. Exact name matches: iterate intersection directly.
            for func_name in set(p_ref.functions) & set(p_cmp.functions):
                if (_is_stochastic_event(func_name)
                        or _is_io_wrapper_call(func_name)
                        # [SUMMARY] entries aggregate across threads; with EBS or
                        # dynamic OpenMP scheduling the per-thread distribution is
                        # non-deterministic, making the aggregate call count vary.
                        or '[SUMMARY]' in func_name
                        # OpenMP_Task call counts are non-deterministic due to
                        # work-stealing: any thread may steal and execute a task.
                        or 'OpenMP_Task' in func_name):
                    continue
                v1 = p_ref.functions[func_name].get('Calls', 0)
                v2 = p_cmp.functions[func_name].get('Calls', 0)
                if (v1 != v2
                        # Allow ±1 absolute tolerance for small-count noise
                        # (e.g. a function called ~10 times where one call
                        # lands on a TAU init/finalize boundary differently).
                        and not (abs(v1 - v2) == 1 and min(v1, v2) >= 5)):
                    call_count_issues.append(
                        html.escape(func_name.strip('"'))
                        + " (" + ref_name + ":" + str(v1)
                        + " vs " + cmp_name + ":" + str(v2) + ")")
            # 2. Normalized matches: populated for all pairs regardless of threshold.
            for p1_name, p2_name, _ in results.get('normalized_matches', []):
                if (_is_stochastic_event(p1_name)
                        or _is_io_wrapper_call(p1_name)
                        or '[SUMMARY]' in p1_name
                        or 'OpenMP_Task' in p1_name):
                    continue
                v1 = p_ref.functions.get(p1_name, {}).get('Calls', 0)
                v2 = p_cmp.functions.get(p2_name, {}).get('Calls', 0)
                if (v1 != v2
                        and not (abs(v1 - v2) == 1 and min(v1, v2) >= 5)):
                    display_name = (p1_name.strip('"') + " / " + p2_name.strip('"')
                                    if p1_name != p2_name else p1_name.strip('"'))
                    call_count_issues.append(
                        html.escape(display_name)
                        + " (" + ref_name + ":" + str(v1)
                        + " vs " + cmp_name + ":" + str(v2) + ")")

            # -- Timing display: matched functions only, capped at _MAX_DIFF_DISPLAY --
            # Suppress "Unique to Profile X" entries (expected for different naming
            # conventions) and stochastic EBS entries.
            display_results, suppressed = _trim_results_for_display(results)
            if display_results['functions'] or display_results['user_events']:
                timing_diffs.append(fname)
                print(html.escape(tau_diff.generate_report_string(
                    p_ref, p_cmp, display_results, _BUILDER_THRESHOLD, "Incl")))
                if suppressed:
                    print(html.escape(
                        "  ... " + str(suppressed) + " additional entries suppressed"
                        " (export TAU_DIFF_MAX_DISPLAY=N to show more)"))
        print("</pre></details>")

        if call_count_issues:
            error("Call count mismatch between " + ref_name + " and " + cmp_name
                  + ctx_suffix + ": " + "; ".join(call_count_issues[:5]))
        elif timing_diffs:
            warning("Timing differs by >" + str(_BUILDER_THRESHOLD)
                    + "% between " + ref_name + " and " + cmp_name
                    + ctx_suffix + " in: " + ", ".join(timing_diffs))
        else:
            output(ref_name + " vs " + cmp_name + ctx_suffix
                   + ": profiles match within threshold.")


def checkProfileInvariants(testName):
    """Check mathematical invariants that must hold for any valid TAU profile.

    These checks are hardware-independent and catch instrumentation bugs:
      - Exclusive and inclusive times must be non-negative.
      - Inclusive time must be >= exclusive time (within a small epsilon).
      - Call counts must be non-negative.
    """
    profiles = sorted(glob.glob("profile.*.*.*"))
    if not profiles:
        for md in sorted(glob.glob("MULTI_*")):
            profiles = sorted(glob.glob(os.path.join(md, "profile.*.*.*")))
            if profiles:
                break
    if not profiles:
        return

    tau_diff_mod = _get_tau_diff()
    if tau_diff_mod is None:
        return

    output("Checking profile structural invariants")
    any_issue = False

    for pf in profiles:
        try:
            p = tau_diff_mod.TauProfile(pf)
        except Exception as e:
            warning("Could not parse " + pf + " for invariant check: " + str(e))
            continue

        # PAPI hardware counter metrics can have negative exclusive values due
        # to counter rollover / measurement noise.  Only apply sign checks to
        # wall-clock timing metrics (metric names containing TIME or CLOCK).
        is_time_metric = ('TIME' in p.metric_name.upper()
                          or 'CLOCK' in p.metric_name.upper())

        for func_name, fdata in p.functions.items():
            excl = fdata.get("Excl", 0.0)
            incl = fdata.get("Incl", 0.0)
            calls = fdata.get("Calls", 0)
            display = html.escape(func_name.strip('"'))
            if is_time_metric:
                if excl < 0 or incl < 0:
                    error("Negative time in " + pf + " for " + display
                          + " (Excl=" + str(excl) + ", Incl=" + str(incl) + ")")
                    any_issue = True
                elif incl < excl - 0.001:  # small epsilon for floating-point rounding
                    warning("Inclusive < Exclusive in " + pf + " for " + display
                            + " (Incl=" + str(incl) + ", Excl=" + str(excl) + ")")
                    any_issue = True
            if calls < 0:
                error("Negative call count in " + pf + " for " + display)
                any_issue = True

    if not any_issue:
        output("Profile structural invariants OK.")


def loadProfilesToDatabaseNULL(config, testname, testType, filename, now):
    return 0

def loadProfilesToDatabase(config, testname, testType, filename, now):

    #    filename=config.name + "." + testname + ".ppk";
    #    retval = system("paraprof --pack " + filename)
    #    if retval != 0:
    #        return retval
    #    metafnameBase = config.name + "." + testname + "." + now.strftime("%F_%s")

    combined_stamp = config.regressionDate + "_" + config.regressionTime
    jsonmeta = {"database": "regression_taudb", "system": config.name, "application": config.name, "experiment": testname, "trialname": combined_stamp,
                "filename": filename, "filetype": "packed", "regression_time": config.regressionTime, "regression_date": config.regressionDate, "git_hash": config.gitHash}
    jsonmeta = dict(list(jsonmeta.items()) + list(testType.items()))

    stringmeta = ""
    for key in jsonmeta:
        #print(type(key))
        #print(key)
        #print(type(jsonmeta[key]))
        #print(jsonmeta[key])
        stringmeta = stringmeta+str(key)+"="+str(jsonmeta[key])+":"

#    metafname = metafnameBase + "_taudb" + ".metadata"

#    f = open(metafname, 'w')
#    f.write(json.dumps(jsonmeta))
#    f.close()

#    system("chmod 777 "+metafname)
    system("chmod 777 "+filename)

    if not config.batchUpload:
        #        keyFile = TEST_ROOT + "/scripts/id_dsa_dropbox_taudb"
        #        destination = "dropbox@taudb.nic.uoregon.edu:loadingdock/."

        retval = system("taudb_loadtrial -c regression_taudb -m " + stringmeta + " -a " +
                        config.name + " -x " + testname + " -n " + combined_stamp + " " + filename)
        if retval != 0:
            return retval

#        retval = system("scp -i " + keyFile + " " + metafname + " " + destination)
#        if retval != 0:
#            return retval

        #system("rm -f " + metafname)
    else:
        system("cp -f " + filename + " " + TEST_ROOT)
        #system("mv -f " + metafname + " " + TEST_ROOT)

    return 0

# Given an object and a namespace returns the list of names for the object
def namestr(obj, namespace):
    return [name for name in namespace if namespace[name] is obj]





def CheckOutput(config, hasTrace, hasProfile, useXml, testName, testType):
    res = 0
    errors_before = errorsFound
    print("<details><summary><b>Checking Output</b></summary>")
    if(hasProfile):
        output("Checking Profile Output")
        profileFiles = sorted(glob.glob("profile.*.*.*"))
        multiDirs = sorted(glob.glob("MULTI_*"))
        def checkProfileFile(pf):
            parts = pf.rsplit("/", 1)[-1].split(".")
            try:
                if int(parts[1]) < 0:
                    return pf
            except (IndexError, ValueError):
                pass
            return None

        allProfileFiles = []
        print("<details><summary><b>Profile Files</b></summary><pre>")
        if profileFiles:
            for pf in profileFiles:
                print(pf)
                allProfileFiles.append(pf)
        elif multiDirs:
            for md in multiDirs:
                mdFiles = sorted(glob.glob(md + "/profile.*.*.*"))
                if mdFiles:
                    for pf in mdFiles:
                        print(pf)
                        allProfileFiles.append(pf)
                else:
                    print(md + "/ (no profile.* files found)")
        else:
            print("(no profile files found)")
        print("</pre></details>")
        badProfileFiles = [pf for pf in allProfileFiles if checkProfileFile(pf)]
        if badProfileFiles:
            error("Negative node index detected in profile output!")
        if(useXml):
            system("paraprof --dump tauprofile.xml")
        #res = res+checkParaProfDump(config, testName, testType) #TODO: Get access to remote taudb database
        if _PROFILE_CHECKS:
            checkProfileInvariants(testName)
            compareToBaseline(testName)
            saveProfilesToCache(testName, errorsFound > errors_before)
    if(hasTrace):
        output("Checking Trace Output")
        res = res+checkTraces(config, testName)
    print("</details>")
    if res > 0:
        warning("Output error!")

def FullClean():
    print("<details><summary><b>Cleaning</b></summary>")
    systemq("rm -rf MULTI_*")
    systemq("rm -r *.pprof *.ppk ebstrace.* profile.*")  # ,0,True,False)
    systemq("rm -f *.vpt.gz *.trc *.edf *.dump")
    print("</details>")

#def SaveCores(binName, testName):
#    rule = re.compile(fnmatch.translate("*core*"), re.IGNORECASE)
#    coreList = [name for name in os.listdir(".") if rule.match(name)]
#    if len(coreList) < 1:
#        return
#    system('gdb --batch --quiet -ex "bt full" -ex "thread 1" -ex "bt full" -ex "quit" '+ binName+" "+coreList[0])
#    now = datetime.datetime.now()
#    archdirname = "C0RE-DUMP."+testName + "." + now.strftime("%F_%s")
#    systemq("mkdir "+archdirname)
#    for path in coreList:
#        systemq("mv " + path + " " + archdirname)
#    systemq("cp " + binName + " " + archdirname)

def find_apport_cores(bin_path, since_timestamp, target_dir):
    """
    Scans /var/crash for relevant .crash files, unpacks them, 
    and moves the 'CoreDump' file to target_dir.
    """
    # 1. Translate /abs/path/to/bin to _abs_path_to_bin (apport uses absolute paths)
    abs_bin_path = os.path.abspath(bin_path)
    encoded_path = abs_bin_path.lstrip("/").replace("/", "_")
    crash_pattern = f"/var/crash/_{encoded_path}.*.crash"
    found_cores = []

    for crash_file in glob.glob(crash_pattern):
        # 2. Check if the crash is recent
        mtime = os.path.getmtime(crash_file)
        if mtime < since_timestamp:
            continue

        # 3. Create a temp directory to unpack
        with tempfile.TemporaryDirectory() as tmp_unpack:
            try:
                # 4. Use apport-unpack to extract the core
                subprocess.run(["apport-unpack", crash_file, tmp_unpack], check=True)
                
                core_src = os.path.join(tmp_unpack, "CoreDump")
                if os.path.exists(core_src):
                    # Use PID from the crash file name or metadata if possible
                    # For now, we'll just give it a unique name
                    pid = crash_file.split('.')[-2] # Rough estimate from filename
                    dest_name = f"core.apport.{pid}"
                    shutil.copy(core_src, os.path.join(target_dir, dest_name))
                    found_cores.append(dest_name)
            except Exception:
                continue
                
    return found_cores

def SaveCores(bin_path, test_name, start_time_epoch):
    # Resolve executable candidates now, while still in the test run directory.
    # Keep matching strict (full executable paths only), but include interpreter
    # executables for script/shebang launches (e.g. python, bash wrappers).
    abs_bin_path = os.path.abspath(bin_path)
    run_cwd = os.path.abspath(os.getcwd())

    exe_candidates = []

    def _add_candidate(path):
        if not path:
            return
        norm = os.path.abspath(path)
        if norm not in exe_candidates:
            exe_candidates.append(norm)

    _add_candidate(abs_bin_path)
    if os.path.exists(abs_bin_path):
        _add_candidate(os.path.realpath(abs_bin_path))

    # If the command is looked up via PATH (e.g. "python3"), include the
    # concrete executable used at runtime.
    if os.path.dirname(bin_path) == "":
        which_path = shutil.which(bin_path)
        if which_path:
            _add_candidate(which_path)
            _add_candidate(os.path.realpath(which_path))

    # If bin_path points to a script with a shebang, include its interpreter.
    # Handles "#!/usr/bin/python3" and "#!/usr/bin/env python3" forms.
    if os.path.isfile(abs_bin_path):
        try:
            with open(abs_bin_path, "rb") as bf:
                first = bf.readline(4096)
            if first.startswith(b"#!"):
                shebang = first[2:].decode("utf-8", errors="replace").strip()
                if shebang:
                    parts = shebang.split()
                    if parts:
                        interp = parts[0]
                        if os.path.basename(interp) == "env" and len(parts) > 1:
                            interp = shutil.which(parts[1]) or parts[1]
                        _add_candidate(interp)
                        if os.path.exists(interp):
                            _add_candidate(os.path.realpath(interp))
        except Exception:
            pass
    arch_dir = f"CORES.{test_name}.{int(start_time_epoch)}"
    os.makedirs(arch_dir, exist_ok=True)

    found_any = False

    # --- PHASE 1: LOCAL SEARCH ---
    local_cores = [f for f in os.listdir('.') if 'core' in f.lower() and os.path.isfile(f)]
    if local_cores:
        for c in local_cores:
            shutil.move(c, os.path.join(arch_dir, c))
        found_any = True

    # --- PHASE 2: SYSTEMD-COREDUMP ---
    # Always check — MPI runs may produce multiple core dumps from different ranks.
    # Match by absolute exe path (COREDUMP_EXE) to distinguish tests that share a
    # binary name; bin_name (COMM) alone would be ambiguous across test directories.
    print("<details><summary><b>coredumpctl diagnostic</b></summary><pre>")
    try:
        since_str = datetime.datetime.fromtimestamp(start_time_epoch).strftime("%Y-%m-%d %H:%M:%S")
        print(html.escape(
            f"coredumpctl: searching for exe candidates={exe_candidates} since={since_str}"))

        # Try --json=short first (systemd >= 248); fall back to text parsing for older systems.
        pids = []
        for exe in exe_candidates:
            res = subprocess.run(
                ["coredumpctl", "--no-pager", "list", exe, "--since", since_str, "--json=short"],
                capture_output=True, text=True)
            print(html.escape(f"coredumpctl --json=short exe={exe} exit={res.returncode}"))
            if res.stderr.strip():
                print(html.escape(res.stderr.strip()))
            if res.returncode == 0 and res.stdout.strip():
                try:
                    for entry in json.loads(res.stdout):
                        pids.append(str(entry['pid']))
                    continue
                except Exception as je:
                    print(html.escape(f"json parse failed for exe={exe}: {je}"))

            # Fallback: parse text output (works on systemd < 248).
            # Lines look like: "Wed 2026-05-06 12:17:42 PDT  3526136 ..."
            res2 = subprocess.run(
                ["coredumpctl", "--no-pager", "list", exe, "--since", since_str],
                capture_output=True, text=True)
            print(html.escape(f"coredumpctl text fallback exe={exe} exit={res2.returncode}"))
            if res2.stderr.strip():
                print(html.escape(res2.stderr.strip()))
            if res2.returncode == 0:
                for line in res2.stdout.splitlines():
                    parts = line.split()
                    # Find the first purely-numeric token with enough digits to be
                    # a PID, skipping the header and date/time tokens.  The format
                    # is: DAY DATE TIME TZ PID UID GID SIG PRESENT EXE, but TZ can
                    # vary so we scan rather than hard-coding column 4.
                    for tok in parts:
                        if tok.isdigit() and int(tok) > 1:
                            pids.append(tok)
                            break

        # De-duplicate and keep original discovery order.
        unique_pids = []
        for pid in pids:
            if pid not in unique_pids:
                unique_pids.append(pid)

        # Tighten matching for shared interpreters (e.g. /usr/bin/python3.X):
        # keep only entries from the same working directory when available.
        pids = []
        for pid in unique_pids:
            keep = True
            try:
                info_res = subprocess.run(
                    ["coredumpctl", "--no-pager", "info", pid],
                    capture_output=True, text=True)
                if info_res.returncode == 0:
                    m_cwd = re.search(r'^\s*CWD:\s+(.*)$', info_res.stdout, re.MULTILINE)
                    if m_cwd:
                        core_cwd = os.path.abspath(m_cwd.group(1).strip())
                        if core_cwd != run_cwd:
                            keep = False
                            print(html.escape(
                                f"coredumpctl: skipping pid={pid} due to cwd mismatch "
                                f"({core_cwd} != {run_cwd})"))
            except Exception as ie:
                print(html.escape(f"coredumpctl info exception for pid={pid}: {ie}"))
            if keep:
                pids.append(pid)

        print(html.escape(f"coredumpctl: found PIDs: {pids}"))
        for pid in pids:
            out_path = os.path.join(arch_dir, f"core.systemd.{pid}")
            dump_res = subprocess.run(
                ["coredumpctl", "--no-pager", "dump", pid, "--output", out_path],
                capture_output=True)
            print(html.escape(f"coredumpctl dump pid={pid} exit={dump_res.returncode}"))
            if dump_res.stderr.strip():
                print(html.escape(dump_res.stderr.strip()))
            if dump_res.returncode == 0:
                found_any = True
    except Exception as e:
        print(html.escape(f"coredumpctl exception: {e}"))
    print("</pre></details>")

    # --- PHASE 3: APPORT (/var/crash) ---
    apport_cores = find_apport_cores(bin_path, start_time_epoch, arch_dir)
    if apport_cores:
        found_any = True

    # --- FINAL PROCESSING ---
    if found_any:
        # Run GDB on every core found, printing all thread backtraces.
        for core in sorted(os.listdir(arch_dir)):
            if 'core' in core.lower():
                core_path = os.path.join(arch_dir, core)
                system(f'gdb --batch --quiet -ex "set pagination off" '
                       f'-ex "thread apply all bt full" '
                       f'{abs_bin_path} {core_path}')
    else:
        os.rmdir(arch_dir)
        output("No cores found in any location.", "3", "darkorange")

def checkSlurmAvailability(config):
    """Check that required SLURM partitions have at least one usable node.

    Scans mpiBefore and seqBefore for '-p <partition>'.  If a partition is
    found and sinfo is available, confirms that the partition has at least one
    idle/allocated/mixed/reserved node.  Aborts the test run if no usable
    nodes are found, preventing the run from hanging on a down cluster.
    """
    partitions = set()
    for field in (config.mpiBefore, config.seqBefore):
        m = re.search(r'-p\s+(\S+)', field)
        if m:
            partitions.add(m.group(1))

    if not partitions:
        return

    # If sinfo is not present this is not a SLURM system; skip the check.
    if subprocess.run(["which", "sinfo"], capture_output=True).returncode != 0:
        return

    for partition in sorted(partitions):
        output(f"Checking SLURM partition availability: {partition}")
        retval = systemq(
            f"sinfo -p {partition} -h -t idle,alloc,mixed,reserved -o \"%n\" | grep -q ."
        )
        if retval != 0:
            error(f"No available nodes in SLURM partition '{partition}' — aborting test run!")
            end(-1)
        retval = systemq(
            f"srun -p {partition} --job-name=health_check --immediate=5 true"
        )
        if retval != 0:
            error(f"srun timed out on SLURM partition '{partition}' — aborting test run!")
            end(-1)

        output(f"SLURM partition '{partition}': nodes available.")


def RunAllTests(config, buildApps):
    hasProf = True
#    if config.scorep == "" and ScorepConf in buildApps:
#        buildApps.remove(ScorepConf)

    for tauBuild in buildApps:
        if tauBuild.stub != "":
            # system("rm -f " + TAU_ROOT + "/include/Makefile") #This seems like a bad idea.
            # retv = system("ln -s " + tauBuild.stub + " " + TAU_ROOT + "/include/Makefile") #Why was this happening?
            # if retv != 0:
            #    continue
            if len(tauBuild.tests)<1:
                warning("No tests for tau configuration!")
            for tauTest in tauBuild.tests:
                # Skip tests whose configRequirements don't match the active config.
                unmet = [k for k, v in tauTest.configRequirements.items()
                         if getattr(config, k, None) != v]
                if unmet:
                    output("Skipping " + tauTest.buildDir +
                           " (unmet requirements: " + ", ".join(unmet) + ")")
                    continue
                outputHeader("Testing " + tauTest.buildDir)
                #testPrefix=TEST_ROOT + "/programs/"
                #if tauTest.tauExample:
                testPrefix=TAU_ROOT+"/examples/"
                cdres=chdir(testPrefix + tauTest.buildDir)
                if cdres != 0:
                    error("Test directory not found! Aborting!")
                    continue
                if len(tauTest.tauBuilders)<1:
                    warning("No builders for tau test!")
                builder_profile_map = {}
                for tauTestBuild in tauTest.tauBuilders:
                    if tauTest.useTauComp == False and tauTestBuild is not DefaultTauBuild:
                        output("Build doesn't recognize TAU_OPTIONS. Skipping")
                        continue

                    output("Building " + tauTest.buildDir + " with: " +
                           tauTestBuild.name, "2", "purple")
                    #             " ".join(tauTestBuild.tauOptions),"2","purple")
                    tauTestBuild.setTauOptions(config, tauBuild.stub)
                    system("env | grep -i tau")

                    if config.tauMake != "make" and tauTest.buildCommand.find(config.tauMake) == -1:
                        tauTest.buildCommand = tauTest.buildCommand.replace(
                            "make", config.tauMake)

                    buildRet = system(tauTest.buildCommand)
                    if buildRet == 0:
                        if tauTest.buildDir != tauTest.binDir:
                            chdir(tauTest.buildDir)
                        baseCommand = tauTest.binName + " " + tauTest.arguments
                        if len(tauTest.tauExec)<1:
                            warning("No executors for tau build!")
                        for tauExec in tauTest.tauExec:
                            if (not config.useTauExec) and tauExec.useTauExec:
                                continue
                            if (not config.useEBS) and tauExec.useEBS:
                                continue
                            if(config.gomp and openmp in tauBuild.arguments):
                                tauExec.gomp = True
                            else:
                                tauExec.gomp = False
                            execCom = tauExec.tauExecCommands(
                                tauBuild.execArgs, tauTestBuild.isShared)
                            output("Tau Exec as:" + tauExec.name)
                            command = execCom + " " + baseCommand
                            if len(tauTest.tauEnv) <1:
                                warning("No run environments for executor!")
                            for envSet in tauTest.tauEnv:
                                if not envSet.isCompatibleWith(tauTest, config):
                                    continue

                                resolvedEnv = envSet.resolveFor(config, tauExec)
                                hasTrace = resolvedEnv.get("TAU_TRACE", "1") != "0"

                                runres = 0
                                testName = tauBuild.execArgs + "_" + tauTest.buildDir + "_" + \
                                    tauTestBuild.name + "_" + tauExec.name + "_" + envSet.name
                                testType = {"tau_exec_args": tauBuild.execArgs, "test_application": tauTest.buildDir,
                                            "tau_build_name": tauTestBuild.name, "tau_exec_name": tauExec.name, "tau_env_name": envSet.name}
                                testName = testName.replace('/', '-')
                                #outputHeader("Running " + tauTest.buildDir + " with " + testName)
                                outputHeader("Running " + tauTest.buildDir + "(" + tauTestBuild.name + ") with:" + envSet.name + ", " + tauExec.name + ", " + tauBuild.execArgs)
                                envSet.setTauRunEnvironment(config, resolvedEnv)
                                resolvedTestEnv = resolveTestEnvironment(tauTest)
                                for var, val in resolvedTestEnv.items():
                                    setEnviron(var, val, config)
                                FullClean()
                                #runs=10
                                test_start_time = datetime.datetime.now().timestamp()
                                for x in range(1):
                                    if(tauTest.useMPI):
                                        runres = executeMpi(command, config)
                                    else:
                                        runres = executeSequential(command, config)
                                    if (runres != 0):
                                        break
                                if(runres == 0): # and tauBuild != ScorepConf):
                                    output("Examining Output")
                                    useXml = False
                                    if TAU_PROFILE_FORMAT in resolvedEnv and resolvedEnv[TAU_PROFILE_FORMAT] == "merged":
                                        useXml = True
                                    CheckOutput(
                                        config, hasTrace, hasProf, useXml, testName, testType)
                                    # Track for cross-builder comparison after all builders run.
                                    if _PROFILE_CHECKS:
                                        _bp_key = (tauBuild.execArgs, tauTest.buildDir,
                                                   tauExec.name, envSet.name)
                                        builder_profile_map.setdefault(_bp_key, []).append(
                                            (tauTestBuild.name, os.path.join(
                                                _profile_cache_dir(),
                                                _safe_cache_subdir(testName))))
                                else:
                                    SaveCores(tauTest.binName, tauTest.buildDir + "_" +
                                              tauTestBuild.name + "_" + tauExec.name + "_" + envSet.name,
                                              test_start_time)
                                for var in resolvedTestEnv:
                                    unsetEnviron(var, config)
                                envSet.unsetTauRunEnvironment(config, resolvedEnv)

                    else:
                        warning("Build Failed, skipping Execution!")
                    tauTestBuild.unsetTauOptions(config)
                # After all builders are done for this test, compare profiles across
                # instrumentation methods for each (exec, env) combination.
                if _PROFILE_CHECKS:
                    for _bp_key, _bp_entries in builder_profile_map.items():
                        if len(_bp_entries) >= 2:
                            _bp_ctx = (_bp_key[1] + "  exec:" + _bp_key[2]
                                       + "  env:" + _bp_key[3])
                            compareBuilderProfiles(_bp_entries, context=_bp_ctx)
        else:
            warning(tauBuild.execArgs + " not built! Skipping tests!")
######################################################################

_parser = argparse.ArgumentParser(
    description="TAU regression worker — runs on the remote test machine.",
    usage="tau_regression.py <configuration> [run_root] [--tests DIR ...]",
)
_parser.add_argument("configuration",
                     help="Config name from configs.py")
_parser.add_argument("run_root", nargs="?", default=os.environ.get("HOME", "/tmp"),
                     help="Root directory for the test tree (default: $HOME)")
_parser.add_argument(
    "--tests", nargs="+", metavar="DIR",
    help="Restrict to tests whose buildDir matches one of these names. "
         "TAU configurations with no matching tests are skipped entirely, "
         "so only the necessary TAU builds are performed.",
)
_args = _parser.parse_args()

selectedConfig = _args.configuration
dirsuf = "-" + selectedConfig

run_prefix = _args.run_root

if not os.access(run_prefix, os.W_OK):
    error("INVALID RUN DIRECTORY: "+run_prefix)
    sys.exit(1)

if selectedConfig not in configs.configurations:
    error("couldn't find config for: " + selectedConfig)
    end(-1)

config=configs.configurations[selectedConfig]

#configFound = False
#for config_it in configs.configurations:
#    if config_it.name == selectedConfig:
#        config = config_it
#        configFound = True

#if configFound == False:
#    error("couldn't find config for: " + selectedConfig)
#    end(-1)


#############################

TEST_ROOT = configs.test_root(run_prefix, selectedConfig)
TAU_ROOT = TEST_ROOT + "/tau2"

# config.basedir overrides run_prefix for the test tree root.  Useful when
# invoking tau_regression.py directly against a hand-built or pre-existing
# TAU tree that lives at a path unrelated to the automated pipeline's runroot.
# (Note: this is independent of config.runroot, which controls where runtests.py
# rsyncs files and is the normal way to redirect the full automated run.)
if config.basedir != "":
    TEST_ROOT = configs.test_root(config.basedir, selectedConfig)
    TAU_ROOT = TEST_ROOT + "/tau2"

os.environ["TAU_ROOT"] = TAU_ROOT
os.environ["TEST_ROOT"] = TEST_ROOT

now = datetime.datetime.now()
config.regressionDate = now.strftime("%D")
config.regressionTime = now.strftime("%T")


print("""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><style>
body {
    background: #1a1a2e;
    color: #e0e0e0;
    font-family: monospace, sans-serif;
    padding: 1rem;
    scroll-behavior: smooth;
}
pre {
    white-space: pre-wrap;       /* Since CSS 2.1 */
    white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */
    white-space: -pre-wrap;      /* Opera 4-6 */
    white-space: -o-pre-wrap;    /* Opera 7 */
    word-wrap: break-word;       /* Internet Explorer 5.5+ */
    background: #12122a;
    border-left: 3px solid #333;
    padding: .4rem .6rem;
    margin: .2rem 0;
}
details {
    border-left: 3px solid #2a2a4a;
    margin: .3rem 0;
    padding-left: .5rem;
}
summary {
    cursor: pointer;
    padding: .2rem 0;
}
summary:hover { color: #a0c0ff; }
h1, h2, h3 { margin: .4rem 0; }
/* Remap legacy named font-color attributes for dark background */
font[color="green"]      { color: #7ec87e !important; }
font[color="red"]        { color: #e08080 !important; }
font[color="blue"]       { color: #6fa8dc !important; }
font[color="darkorange"] { color: #f4a460 !important; }
font[color="purple"]     { color: #b07fd4 !important; }
#toggle-bar {
    position: sticky;
    top: 0;
    background: #12122a;
    border-bottom: 1px solid #333;
    padding: .3rem .6rem;
    z-index: 10;
}
#toggle-bar button {
    background: #252540;
    color: #e0e0e0;
    border: 1px solid #444;
    border-radius: 3px;
    padding: .2rem .7rem;
    cursor: pointer;
    font-family: inherit;
    font-size: .85rem;
    margin-right: .4rem;
}
#toggle-bar button:hover { background: #333360; }
</style>
<script>
function toggleAll(open) {
    document.querySelectorAll('details').forEach(d => d.open = open);
}
</script>
</head>
<body>
<div id="toggle-bar">
  <button onclick="toggleAll(true)">Expand all</button>
  <button onclick="toggleAll(false)">Collapse all</button>
</div>
""")  # <PRE>

if chdir(TAU_ROOT) != 0:
    error("TAU_ROOT not found — cannot continue")
    end(-1)

system("git branch", timeout=0, reportTime=False)
system("git log -1 --pretty=format:'%h  %ad  %s' --date=format:'%Y-%m-%d %H:%M'", timeout=0, reportTime=False)
try:
    config.gitHash = check_output(["git", "rev-parse", "HEAD"]).rstrip()
except Exception:
    config.gitHash = b"unknown"

outputHeader("Configuration: " + config.name)

if config.path != "":
    prependPath(config.path, config)
# TODO: Re-enable ld-library-path if turning it off has no effect.
# if config.ld_library_path != "":
#    prependVar("LD_LIBRARY_PATH", config.ld_library_path, config)

system("echo $PYTHONPATH", timeout=0, reportTime=False)

config.prepare()

applyConfigEnvironment(config)

outputHeader("Startup")
prependPath(TAU_ROOT + "/" + config.arch + "/bin", config)
#prependVar("LD_LIBRARY_PATH", TAU_ROOT + "/" + config.arch + "/lib", config)
#system("which amdclang")

spackString=""
useSpack=False
for package in config.spack:
    #system("spack load --first "+package)
    if not useSpack:
        useSpack = True
    spackString=spackString+" "+package

if useSpack:
    spackCommand="spack load --sh --first "+spackString
    print(spackCommand)
    spackEnv=check_output([spackCommand], shell=True, universal_newlines=True)
    spackEnv="eval "+spackEnv+" " 
printSysInfo(config)

checkSlurmAvailability(config)

systemq("rm -rf " + TAU_ROOT + "/" + config.arch)

system("which " + config.mpiCommand)

buildApps = build_app_list(
    useOpenMPOMPT=config.useOpenMPOMPT,
    cuda=config.cuda,
    rocm=config.rocm,
    level_zero=config.level_zero,
    minimal=config.minimal,
    python=config.python,
)

buildApps = filter_buildapps(buildApps, _args.tests)

buildApps = batchBuildTAU(config, buildApps)

#############

if config.mpiStartup != "":
    system(config.mpiStartup)

RunAllTests(config, buildApps)

if config.mpiShutdown != "":
    system(config.mpiShutdown)

end(0)
