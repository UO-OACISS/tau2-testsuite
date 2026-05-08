import os

configurations = {}

class Configuration:
    def __init__(self, name, arch):
        self.name = name
        self.description = ""
        self.arch = arch
        self.path = ""
# I think -j is causing the intermittant compile problems
        self.makeExtra = " -j"
#        self.makeExtra = ""
        self.f90 = ""
        self.mpiStartup = ""
        self.mpiShutdown = ""
        self.papi = ""
        self.mpi = ""
        self.mpiBefore = ""
        self.mpiAfter = ""
        self.epilog = ""
        self.ld_library_path = ""
        self.opari = "-openmp -opari"  # -oparicomp=gnu"
        self.makeline = "make clean ; make"
        self.scorep = ""
        self.cuda = ""
        self.cupti = ""
        self.metrics = "PAPI_L1_DCM"
        self.cudametrics = ""
        self.cudatestdir = ""
        self.rocm = ""
        self.oneapi=""
        self.path = ""
        self.hdf5 = "/usr/local/packages/hdf5-1.8.6/"
        self.tauMake = "make"
        self.mpiCommand = "mpirun"
        self.seqBefore = ""
        self.seqAfter = ""
        self.envVarsExport = set([])
        self.passEnv = False
        self.batchUpload = False
        self.useTauExec = True
        self.useEBS = True
        self.noShared = False
        self.useOpari = True
        self.regressionTime = ""
        self.regressionDate = ""
        self.downloadBFD = True
        self.execMemory = True
        self.gomp = False
        self.perfetto = True
        self.libunwind = ""
        self.basedir = ""
        self.runroot = "/tmp/regression"
        self.gitHash = ""
        self.pdt = "-pdt=${TAU_ROOT}/../pdtoolkit"
        self.pdt_config = ""
        self.build_pdt = True
        self.useOpenMPOMPT = True  # Turn this off for PGI!
        self.cleanBFD=False #Turn this on for PGI/NVHPC. We need to configure tau without pgi to get a successful binutils build
        self.minimal=False
        self.otf2="-otf=download"
        self.useropt=" -syscall  -useropt=-g\\ -Og"
        self.opencl=""
        self.level_zero=""
        self.opencl=""
        self.spack = []
        self.envVars = {}
        self.url = ""
        self.remoteHome = ""  # set in scripts/local_settings.py
        configurations[self.name]=self

    def prepare(self):
        pass
    def purge(self):
        pass


class ModuleConfiguration(Configuration):
    def __init__(self, name, arch):
        Configuration.__init__(self, name, arch)
        self.modules = []

    def purge(self,):
        import envmod
        print("<b><pre>" + os.getcwd() + "> module purge</pre></b>")
        envmod.modcommand("purge")
    def prepare(self,):
        import envmod
        for mod in self.modules:
            loaded = os.environ.get('LOADEDMODULES', '').split(':')
            action = 'load'
            for prefix in envmod._EXCLUSIVE_PREFIXES:
                if mod.startswith(prefix):
                    conflict = next(
                        (m for m in loaded
                         if m == prefix[:-1] or m.startswith(prefix)),
                        None
                    )
                    if conflict and conflict != mod:
                        action = 'swap ' + conflict
                        break
            print("<b><pre>" + os.getcwd() +
                  "> module " + action + " " + mod + "</pre></b>")
            envmod.smart_load(mod)




