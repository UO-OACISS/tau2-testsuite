import os

TAUOPTIONS = "TAU_OPTIONS"
TAUMAKE = "TAU_MAKEFILE"
mpi = "mpi"
opari = "opari"
cuda = "cuda"
phase = "phase"
pthread = "pthread"
vtf = "vtf"
scorep = "scorep"
openmp = "openmp"
rocm = "rocm"


def setEnviron(variable, value, config, runenv=True):
    print("<b><pre> export " +
          variable + "=\"" + value + "\"</pre></b>")
    if runenv:
        config.envVarsExport.add(variable)
    os.environ[variable] = value

def unsetEnviron(variable, config):
    print("<b><pre> unset " + variable + "</pre></b>")
    config.envVarsExport.discard(variable)
    os.environ.pop(variable, None)


class TauBuilder:
    def __init__(self, name):
        self.tauOptions = ["-optNoRevert", "-optVerbose"]
        self.name = name
        self.isShared = False

    def setTauOptions(self, config, stub):
        print("<details><summary><b>Set Build Environment</b></summary>")
        print( os.getcwd() + " >")
        envval = " ".join(self.tauOptions)
        #envval = "\"" + envval + "\""
        setEnviron(TAUOPTIONS, envval, config, False)
        setEnviron(TAUMAKE, stub, config, False)
        for key, value in config.envVars.items():
            setEnviron(key,value,config,False)
        print("</details>")

    def unsetTauOptions(self, config):
        print("<details><summary><b>Clear Build Environment</b></summary>")
        print( os.getcwd() + " >")
        unsetEnviron(TAUOPTIONS, config)
        unsetEnviron(TAUMAKE, config)
        for key, value in config.envVars.items():
            unsetEnviron(key,config)
        print("</details>")

profile = "profile"
merged = "merged"

class TauEnv:
    def __init__(self, name):
        self.name = name
        self.environment = {"TAU_TRACE": "1", "TAU_PROFILE": "1", "TAU_TRACK_MESSAGE": "1", "TAU_COMM_MATRIX": "1", "TAU_TRACK_IO_PARAMS": "1", "OMP_NUM_THREADS": "4", "SCOREP_PROFILING_FORMAT": "TAU_SNAPSHOT",
                            "TAU_THROTTLE_PERCALL": "50", "TAU_METRICS": "TIME", "TAU_CALLPATH": "1", "TAU_EBS_PERIOD": "5000"}  # , "TAU_EBS_UNWIND":"1"}  # ,"TAU_CALLSITE":"1","TAU_VERBOSE":"1", "TAU_TRACK_HEADROOM":"1","TAU_TRACK_HEAP":"1",
        # Set requiresMPI=True on environments that only apply to MPI tests (e.g. mergedEnv).
        self.requiresMPI = False
        # Set requiresPAPI=True on environments that require a PAPI-enabled build (e.g. papiEnv).
        self.requiresPAPI = False

    def isCompatibleWith(self, test, config):
        """Return False if this environment should be skipped for the given test and config."""
        if self.requiresMPI and not test.useMPI:
            return False
        if self.requiresPAPI and config.papi == "":
            return False
        return True

    def resolveFor(self, config, tauExec):
        """Return a resolved copy of the environment dict for this (config, tauExec) combination.

        This leaves self.environment unchanged and encodes all runtime decisions
        (metrics selection, trace suppression for EBS/memory, callsite availability)
        in the returned dict rather than in the driver loop.
        """
        env = dict(self.environment)
        # Metrics: GPU+CUDA builds use cuda-specific metrics; all others use standard metrics.
        if tauExec.gpu and config.cuda != "":
            env["TAU_METRICS"] = "TIME:" + config.cudametrics
        else:
            env["TAU_METRICS"] = "TIME:" + config.metrics
        # EBS and memory profiling are incompatible with tracing.
        if tauExec.useEBS or tauExec.useMemory:
            env["TAU_TRACE"] = "0"
        # Callsite unwinding requires libunwind.
        if config.libunwind == "":
            env["TAU_CALLSITE"] = "0"
        return env

    def setTauRunEnvironment(self, config, resolvedEnv=None):
        print("<details><summary><b>Set Run Environment</b></summary>")
        print(os.getcwd() + ">")
        env = resolvedEnv if resolvedEnv is not None else self.environment
        for var, val in env.items():
            setEnviron(var, val, config)
        print("</details>")

    def unsetTauRunEnvironment(self, config, resolvedEnv=None):
        print("<details><summary><b>Clear Run Environment</b></summary>")
        print(os.getcwd() + ">")
        env = resolvedEnv if resolvedEnv is not None else self.environment
        for var, val in env.items():
            unsetEnviron(var, config)
        print("</details>")

