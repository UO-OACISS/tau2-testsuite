import os, string, subprocess

#if 'MODULE_VERSION' not in os.environ:
#        os.environ['MODULE_VERSION_STACK'] = '3.2.3'
#        os.environ['MODULE_VERSION'] = '3.2.3'
#else:
#        os.environ['MODULE_VERSION_STACK'] = os.environ['MODULE_VERSION']
#
#if 'MODULESHOME' not in os.environ:
#        os.environ['MODULESHOME'] = '/usr/local/packages/modules/Modules/3.2.3';


#modScript='/init/python.py'
#if 'LMOD_ROOT' in os.environ:
#        modScript='/init/env_modules_python.py'

if 'MODULESHOME' not in os.environ and 'LMOD_ROOT' not in os.environ:
        # Some platforms set MODULESHOME only in interactive shells (.bashrc)
        # rather than login shells (.bash_profile).  Ask a login shell for it.
        try:
                _r = subprocess.run(
                        ['bash', '-l', '-c',
                         'echo "MODULESHOME=${MODULESHOME:-} LMOD_ROOT=${LMOD_ROOT:-}"'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        universal_newlines=True, timeout=10
                )
                for _tok in _r.stdout.split():
                        _k, _, _v = _tok.partition('=')
                        if _k in ('MODULESHOME', 'LMOD_ROOT') and _v:
                                os.environ[_k] = _v
        except Exception:
                pass

#if 'LMOD_ROOT' in os.environ:
#        modScript='/init/env_modules_python.py'
if 'LMOD_ROOT' in os.environ:
    modScript = '/init/env_modules_python.py'
else:
    modScript = '/init/python.py'

if 'MODULESHOME' in os.environ:
        fullModScript=os.environ['MODULESHOME']+modScript
        import warnings
        with warnings.catch_warnings():
                warnings.simplefilter('ignore', SyntaxWarning)
                exec(open(fullModScript).read())
else:
        import sys
        print('WARNING: envmod: MODULESHOME not found; module loading will be skipped.', file=sys.stderr)
        def module(command, *args):
                print('WARNING: module system unavailable; skipping: module %s %s' % (command, ' '.join(args)), file=sys.stderr)


#if 'MODULEPATH' not in os.environ:
#        os.environ['MODULEPATH'] = os.popen("""sed 's/#.*$//' ${MODULESHOME}/init/.modulespath | awk 'NF==1{printf("%s:",$1)}'""").readline()


#if 'LOADEDMODULES' not in os.environ:
#        os.environ['LOADEDMODULES'] = '';


def modcommand(command, *arguments):
        module(command, " ".join(arguments))


# Module families where only one member may be loaded at a time.
# Each entry is a tuple of prefixes/exact-names belonging to the same exclusive
# family.  When loading a module matching any family, any currently-loaded
# module in that same family will be swapped out rather than attempting a plain
# load (which would fail or silently misbehave).
_EXCLUSIVE_FAMILIES = (
        ('PrgEnv-',),
        ('craype-network-',),
        ('cray-mpich',),
        ('gcc/', 'gcc-native/', 'gcc-native'),
)


def _matches_family(modname, family):
        for pat in family:
                base = pat.rstrip('-/')
                if modname == base or modname.startswith(pat):
                        return True
        return False


def smart_load(modname):
        """Load a module, swapping out any conflicting module in the same
        exclusive family.  Falls back to a plain 'module load' when no
        conflict is detected."""
        loaded = [m for m in os.environ.get('LOADEDMODULES', '').split(':') if m]
        for family in _EXCLUSIVE_FAMILIES:
                if _matches_family(modname, family):
                        conflict = next(
                                (m for m in loaded if _matches_family(m, family)),
                                None
                        )
                        if conflict and conflict != modname:
                                module('swap', conflict, modname)
                                return
                        break
        module('load', modname)
#        modulecmd = '%s/bin/modulecmd' % os.environ['MODULESHOME']
#        if not os.path.isfile(modulecmd): 
#                whichproc = subprocess.Popen(['which', 'modulecmd'],stdout=subprocess.PIPE )
#                modulecmd = whichproc.stdout.read().rstrip();
#        commands = os.popen('%s python %s %s' % (modulecmd, command, "".join(arguments))).read()
#        exec( commands )