pegasus = ModuleConfiguration("pegasus", "x86_64")
pegasus.baseConfig = ""
pegasus.f90 = "-fortran=gfortran"
#manticore_pgi.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-cvs-manticore"
# pegasus.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-3.24-manticore/ -pdt_c++=g++"#-pdtcompdir=pgi" /usr/local/packages/gcc/4.9/bin/
pegasus.papi = "-papi=/packages/papi/6.0.0.1" #/packages/papi/5.6.0"
pegasus.libunwind = "-unwind=download"
# /home/users/wspear/bin/libunwind-1.1/"
#pegasus.cuda = "-cuda=/packages/cuda/10.2"
#" /opt/cuda-4.0.11/"
#manticore_pgi.cupti = "-cupti=/opt/cupti-4.1alpha"
# pegasus.cudatestdir="/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
#manticore_pgi.ld_library_path = "/home/users/wspear/bin/libunwind-1.1/lib"
# pegasus.cudametrics="CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
pegasus.mpi = "-mpi"
pegasus.mpiBefore = "mpirun -np 4"  # --mca btl self,tcp --mca pml ob1 -np 4"
pegasus.mpiAfter = ""
# "mpi/openmpi-4.0.1_gcc-8.1","gcc-9.3.0-gcc-4.8.5-a6plyj6", "mpich-3.3.2-gcc-9.3.0-zo67p4i",  binutils, "gcc/4.8"] #mpi-tor/openmpi-1.6.3_pgi-12.10 mpi-tor/openmpi-1.7_pgi-13 , "papi/5.4.3"
#pegasus.modules = ["gcc/10.2.0"] #"mpi/openmpi-3.1.1_gcc-7.3",  "papi/5.6.0", "java"]
pegasus.pdt_config = ""
pegasus.spack = [ "mpich%gcc" ] #, "python@:2" ]
pegasus.url = "pegasus.nic.uoregon.edu"


pegasus_intel = ModuleConfiguration("pegasus_intel", "x86_64")
pegasus_intel.baseConfig = "-cc=icx -c++=icpx"
pegasus_intel.f90 = "-fortran=intel"
#manticore_pgi.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-cvs-manticore"
# pegasus_intel.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-3.24-manticore/ -pdt_c++=g++"#-pdtcompdir=pgi" /usr/local/packages/gcc/4.9/bin/
pegasus_intel.papi = "-papi=/packages/papi/6.0.0.1" #/packages/papi/5.6.0"
pegasus_intel.libunwind = "-unwind=download"
# /home/users/wspear/bin/libunwind-1.1/"
#pegasus_intel.cuda = "-cuda=/usr/local/packages/cuda/10.2"
#" /opt/cuda-4.0.11/"
#manticore_pgi.cupti = "-cupti=/opt/cupti-4.1alpha"
# pegasus_intel.cudatestdir="/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
#manticore_pgi.ld_library_path = "/home/users/wspear/bin/libunwind-1.1/lib"
# pegasus_intel.cudametrics="CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
pegasus_intel.mpi = "-mpi "  # "-mpi" -cc=mpicc -c++=mpicxx -fortran=mpif90
# --mca btl self,tcp --mca pml ob1  -np 4" #--mca btl self,tcp --mca pml ob1 -np 4"
pegasus_intel.mpiBefore = "mpirun -genv I_MPI_OFI_PROVIDER TCP  -np 4"
pegasus_intel.mpiAfter = ""
# , "mpi/openmpi-4.0_intel-20" "gcc/4.8"] #mpi-tor/openmpi-1.6.3_pgi-12.10 mpi-tor/openmpi-1.7_pgi-13 , "papi/5.4.3","mpi/openmpi-4.0_intel-20","mpi/openmpi-2.1_intel-18"
pegasus_intel.spack = ["intel-oneapi-compilers","intel-oneapi-mpi" ] #, "python@:2"]#"mpi/openmpi-2.1_intel-18", "papi/5.6.0", "java", "gcc/7.3"]
#pegasus_intel.modules = ["papi/5.6.0", "java", "gcc/8.1", "mpi/openmpi-4.0_intel-20"]
pegasus_intel.pdt_config = " -icpx "
pegasus_intel.url = "pegasus.nic.uoregon.edu"