defaultEnv = TauEnv("defaultEnv")
mergedEnv = TauEnv("mergedEnv")
mergedEnv.requiresMPI = True

TAU_PROFILE_FORMAT = "TAU_PROFILE_FORMAT"
mergedEnv.environment[TAU_PROFILE_FORMAT] = "merged"
# These two options are currently incompatible!
mergedEnv.environment["TAU_TRACK_HEAP"] = "0"

callEnv = TauEnv("callEnv")
callEnv.environment["TAU_CALLPATH"] = "1"

compEnv = TauEnv("compEnv")
compEnv.environment["TAU_COMPENSATE"] = "1"

papiEnv = TauEnv("papiEnv")
papiEnv.requiresPAPI = True
papiEnv.environment["TAU_METRICS"] = "time:PAPI_L1_DCM"

otf2Env = TauEnv("otf2Env")
otf2Env.environment["TAU_TRACE_FORMAT"] = "OTF2"

perfettoEnv = TauEnv("perfettoEnv")
perfettoEnv.environment["TAU_TRACE_FORMAT"] = "PERFETTO"

mpitEnv = TauEnv("mpitEnv")
mpitEnv.environment["TAU_TRACK_MPI_T_PVARS"] = "1"
mpitEnv.environment["TAU_MPI_T_CVAR_METRICS"] = "MPIR_CVAR_VBUF_POOL_CONTROL,MPIR_CVAR_USE_BLOCKING,MPIR_CVAR_VBUF_POOL_REDUCED_VALUE[3]"
mpitEnv.environment["TAU_MPI_T_CVAR_VALUES"] = "1,1,21"

# :time:P_WALL_CLOCK_TIME:P_VIRTUAL_TIME

class TauExec:
    def __init__(self, tauExecArgs, name):
        self.tauExecArgs = tauExecArgs
        self.useTauExec = False
        self.useEBS = False
        self.useMemory = False
        self.name = name
        self.gpu = False
        self.gomp = False

    def tauExecCommands(self, libString, sharedBuild=True):
        if self.useTauExec == False:
            return ""
        memarg = ""
        if self.useMemory == True and sharedBuild == True:
            memarg = " -memory "
        if self.gomp == True:
            command = "tau_exec -gomp " + memarg + self.tauExecArgs + " -T " + libString
        else:
            command = "tau_exec " + self.tauExecArgs + " -T " + libString
        return command

# All tau test builds will be shared until further notice
DefaultTauBuild = TauBuilder("DefaultTauBuild")
DefaultTauBuild.tauOptions.append("-optShared")
DefaultTauBuild.isShared = True
CompInstTauBuild = TauBuilder("CompInstTauBuild")
CompInstTauBuild.tauOptions.append("-optCompInst")
CompInstTauBuild.tauOptions.append("-optShared")
CompInstTauBuild.isShared = True
#SharedTauBuild = TauBuilder("SharedTauBuild")
# SharedTauBuild.tauOptions.append("-optShared")
#SharedTauBuild.isShared = True

noExec = TauExec("", "noExec")
base = " -io "
# TEST LACK OF IO
#base = "" # -syscall  " #WARNING, WE MAY NEED THIS BACK
# if config.execMemory == True:
#    base = base + " -memory "
ioMemExec = TauExec(base + " -memory ", "ioMemExec")  # -memory
# ioMemExec=TauExec(" -io ","ioMemExec")
ioMemExec.useTauExec = True
ioMemExec.useMemory = True
base = base + "  -ebs "

