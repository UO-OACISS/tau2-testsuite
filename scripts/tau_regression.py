#!/usr/bin/env python3

import sys
import os
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
    print("</HTML>\n")  # <PRE>
    sys.exit(errorsFound)

def usage():
    print("Usage: tau_regression.py <configuration> <run root path (optional)>")
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
    for x in config.envVarsExport:
        envString += '\'' + x + '=' + os.environ[x] + '\'' + ':'
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
        error("Error: failed to configure!")
        return retval
    retval = system(config.tauMake + " clean install" + config.makeExtra)
    #system("rm ./"+config.arch+"/lib/libTAU.so")
    if retval != 0:
        error("Error: failed to build TAU!")
    return retval

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
            error("Error: failed to configure!")
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
    # Resolve the absolute path now, while still in the test run directory.
    # Many tests share the same binary name (e.g. matmult); using the full path
    # matches coredumpctl's COREDUMP_EXE field, which is unique per test directory.
    abs_bin_path = os.path.abspath(bin_path)
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
        print(html.escape(f"coredumpctl: searching for exe={abs_bin_path} since={since_str}"))

        # Try --json=short first (systemd >= 248); fall back to text parsing for older systems.
        pids = []
        res = subprocess.run(
            ["coredumpctl", "--no-pager", "list", abs_bin_path, "--since", since_str, "--json=short"],
            capture_output=True, text=True)
        print(html.escape(f"coredumpctl --json=short exit={res.returncode}"))
        if res.stderr.strip():
            print(html.escape(res.stderr.strip()))
        if res.returncode == 0 and res.stdout.strip():
            for entry in json.loads(res.stdout):
                pids.append(str(entry['pid']))
        else:
            # Fallback: parse text output (works on systemd < 248).
            # Lines look like: "Wed 2026-05-06 12:17:42 PDT  3526136 ..."
            res2 = subprocess.run(
                ["coredumpctl", "--no-pager", "list", abs_bin_path, "--since", since_str],
                capture_output=True, text=True)
            print(html.escape(f"coredumpctl text fallback exit={res2.returncode}"))
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
                for tauTestBuild in tauTest.tauBuilders:
                    if tauTest.useTauComp == False and tauTestBuild is not DefaultTauBuild:
                        output("Build doesn't recognize TAU_OPTIONS. Skipping")
                        continue

                    output("Building with TAU Options: " +
                                 " ".join(tauTestBuild.tauOptions),"2","purple")
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
                                outputHeader("Running " + testName)
                                envSet.setTauRunEnvironment(config, resolvedEnv)
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
                                else:
                                    SaveCores(tauTest.binName, tauTest.buildDir + "_" +
                                              tauTestBuild.name + "_" + tauExec.name + "_" + envSet.name,
                                              test_start_time)
                                envSet.unsetTauRunEnvironment(config, resolvedEnv)

                    else:
                        warning("Build Failed, skipping Execution!")
                    tauTestBuild.unsetTauOptions(config)
        else:
            warning(tauBuild.execArgs + " not built! Skipping tests!")
######################################################################

args = sys.argv[1:]
if len(args) == 0:
    error("TEST NAME REQUIRED")
    sys.exit(1)

if len(args) > 2:
    usage()
    sys.exit(1)
    
selectedConfig = args[0]
dirsuf = "-" + selectedConfig

run_prefix = os.environ['HOME']
if len(args) > 1:
    run_prefix = args[1]

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


print("<HTML><head><meta charset=\"utf-8\"><style>\npre {\n    white-space: pre-wrap;       /* Since CSS 2.1 */\n    white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */\n    white-space: -pre-wrap;      /* Opera 4-6 */\n    white-space: -o-pre-wrap;    /* Opera 7 */\n    word-wrap: break-word;       /* Internet Explorer 5.5+ */\n}\n</style></head>\n")  # <PRE>

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
)

buildApps = batchBuildTAU(config, buildApps)

#############

if config.mpiStartup != "":
    system(config.mpiStartup)

RunAllTests(config, buildApps)

if config.mpiShutdown != "":
    system(config.mpiShutdown)

end(0)