pegasus_pgi = ModuleConfiguration("pegasus_pgi", "x86_64")
pegasus_pgi.baseConfig = "-cc=pgcc -c++=pgc++"
pegasus_pgi.f90 = "-fortran=pgi"
#manticore_pgi.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-cvs-manticore"
# pegasus_pgi.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-3.24-manticore/ -pdt_c++=g++"#-pdtcompdir=pgi" /usr/local/packages/gcc/4.9/bin/
pegasus_pgi.papi = "-papi=/packages/papi/5.6.0"
pegasus_pgi.libunwind = "-unwind=download"
# /home/users/wspear/bin/libunwind-1.1/"
#pegasus_pgi.cuda = "-cuda=/usr/local/packages/cuda/8.0"
#" /opt/cuda-4.0.11/"
#manticore_pgi.cupti = "-cupti=/opt/cupti-4.1alpha"
# pegasus_pgi.cudatestdir="/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
#manticore_pgi.ld_library_path = "/home/users/wspear/bin/libunwind-1.1/lib"
# pegasus_pgi.cudametrics="CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
# "-mpi" -cc=mpicc -c++=mpicxx -fortran=mpif90
pegasus_pgi.mpi = "-mpi -mpilibrary=\"-lmpi_usempif08 -lmpi_usempi_ignore_tkr -lmpi_mpifh -lmpi\""
pegasus_pgi.mpiBefore = "mpirun -np 4"
pegasus_pgi.mpiAfter = ""
# , "gcc/4.8"] #mpi-tor/openmpi-1.6.3_pgi-12.10 mpi-tor/openmpi-1.7_pgi-13 , "papi/5.4.3"
pegasus_pgi.modules = ["mpi/openmpi-2.1_pgi-17",
                       "binutils",  "gcc/4.9", "java"]
pegasus_pgi.pdt_config = " -PGI "
pegasus_pgi.useOpenMPOMPT = False
pegasus_pgi.url = "pegasus.nic.uoregon.edu"


delphi = ModuleConfiguration("delphi", "x86_64")
delphi.baseConfig = ""
delphi.f90 = "-fortran=gfortran"
delphi.papi = "-papi=/packages/papi/6.0.0.1"
delphi.libunwind = "-unwind=download"
delphi.cuda = "-cuda=/packages/cuda/11.5.2"
#delphi.cupti = "-cupti=/packages/cuda/10.2/extras/CUPTI"
delphi.cudatestdir = "/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
#delphi.cudametrics = "CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
delphi.otf2 = "-otf=/mnt/beegfs/users/wspear/bin/SPACK/delphi/spack/opt/spack/linux-rhel8-broadwell/gcc-11.3.0/otf2-2.3-fkydc2k3wnlmrodb25bv72qam4rgrqpx"
delphi.mpi = "-mpi"
delphi.mpiBefore = "mpirun -np 4"
delphi.mpiAfter = ""
delphi.modules = [ "openmpi/4.0.6-gcc10.2", "cuda/11.5" ]
delphi.pdt_config = ""
delphi.spack = [ "python" ]
delphi.url = "delphi.nic.uoregon.edu"


delphi_intel = ModuleConfiguration("delphi_intel", "x86_64")
delphi_intel.baseConfig = "-cc=icx -c++=icpx"
delphi_intel.f90 = "-fortran=intel"
delphi_intel.papi = "-papi=/packages/papi/6.0.0.1"
delphi_intel.libunwind = "-unwind=download"
delphi_intel.otf2 = "-otf=/mnt/beegfs/users/wspear/bin/SPACK/delphi/spack/opt/spack/linux-rhel8-broadwell/gcc-11.3.0/otf2-2.3-fkydc2k3wnlmrodb25bv72qam4rgrqpx"
delphi_intel.cuda = "-cuda=/usr/local/packages/cuda/11.5.2"
#delphi_intel.cupti = "-cupti=/packages/cuda/10.2/extras/CUPTI"
delphi_intel.cudatestdir = "/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
#delphi_intel.cudametrics = "CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
delphi_intel.mpi = "-mpi "
delphi_intel.mpiBefore = "mpirun -genv I_MPI_OFI_PROVIDER TCP -np 4"
delphi_intel.mpiAfter = ""
# "mpi/openmpi-4.0_intel-20" "mpi/openmpi-2.1_intel-18"
delphi_intel.modules = [ "cuda/11.5" ]
delphi_intel.pdt_config = " -icpc "
delphi_intel.spack = [ "python", "intel-oneapi-compilers", "intel-oneapi-mpi" ] #"python@:2", (Why?)
delphi_intel.url = "delphi.nic.uoregon.edu"