#ioMemEbsExec = TauExec(base, "ioMemEbsExec")  # -memory
ioMemEbsExec=TauExec("-ebs -io -memory ","ioMemEbsExec")
ioMemEbsExec.useTauExec = True
ioMemExec.useMemory = True
ioMemEbsExec.useEBS = True


ebsExec = TauExec("  -ebs ", "ebsExec")  # -memory -syscall
# ioMemEbsExec=TauExec("-ebs -io ","ioMemEbsExec")
ebsExec.useTauExec = True
ebsExec.useEBS = True

#cudaExec = TauExec("-cuda", "cudaExec")
#cudaExec.useTauExec = True
#cudaExec.gpu = True
cuptiExec = TauExec(" -cupti", "cuptiExec") #-syscall
cuptiExec.useTauExec = True
cuptiExec.gpu = True

rocmExec = TauExec(" -rocm", "rocmExec") #-syscall
rocmExec.useTauExec = True

oneAPIExec = TauExec(" -l0", "oneAPIExec") #-syscall
oneAPIExec.useTauExec = True

class TestApp:
    def __init__(self, buildDir, binName, tauExample=False):
        self.tauExample=tauExample
        self.buildDir = buildDir
        self.binDir = buildDir
        self.binName = binName
        self.arguments = ""
        self.buildCommand = "make clean; make"

        # , SharedTauBuild] #All builds shared for now
        self.tauBuilders = [DefaultTauBuild, CompInstTauBuild]

        self.tauExec = [noExec, ioMemExec, ebsExec, ioMemEbsExec]  # ,ioMemExec ioMemEbsExec

        self.tauEnv = [defaultEnv, mergedEnv, otf2Env, perfettoEnv]  # compEnv, ,callEnv,papiEnv
        self.env = []
        self.useMPI = False
        self.useTauComp = False

class OutputTester:
    def __init__(self, testCommands):
        self.testCommands = testCommands

rocmTest = TestApp("gpu/roctx", "./MT", tauExample=True)
rocmTest.buildCommand = "hipcc MatrixTranspose.cpp -o MT -I/opt/rocm/roctracer/include/ -L/opt/rocm/roctracer/lib/ -lroctx64 -lroctracer64"
rocmTest.tauBuilders.remove(CompInstTauBuild)
rocmTest.tauExec.clear()
rocmTest.tauExec.append(rocmExec)

oneAPITest = TestApp("gpu/oneapi/complex_mult", "./complex_mult.exe", tauExample=True)
oneAPITest.buildCommand = "make"
oneAPITest.tauBuilders.remove(CompInstTauBuild)
oneAPITest.tauExec.clear()
oneAPITest.tauExec.append(oneAPIExec)

phaseTestCpp = TestApp("phase/c++", "./simple")
pthreadTestCpp = TestApp("threads_clean", "./hello", tauExample=True)
# pthreadTestCpp.tauExec.remove(ioMemExec)
# pthreadTestCpp.tauExec.remove(ioMemEbsExec)
pthreadTestCpp.useTauComp = True
minimalHello = TestApp("instrument_clean", "./simple", tauExample=True)
minimalHello.useTauComp = True

matmultF90 = TestApp("mm", "./matmult")
matmultF90.useMPI = True
matmultF90.useTauComp = True

mmC = TestApp("mm", "./matmult")
mmC.useMPI = True
mmC.useTauComp = True

matmultF90ProfileOnlyMPI = TestApp("mm", "./matmult")
matmultF90ProfileOnlyMPI.useMPI = True
matmultF90ProfileOnlyMPI.useTauComp = False
# matmultF90ProfileOnlyMPI.tauBuilders.remove(SharedTauBuild)
matmultF90ProfileOnlyMPI.tauExec.remove(ebsExec)
matmultF90ProfileOnlyMPI.tauEnv.remove(mergedEnv)
matmultF90ProfileOnlyMPI.tauBuilders.remove(CompInstTauBuild)
matmultF90ProfileOnlyMPI.tauExec.remove(ioMemExec)