delphi_pgi = ModuleConfiguration("delphi_pgi", "x86_64")
delphi_pgi.baseConfig = "-cc=pgcc -c++=pgc++"
delphi_pgi.f90 = "-fortran=pgi"
delphi_pgi.papi = "-papi=/packages/papi/5.6.0"
delphi_pgi.libunwind = "-unwind=download"
delphi_pgi.cuda = "-cuda=/usr/local/packages/cuda/10.2"
delphi_pgi.cudatestdir = "/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
#delphi_pgi.cudametrics = "CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
delphi_pgi.mpi = " -mpi "
delphi_pgi.mpiBefore = "mpirun -np 4"
delphi_pgi.mpiAfter = ""
delphi_pgi.modules = [ "gcc", "nvhpc/21.5%gcc@8.1.0",   #"mpi/openmpi-3.1_pgi-19 ",
                      "cuda/10.2", "papi/5.6.0", "java"]
delphi_pgi.pdt_config = " -PGI "
delphi_pgi.useOpenMPOMPT = False
delphi_pgi.cleanBFD=True
delphi_pgi.url = "delphi.nic.uoregon.edu"

yu = Configuration("yu", "x86_64")
yu.baseConfig = ""
yu.f90 = "-fortran=gfortran"
yu.mpi = "-mpi"
yu.mpiBefore = "mpirun -np 4"
yu.mpiAfter = ""
yu.papi = "-papi=/home/wspear/bin/papi-git"
#yu.useOpenMPOMPT = False
yu.makeExtra = " -j "
yu.url = "yu"
yu.remoteHome = "/home/wspear"

miniyu = Configuration("miniyu", "x86_64")
miniyu.baseConfig = ""
miniyu.f90 = "-fortran=gfortran"
miniyu.mpi = "-mpi"
miniyu.mpiBefore = "mpirun -np 4"
miniyu.mpiAfter = ""
miniyu.papi = "-papi=/home/wspear/bin/papi-git"
miniyu.useOpenMPOMPT = False
miniyu.makeExtra = " -j "
miniyu.minimal = True
miniyu.url = "yu"
miniyu.remoteHome = "/home/wspear"



tmpconfig = instinct = Configuration("instinct", "x86_64")
tmpconfig.baseConfig = ""
tmpconfig.f90 = "-fortran=gfortran"
tmpconfig.pdt_config = " -GNU "
tmpconfig.papi = "-papi=/storage/users/wspear/bin/SPACK/instinct/spack/opt/spack/linux-ubuntu22.04-zen3/gcc-11.4.0/papi-7.1.0-aannh6qrlqkimzdspn2btzglbwhhwfzw" #/packages/papi/6.0.0.1"
tmpconfig.libunwind = "-unwind=download"
#tmpconfig.rocm = "-roctracer=/opt/rocm/roctracer/ -rocprofiler=/opt/rocm/rocprofiler/ -rocm -cc=hipcc"
tmpconfig.mpiBefore = "mpirun -np 4 "
tmpconfig.mpi = "-mpi"
tmpconfig.useropt = " -useropt=-g\\ -O0 "
#\ -fPIE\ -fPIC
#tmpconfig.modules=["rocm/5.6.0"]
tmpconfig.url = "instinct.nic.uoregon.edu"