# Add the MPIT environment here
matmultF90ProfileOnlyMPIWithMPIT = TestApp("mm", "./matmult")
matmultF90ProfileOnlyMPIWithMPIT.useMPI = True
matmultF90ProfileOnlyMPIWithMPIT.useTauComp = False
# matmultF90ProfileOnlyMPIWithMPIT.tauBuilders.remove(SharedTauBuild)
matmultF90ProfileOnlyMPIWithMPIT.tauExec.remove(ebsExec)
matmultF90ProfileOnlyMPIWithMPIT.tauEnv.remove(mergedEnv)
matmultF90ProfileOnlyMPIWithMPIT.tauBuilders.remove(CompInstTauBuild)
matmultF90ProfileOnlyMPIWithMPIT.tauExec.remove(ioMemExec)
matmultF90ProfileOnlyMPIWithMPIT.tauEnv.append(mpitEnv)

matmultF90Serial = TestApp("mm", "./matmult")
matmultF90Serial.useMPI = False
matmultF90Serial.useTauComp = True

gompWrapper = TestApp("gomp_wrapper", "./matmult")
gompWrapper.useMPI = False
gompWrapper.useTauComp = True

ompCxx = TestApp("openmp/multitask_openmp", "./multitask_openmp", tauExample=True)
ompCxx.useMPI = False
ompCxx.useTauComp = True

NPBBT = TestApp("NPB3.4-MPI", "./bin/bt.W.x", tauExample=True)
NPBBT.useMPI = True
NPBBT.useTauComp = True
NPBBT.buildCommand = "make clean; make bt NPROCS=4 CLASS=W"
# TESTING NPB ALONE
# NPBBT.tauBuilders.remove(DefaultTauBuild)
# NPBBT.tauExec.remove(noExec)
# NPBBT.tauExec.remove(ioMemExec)
# NPBBT.tauEnv.remove(defaultEnv)
# NPBBT.tauEnv.remove(mergedEnv)
# NPBBT.tauEnv.remove(callEnv)
# NPBBT.tauEnv.remove(compEnv)

cudaStream = TestApp("gpu/cuda/cuda_streaming", "./matmult", tauExample=True)
cudaStream.tauExec.remove(noExec)
cudaStream.tauExec.remove(ioMemExec)
cudaStream.tauExec.remove(ebsExec)
# cudaStream.tauExec.append(cudaExec)
cudaStream.tauExec.append(cuptiExec)
# Only shared seems to work so remove these two
#cudaStream.tauBuilders.remove(DefaultTauBuild)
cudaStream.tauBuilders.remove(CompInstTauBuild)

cudaOMP = TestApp("gpu/cuda/hybrid_omp_cuda", "./matmult", tauExample=True)
cudaOMP.tauExec.remove(noExec)
cudaOMP.tauExec.remove(ioMemExec)
cudaOMP.tauExec.remove(ebsExec)
# cudaOMP.tauExec.append(cudaExec)
cudaOMP.tauExec.append(cuptiExec)
# Only shared seems to work so remove these two
cudaOMP.tauBuilders.remove(DefaultTauBuild)
#cudaOMP.tauBuilders.remove(CompInstTauBuild)
cudaOMP.useTauComp = True

class TAUConfiguration:
    def __init__(self, arguments, execArgs, tests):
        self.arguments = arguments
        self.execArgs = execArgs
        self.tests = tests
        self.stub = ""


# ["NPB-MZ/BT","NPB-MZ/IS"])
OpariMPIConf = TAUConfiguration([mpi, opari], "OPARI", [matmultF90])
OpenMPMPIConf = TAUConfiguration([mpi, openmp], "OPENMP,OMPT", [
                                 matmultF90])  # ["NPB-MZ/BT","NPB-MZ/IS"])
# ["NPB-OMP/BT","NPB-OMP/IS"])
OpariConf = TAUConfiguration([opari], "SERIAL,OPARI", [
                             matmultF90Serial, ompCxx])
OpenMPConf = TAUConfiguration([openmp], "SERIAL,OPENMP,OMPT", [
                              ompCxx, matmultF90Serial, gompWrapper])  # ["NPB-OMP/BT","NPB-OMP/IS"])