tmpconfig = instinct_rocm = ModuleConfiguration("instinct_rocm", "x86_64")
tmpconfig.baseConfig = "-c++=hipcc -cc=amdclang"
tmpconfig.f90 = "-fortran=amdflang"
tmpconfig.pdt_config = " -GNU "
tmpconfig.papi = "/storage/usersb/wspear/bin/SPACK/instinct/spack/opt/spack/linux-ubuntu22.04-zen3/gcc-11.4.0/papi-6.0.0.1-wolpsrjiqgxmmysdyd2nxmih2unpqdyz" # /packages/papi/6.0.0.1"
tmpconfig.libunwind = "-unwind=download"
tmpconfig.rocm = "-roctracer=/opt/rocm-5.2.0/roctracer/ -rocprofiler=/opt/rocm-5.2.0/rocprofiler/ -rocm"
tmpconfig.mpiBefore = "mpirun -np 4 "
tmpconfig.mpi = "-mpi"
#tmpconfig.useropt = " -useropt=-g3\ -Og"
tmpconfig.modules=["rocm/5.6.0"]
tmpconfig.spack = ["openmpi@4.1.5%rocmcc"]
tmpconfig.url = "instinct.nic.uoregon.edu"

tmpconfig = omnia_rocm = ModuleConfiguration("omnia_rocm", "x86_64")
tmpconfig.baseConfig = "-c++=hipcc -cc=amdclang"
tmpconfig.f90 = "-fortran=amdflang"
tmpconfig.pdt_config = " -GNU "
tmpconfig.papi = "-papi=/packages/papi/6.0.0.1" # /packages/papi/6.0.0.1"
tmpconfig.libunwind = "-unwind=download"
tmpconfig.rocm = "-roctracer=/opt/rocm-5.5.0/roctracer/ -rocprofiler=/opt/rocm-5.5.0/rocprofiler/ -rocm"
tmpconfig.mpiBefore = "mpirun -np 4 "
tmpconfig.mpi = "-mpi"
#tmpconfig.useropt = " -useropt=-g3\ -Og"
#tmpconfig.modules=[ "rocm/5.5.0" , "mpich/031021-llvm12" ]
#tmpconfig.spack = ["openmpi@4.1.5%rocmcc"]
tmpconfig.url = "omnia"



tmpconfig = sever = Configuration("sever", "x86_64")
tmpconfig.baseConfig = "-cc=icx -c++=icpx"
tmpconfig.f90 = "-fortran=intel"
tmpconfig.level_zero="-level_zero"
tmpconfig.opencl="-opencl"
#tmpconfig.pdt_config = " -GNU "
tmpconfig.papi = "-papi=/packages/papi/6.0.0.1"
tmpconfig.libunwind = "-unwind=download"
tmpconfig.mpiBefore = "mpirun -np 4 "
tmpconfig.mpi = "-mpi"
#tmpconfig.useropt = " -useropt=-g3\ -Og"
tmpconfig.url = "sever.nic.uoregon.edu"



tmpconfig = saturn = Configuration("saturn", "x86_64")
tmpconfig.baseConfig = ""
tmpconfig.f90 = "-fortran=gfortran"
tmpconfig.cuda = "-cuda=/packages/cuda/12.5.1"
#tmpconfig.level_zero="-level_zero"
#tmpconfig.opencl="-opencl"
#tmpconfig.pdt_config = " -GNU "
#tmpconfig.papi = "-papi=/packages/papi/6.0.0.1"
tmpconfig.libunwind = "-unwind=download"
tmpconfig.mpiBefore = "mpirun -np 4 "
tmpconfig.mpi = "-mpi"
#tmpconfig.useropt = " -useropt=-g3\ -Og"
tmpconfig.modules=[ "openmpi", "cuda/12.5" ]
tmpconfig.url = "saturn.nic.uoregon.edu"