MPIPthreadConf = TAUConfiguration([mpi, pthread], "PTHREAD", [matmultF90])

CudaConf = TAUConfiguration(
    [cuda, opari], "SERIAL,CUPTI,PDT,OPENMP,OPARI", [cudaStream, cudaOMP])
    
RocmConf = TAUConfiguration([rocm],"SERIAL,ROCM",[rocmTest])

oneAPIConf = TAUConfiguration(["level_zero"],"SERIAL,LEVEL_ZERO",[oneAPITest])

# ,PAPI "NPB-MPI/BT","NPB-MPI/IS"
MPIConf = TAUConfiguration([mpi], "MPI,PDT", [matmultF90, NPBBT])
#MVAPICHConf = TAUConfiguration([mpi], "MVAPICH2,MPI,PDT", [matmultF90ProfileOnlyMPI])

MVAPICHWithMPITConf = TAUConfiguration([mpi], "MVAPICH2,MPIT,MPI,PDT", [
                                       matmultF90ProfileOnlyMPIWithMPIT, matmultF90ProfileOnlyMPI])

MPCConf = TAUConfiguration([mpi], "MPI,PDT", [mmC])

# TESTING NPB ALONE
# MPIConf=TAUConfiguration([mpi],"MPI,PDT",[NPBBT])
# vtf,TRACE ,PAPI "NPB-SER/BT","NPB-SER/IS"
SerConf = TAUConfiguration([], "SERIAL,PDT", [minimalHello])
PhaseConf = TAUConfiguration([phase], "SERIAL,PHASE", [phaseTestCpp])
PThreadConf = TAUConfiguration([pthread], "SERIAL,PTHREAD", [
                               pthreadTestCpp, matmultF90Serial])

#ScorepConf = TAUConfiguration([scorep], "SCOREP,SERIAL", [minimalHello])



def build_app_list(useOpenMPOMPT=True, cuda="", rocm="", level_zero="", minimal=False):
    apps = [SerConf, PhaseConf, PThreadConf, OpariConf, MPIConf, OpariMPIConf]
    if useOpenMPOMPT:
        apps += [OpenMPConf, OpenMPMPIConf]
    if cuda:
        apps.append(CudaConf)
    if rocm:
        apps.append(RocmConf)
    if level_zero:
        apps.append(oneAPIConf)
    if minimal:
        apps = [SerConf]
    return apps



#system("which amdclang")

##################
# buildApps=[([mpi],["NPB-MPI/BT","NPB-MPI/IS"]),([mpi,opari],["NPB-MZ/BT","NPB-MZ/IS"]),([],["NPB-SER/BT","NPB-SER/IS"]),([opari],["NPB-OMP/BT","NPB-OMP/IS"]),([cuda],["CUDA"])([phase],["PHASE"])]
# buildApps=[MPIConf,OpenMPIConf,OMPConf,SerConf,CudaConf,PhaseConf]
# NORMAL
#buildApps = [SerConf, PhaseConf, PThreadConf, OpariConf, MPIConf, OpariMPIConf] #Redundant: MPIPthreadConf,  ScorepConf,
#buildApps = [PThreadConf]
#if config.useOpenMPOMPT is True:
#    buildApps.append(OpenMPConf)
#    buildApps.append(OpenMPMPIConf)
#if config.cuda:
#    buildApps.append(CudaConf)
	
#if config.rocm:
#    buildApps.append(RocmConf)
#if config.level_zero:
#    buildApps.append(oneAPIConf)

# MAKING MODIFICATIONS TO SUIT MY USE CASE
#if(config == configs.cerberusMVAPICH):
#    buildApps = [MVAPICHWithMPITConf]  # MVAPICHConf,
#if(config == configs.cerberusMPC):
#    buildApps = [MPCConf]
# PTHREADS:
# buildApps=[MPIPthreadConf,PThreadConf]
# TESTING MPI
# buildApps=[MPIConf]
# buildApps=[CudaConf]
#if config.minimal:
#    buildApps = [SerConf]