tmpconfig = hopper1 = Configuration("hopper1", "arm64_linux")
tmpconfig.baseConfig = ""
tmpconfig.f90 = "-fortran=gfortran"
tmpconfig.cuda = "-cuda=/packages/cuda/12.5.1"
#tmpconfig.level_zero="-level_zero"
#tmpconfig.opencl="-opencl"
#tmpconfig.pdt_config = " -GNU "
#tmpconfig.papi = "-papi=/packages/papi/6.0.0.1"
#tmpconfig.libunwind = "-unwind=download" #TODO; FIX on arm64_linux
tmpconfig.mpiBefore = "mpirun -np 4 "
tmpconfig.mpi = "-mpi"
#tmpconfig.useropt = " -useropt=-g3\ -Og"
tmpconfig.modules=[ "openmpi", "cuda/12.5" ]
tmpconfig.url = "hopper1.nic.uoregon.edu"


tmpconfig = gilgamesh_nvhpc = ModuleConfiguration("gilgamesh_nvhpc", "craycnl")
# Use Cray PE wrappers (cc/CC) backed by PrgEnv-nvidia rather than spelling out
# nvc/nvc++ explicitly and fighting with a spack gcc-built mpich.  With
# PrgEnv-nvidia loaded, the PE wrappers front nvc/nvc++ and PE MPI is used
# directly, so mpicc -show correctly reports nvc.
tmpconfig.baseConfig = "-c++=CC -cc=cc -pdt_c++=g++"
tmpconfig.f90 = "-fortran=nvfortran"
tmpconfig.pdt_config = " -GNU "
tmpconfig.papi = "-papi=/packages/papi/6.0.0.1"
#tmpconfig.libunwind = "-unwind=download"
tmpconfig.mpiBefore = "srun -p greece  -n 4"
tmpconfig.mpi = "-mpi"
tmpconfig.useropt = " -useropt=-g\\ -O2"
tmpconfig.modules=[ "craype-x86-rome", "PrgEnv-nvidia", "gcc/12.2.0" ] #, "nvhpc/23.5" ]
# No spack mpich: use Cray PE MPI (cray-mpich) so mpicc/mpicxx wrap nvc/nvc++
tmpconfig.cleanBFD=True
tmpconfig.envVars={'EXTRA_FFLAGS':'-noswitcherror'}
tmpconfig.url = "gilgamesh.nic.uoregon.edu"
tmpconfig.runroot = "/home/users/wspear/regression"

tmpconfig = gary = ModuleConfiguration("gary", "craycnl")
tmpconfig.baseConfig = "-c++=CC -cc=cc"  #-c++=nvc++ -cc=nvc -pdt_c++=g++"
#tmpconfig.f90 = "-fortran=nvfortran" 
#-tmpconfig.pdt_config = " -GNU "
tmpconfig.papi = "-papi=/packages/papi/6.0.0.1"
#tmpconfig.libunwind = "-unwind=download"
#tmpconfig.rocm = "-roctracer=/opt/rocm-5.2.0/roctracer/ -rocprofiler=/opt/rocm-5.2.0/rocprofiler/ -rocm"
tmpconfig.mpiBefore = "srun  -n 4 " #--mca btl self,tcp  --mca orte_base_help_aggregate 0
tmpconfig.mpi = "-mpi"
tmpconfig.useropt = " -useropt=-g\\ -O2"
tmpconfig.mpiCommand = "srun"
tmpconfig.envVars={'DEFAULT_FFLAGS':'-O3'}
tmpconfig.url = "gary.nic.uoregon.edu"
tmpconfig.runroot = "/home/users/wspear/regression"
#tmpconfig.modules=[ "craype-x86-rome", "PrgEnv-nvhpc", "gcc/12.2.0",  "nvhpc/23.5"  ]  #"gcc/12.2"]  #"nvhpc/22.11"]
#tmpconfig.spack=[  "nvhpc+mpi" ] #, "mpich%nvhpc"   ]  #"/2v5nfh", "/uvtby3g"]   #"mpich%nvhpc@22.11"]
#tmpconfig.cleanBFD=True

