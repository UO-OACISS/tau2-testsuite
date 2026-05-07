aix32 = Configuration("aix32", "rs6000")
aix32.baseConfig = ""
aix32.f90 = "-fortran=ibm"
#aix32.pdt = "-pdt=/usr/local/packages/pdtoolkit-3.17"
aix32.mpi = "-mpi"
aix32.mpiBefore = "poe"
# aix32.mpiAfter = "-hfile " + TEST_ROOT + "/host.list -procs 4"
aix32.mpiAfter = "-procs 4"
aix32.papi = "-papi=/usr/local/packages/papi-3.5.0"
# kojak doesn't seem to work on AIX (no `expert`)
# aix32.epilog = "-epilog=/usr/local/packages/kojak-2.2"
# aix32.path = "/usr/local/packages/kojak-2.2/bin"
aix32.makeExtra = " -j"
aix32.makeline = "gmake clean; gmake"
aix32.path = "/usr/java5_64/bin"
aix32.tauMake = "gmake"
aix32.mpiCommand = "poe"
aix32.useEBS = False
aix32.downloadBFD = False

aix64 = Configuration("aix64", "ibm64")
aix64.baseConfig = "-arch=ibm64"
aix64.f90 = "-fortran=ibm64"
#aix64.pdt = "-pdt=/usr/local/packages/pdtoolkit-3.17"
aix64.mpi = "-mpi"
aix64.mpiBefore = "poe"
# aix64.mpiAfter = "-hfile " + TEST_ROOT + "/host.list -procs 4"
aix64.mpiAfter = "-procs 4"
aix64.papi = "-papi=/usr/local/packages/papi-3.5.0"
# doesn't work
# aix64.epilog = "-epilog=/usr/local/packages/kojak-2.1.1"
# doesn't work
# aix64.epilog = "-epilog=/usr/local/packages/kojak-2.1.1"
aix64.makeExtra = " -j"
aix64.makeline = "gmake clean; gmake"
aix64.path = "/usr/java5_64/bin"
aix64.tauMake = "gmake"
aix64.mpiCommand = "poe"
aix64.useEBS = False
aix64.downloadBFD = False

sunx86_64 = Configuration("sunx86_64", "sunx86_64")
sunx86_64.baseConfig = "-cc=cc -c++=CC -arch=sunx86_64"
sunx86_64.f90 = "-fortran=sun"
#sunx86_64.pdt = "-pdt=/usr/local/packages/pdtoolkit-3.17"
sunx86_64.mpi = "-mpiinc=/opt/SUNWhpc/HPC8.1/sun/include/amd64 -mpilib=/opt/SUNWhpc/HPC8.1/sun/lib/amd64"
sunx86_64.mpiBefore = "mpirun -np 4"
sunx86_64.mpiAfter = ""
sunx86_64.opari = "-opari"
sunx86_64.useTauExec = False

alulimGNU = ModuleConfiguration("alulimGNU", "x86_64")
alulimGNU.baseConfig = ""
alulimGNU.f90 = "-fortran=gfortran"
#alulimGNU.pdt = "-pdt=/home/wspear/bin/pdtoolkit-3.19"
# alulimGNU.mpi = "-mpiinc=/usr/local/packages/mpich2-1.0.6p1/pathscale-3.0/include -mpilib=/usr/local/packages/mpich2-1.0.6p1/pathscale-3.0/lib"
alulimGNU.mpi = "-mpi"
alulimGNU.mpiBefore = "mpirun -np 4"
alulimGNU.mpiAfter = ""
# alulimGNU.mpiStartup = "mpdallexit ; killall -9 mpd ; mpdcleanup ; mpd --ifhn=128.223.202.190 -d"
# alulimGNU.mpiShutdown = "mpdallexit ; killall -9 mpd ; mpdcleanup"
# alulimGNU.papi = "-papi=/home/wspear/bin/papi-4.1.2.1"
alulimGNU.papi = "-papi=/home/wspear/bin/papi-5.1.1"
# alulimGNU.modules = ["mpi/mpich2-1.0.6p1_pathscale-3.0", "pathscale"]

tank = ModuleConfiguration("tank", "x86_64")
tank.baseConfig = ""
tank.f90 = "-fortran=gfortran"
#tank.pdt = "-pdt=/usr/local/packages/pdtoolkit-3.17-tank"
tank.mpi = "-mpi"
tank.mpiBefore = "mpirun -np 4"
tank.mpiAfter = ""
tank.papi = "-papi=/usr/local/packages/papi-4.1.3/"
tank.scorep = "-scorep=/usr/local/packages/scorep-1.0.2 -bfd=download"
tank.ld_library_path = "/usr/local/packages/papi-4.1.3/lib64:/usr/local/packages/scorep-1.0.2/lib"
tank.modules = ["mpi-pbs/openmpi-1.5.3_gcc-4.6.1-64bit", "gcc/4.6.1", "java"]
# tank.modules = ["mpi-pbs/openmpi-1.4.3_gcc-4.3.5-64bit", "gcc/4.3.5", "java"]

tank_intel = ModuleConfiguration("tank_intel", "x86_64")
tank_intel.baseConfig = "-cc=icc -c++=icpc"
tank_intel.f90 = "-fortran=intel"
#tank_intel.pdt = "-pdt=/usr/local/packages/pdtoolkit-3.17-tank -pdtcompdir=intel"
tank_intel.mpi = "-mpi"
tank_intel.mpiBefore = "mpirun -np 4"
tank_intel.mpiAfter = ""
tank_intel.papi = "-papi=/usr/local/packages/papi-4.1.3/"
tank_intel.scorep = "-scorep=/usr/local/packages/scorep-1.0.2  -bfd=download"
tank_intel.ld_library_path = "/usr/local/packages/papi-4.1.3/lib64:/usr/local/packages/scorep-1.0.2/lib"
tank_intel.modules = ["mpi-pbs/openmpi-1.5.3_intel-12.0-64bit", "gcc", "java"]
tank_intel.hdf5 = "/usr/local/packages/hdf5-1.8.8/openmpi-1.5.3_intel-12.0-64bit/"
# tank_intel.execMemory=False
# tank_intel.opari="-----"


tank_pgi = ModuleConfiguration("tank_pgi", "x86_64")
tank_pgi.baseConfig = "-cc=pgcc -c++=pgCC"
tank_pgi.f90 = "-fortran=pgi"
#tank_pgi.pdt = "-pdt=/usr/local/packages/pdtoolkit-3.17-tank -pdtcompdir=pgi"
tank_pgi.mpi = "-mpi"
tank_pgi.mpiBefore = "mpirun -np 4"
tank_pgi.mpiAfter = ""
tank_pgi.papi = "-papi=/usr/local/packages/papi-4.1.3/"
tank_pgi.scorep = "-scorep=/usr/local/packages/scorep-1.0.2 -bfd=download"
tank_pgi.ld_library_path = "/usr/local/packages/papi-4.1.3/lib64:/usr/local/packages/scorep-1.0.2/lib"
tank_pgi.modules = ["mpi-pbs/openmpi-1.4.5_pgi-10.9-64bit", "gcc", "java", ]
tank_pgi.pdt_config = " -PGI "
tank_pgi.useOpenMPOMPT = False

vampire = ModuleConfiguration("vampire", "x86_64")
vampire.baseConfig = ""
vampire.f90 = "-fortran=gfortran"
#vampire.pdt = "-pdt=/usr/local/packages/pdtoolkit-3.17"
# vampire.cuda = "-cuda=/opt/cuda-4.0/"
# vampire.cupti = "-cupti=/usr/local/packages/cupti-4.0/CUPTI/"
# vampire.cudatestdir = "/usr/local/packages/systemtest/accelerator/cuda-4.0/bin/"
# vampire.ld_library_path="/opt/cuda-4.0/lib64:/usr/local/packages/cupti-4.0/CUPTI/lib"
# vampire.metrics=["CUDA.GeForce_GTX_480.domain_a.branch"]
vampire.mpi = "-mpi"
vampire.mpiBefore = "mpirun -np 4"
vampire.mpiAfter = ""
# vampire.modules = ["mpi-pbs/openmpi-1.5.3_gcc-4.6.1-64bit"]
vampire.modules = ["mpi-pbs/openmpi-1.5.2_gcc-4.4.5-64bit"]
vampire.hdf5 = "/usr/local/packages/hdf5-1.8.8/openmpi-1.5.2_gcc-4.4.5-64bit/"


#pegasus = ModuleConfiguration("pegasus", "x86_64")
#pegasus.baseConfig = ""
#pegasus.f90 = "-fortran=gfortran"
#manticore.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-3.24-manticore"
# "-pdt=/home/users/wspear/bin/pdtoolkit-3.21-manticore"
#pegasus.papi = "-papi=/packages/papi/5.4.3"
#pegasus.libunwind = "-unwind=download"
# /home/users/wspear/bin/libunwind-1.1/"
#pegasus.cuda = "-cuda=/usr/local/packages/cuda/9.2"
# /opt/cuda-4.0.11/"
# manticore.cupti = "-cupti=/opt/cupti-4.1alpha"
#pegasus.cudatestdir = "/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
# manticore.ld_library_path="/usr/local/packages/cuda/5.0.35/lib64/:/usr/local/packages/cuda/5.0.35/extras/CUPTI/lib64"
#pegasus.cudametrics = "CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
#pegasus.mpi = "-mpi"
#pegasus.mpiBefore = "mpirun -np 4"
#pegasus.mpiAfter = ""
#manticore.gomp = True
# pegasus.modules = ["mpi/openmpi-2.1_gcc-7.3", "cuda/9.2"]#, "gcc/4.8"]#["mpi-tor/openmpi-1.6.0_gcc-4.6.3", "cuda/5.0.35", "papi/5.0.1"] mpi-tor/openmpi-1.8_gcc-4.9  mpi-tor/openmpi-1.5.4_gcc-4.5.3 , "papi/5.4.3"

manticore = ModuleConfiguration("manticore", "x86_64")
manticore.baseConfig = ""
manticore.f90 = "-fortran=gfortran"
#manticore.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-3.24-manticore"
# "-pdt=/home/users/wspear/bin/pdtoolkit-3.21-manticore"
manticore.papi = "-papi=/storage/users/wspear/bin/SPACK/spack/opt/spack/linux-rhel6-westmere/gcc-4.9.3/papi-5.7.0-7zku2pkravrnadvs6zrduypi4qox256n"
manticore.libunwind = "-unwind=download"
# /home/users/wspear/bin/libunwind-1.1/"
manticore.cuda = "-cuda=/usr/local/packages/cuda/9.1"
# /opt/cuda-4.0.11/"
# manticore.cupti = "-cupti=/opt/cupti-4.1alpha"
manticore.cudatestdir = "/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
# manticore.ld_library_path="/usr/local/packages/cuda/5.0.35/lib64/:/usr/local/packages/cuda/5.0.35/extras/CUPTI/lib64"
manticore.cudametrics = "CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
manticore.mpi = "-mpi"
manticore.mpiBefore = "mpirun -np 4"
manticore.mpiAfter = ""
#manticore.gomp = True
# [ "openmpi-3.1.4-gcc-6.5.0-lcvlmxt", "gcc-6.5.0-gcc-8.3.0-ahapdwa", "zlib-1.2.11-gcc-6.5.0-nzhl3os" ,"cuda/9.1"]#,"mpi-tor/openmpi-1.8_gcc-4.9", "gcc/4.8"]#["mpi-tor/openmpi-1.6.0_gcc-4.6.3", "cuda/5.0.35", "papi/5.0.1"] mpi-tor/openmpi-1.8_gcc-4.9  mpi-tor/openmpi-1.5.4_gcc-4.5.3 , "papi/5.4.3"
manticore.modules = ["mpich-3.3.1-gcc-4.9.3-mf5jiip", "cuda/9.1"]

manticore_intel = ModuleConfiguration("manticore_intel", "x86_64")
manticore_intel.baseConfig = "-cc=icc -c++=icpc"
manticore_intel.f90 = "-fortran=intel"
#manticore_intel.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-3.24-manticore -pdtcompdir=intel"
# "-pdt=/home/users/wspear/bin/pdtoolkit-3.21-manticore"
manticore_intel.papi = "-papi=/packages/papi/5.4.3"
manticore_intel.libunwind = "-unwind=download"
# /home/users/wspear/bin/libunwind-1.1/"
manticore_intel.cuda = "-cuda=/usr/local/packages/cuda/7.5"
# /opt/cuda-4.0.11/"
#manticore_intel.cupti = "-cupti=/opt/cupti-4.1alpha"
manticore_intel.cudatestdir = "/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
manticore_intel.ld_library_path = "/home/users/wspear/bin/libunwind-1.1/lib"
manticore_intel.cudametrics = "CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
manticore_intel.mpi = "-mpi"
manticore_intel.mpiBefore = "mpirun -np 4"
manticore_intel.mpiAfter = ""
# ,,"mpi-tor/openmpi-1.8_intel-15" "gcc/4.8"] #mpi-tor/openmpi-1.5.5_intel-12.1.4  mpi-tor/openmpi-1.8_intel-15 , "papi/5.4.3"
manticore_intel.modules = ["mpi/mvapich2-2.2_intel-17", "cuda/7.5"]

manticore_pgi = ModuleConfiguration("manticore_pgi", "x86_64")
manticore_pgi.baseConfig = "-cc=pgcc -c++=pgc++"
manticore_pgi.f90 = "-fortran=pgi"
#manticore_pgi.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-cvs-manticore"
# manticore_pgi.pdt = "-pdt=/usr/local/packages/pdtoolkit-3.24/ -pdt_c++=g++"#"-pdt=/home/users/wspear/bin/pdtoolkit-3.24-manticore/ -pdtcompdir=pgi"
manticore_pgi.papi = "-papi=/packages/papi/5.4.3"
manticore_pgi.libunwind = "-unwind=download"
# /home/users/wspear/bin/libunwind-1.1/"
manticore_pgi.cuda = "-cuda=/usr/local/packages/cuda/7.5"
#" /opt/cuda-4.0.11/"
#manticore_pgi.cupti = "-cupti=/opt/cupti-4.1alpha"
manticore_pgi.cudatestdir = "/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
#manticore_pgi.ld_library_path = "/home/users/wspear/bin/libunwind-1.1/lib"
manticore_pgi.cudametrics = "CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
# "-mpi" -cc=mpicc -c++=mpicxx -fortran=mpif90
manticore_pgi.mpi = "-mpi -mpilibrary=\"-lmpi_usempif08 -lmpi_usempi_ignore_tkr -lmpi_mpifh -lmpi\""
manticore_pgi.mpiBefore = "mpirun -np 4"
manticore_pgi.mpiAfter = ""
# "mpi-tor/openmpi-1.8_pgi-14",, "gcc/4.8"] #mpi-tor/openmpi-1.6.3_pgi-12.10 mpi-tor/openmpi-1.7_pgi-13 , "papi/5.4.3" mpi-tor/openmpi-1.8_pgi-14  mpi-tor/openmpi-2.1_pgi-17
manticore_pgi.modules = ["mpi-tor/openmpi-1.10_pgi-16",
                                 "cuda/7.5", "binutils", "gcc/4.9"]
manticore_pgi.pdt_config = " -PGI "
manticore_pgi.useOpenMPOMPT = False

godzilla = ModuleConfiguration("godzilla", "x86_64")
godzilla.baseConfig = ""
godzilla.f90 = "-fortran=gfortran"
#manticore_pgi.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-cvs-manticore"
# godzilla.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-3.24-manticore/ -pdt_c++=g++"#-pdtcompdir=pgi" /usr/local/packages/gcc/4.9/bin/
godzilla.papi = "-papi=/packages/papi/5.4.3"
godzilla.libunwind = "-unwind=download"
# /home/users/wspear/bin/libunwind-1.1/"
#godzilla.cuda = "-cuda=/packages/cuda/10.2"
#" /opt/cuda-4.0.11/"
#manticore_pgi.cupti = "-cupti=/opt/cupti-4.1alpha"
# godzilla.cudatestdir="/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
#manticore_pgi.ld_library_path = "/home/users/wspear/bin/libunwind-1.1/lib"
# godzilla.cudametrics="CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
godzilla.mpi = "-mpi"
godzilla.mpiBefore = "mpirun -np 4"
godzilla.mpiAfter = ""
# binutils, "gcc/4.8"] #mpi-tor/openmpi-1.6.3_pgi-12.10 mpi-tor/openmpi-1.7_pgi-13 , "papi/5.4.3"
godzilla.modules = ["gcc-9.3.0-gcc-4.8.5-a6plyj6",
                            "mpich-3.3.2-gcc-9.3.0-zo67p4i", "java"]
godzilla.pdt_config = ""


godzilla_intel = ModuleConfiguration("godzilla_intel", "x86_64")
godzilla_intel.baseConfig = "-cc=icc -c++=icpc"
godzilla_intel.f90 = "-fortran=intel"
#manticore_pgi.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-cvs-manticore"
# godzilla_intel.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-3.24-manticore/ -pdt_c++=g++"#-pdtcompdir=pgi" /usr/local/packages/gcc/4.9/bin/
godzilla_intel.papi = "-papi=/packages/papi/5.4.3"
godzilla_intel.libunwind = "-unwind=download"
# /home/users/wspear/bin/libunwind-1.1/"
#godzilla_intel.cuda = "-cuda=/usr/local/packages/cuda/10.2"
#" /opt/cuda-4.0.11/"
#manticore_pgi.cupti = "-cupti=/opt/cupti-4.1alpha"
# godzilla_intel.cudatestdir="/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
#manticore_pgi.ld_library_path = "/home/users/wspear/bin/libunwind-1.1/lib"
# godzilla_intel.cudametrics="CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
godzilla_intel.mpi = "-mpi "  # "-mpi" -cc=mpicc -c++=mpicxx -fortran=mpif90
godzilla_intel.mpiBefore = "mpirun -np 4"
godzilla_intel.mpiAfter = ""
# , "gcc/4.8"] #mpi-tor/openmpi-1.6.3_pgi-12.10 mpi-tor/openmpi-1.7_pgi-13 , "papi/5.4.3"
godzilla_intel.modules = ["mpi/openmpi-4.0_intel-20", "java"]
godzilla_intel.pdt_config = " -icpc "


godzilla_pgi = ModuleConfiguration("godzilla_pgi", "x86_64")
godzilla_pgi.baseConfig = "-cc=pgcc -c++=pgc++"
godzilla_pgi.f90 = "-fortran=pgi"
#manticore_pgi.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-cvs-manticore"
# godzilla_pgi.pdt = "-pdt=/home/users/wspear/bin/pdtoolkit-3.24-manticore/ -pdt_c++=g++"#-pdtcompdir=pgi" /usr/local/packages/gcc/4.9/bin/
godzilla_pgi.papi = "-papi=/packages/papi/5.6.0"
godzilla_pgi.libunwind = "-unwind=download"
# /home/users/wspear/bin/libunwind-1.1/"
#godzilla_pgi.cuda = "-cuda=/usr/local/packages/cuda/9.1"
#" /opt/cuda-4.0.11/"
#manticore_pgi.cupti = "-cupti=/opt/cupti-4.1alpha"
# godzilla_pgi.cudatestdir="/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
#manticore_pgi.ld_library_path = "/home/users/wspear/bin/libunwind-1.1/lib"
# godzilla_pgi.cudametrics="CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
# -mpilibrary=\"-lmpi_usempif08 -lmpi_usempi_ignore_tkr -lmpi_mpifh -lmpi\"" #"-mpi" -cc=mpicc -c++=mpicxx -fortran=mpif90
godzilla_pgi.mpi = " -mpi "
godzilla_pgi.mpiBefore = "mpirun -np 4"
godzilla_pgi.mpiAfter = ""
# "mpi/openmpi-2.1_pgi-17" , "gcc/4.8"] #mpi-tor/openmpi-1.6.3_pgi-12.10 mpi-tor/openmpi-1.7_pgi-13 , "papi/5.4.3"
godzilla_pgi.modules = ["mpi/openmpi-3.1_pgi-19 ", "papi/5.6.0", "java"]
godzilla_pgi.pdt_config = " -PGI "
godzilla_pgi.useOpenMPOMPT = False



frankenstein_pgi = ModuleConfiguration("frankenstein_pgi", "x86_64")
frankenstein_pgi.baseConfig = "-cc=pgcc -c++=pgc++ -bfd=download"
frankenstein_pgi.f90 = "-fortran=pgi"
# frankenstein_pgi.pdt = "-pdt_c++=g++ -pdt=/usr/local/packages/pdtoolkit-3.24" #/usr/local/packages/gcc/4.9/bin/
frankenstein_pgi.papi = "-papi=/packages/papi/5.4.3"
frankenstein_pgi.libunwind = "-unwind=download"
frankenstein_pgi.cuda = "-cuda=/usr/local/packages/cuda/4.0/"
frankenstein_pgi.cupti = "-cupti=/usr/local/packages/cupti-4.0/CUPTI/"
frankenstein_pgi.cudatestdir = "/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
frankenstein_pgi.ld_library_path = "/usr/local/packages/cuda/4.0/lib64/:/usr/local/packages/cupti-4.0/CUPTI/lib"
frankenstein_pgi.metrics = ["CUDA.GeForce_GTX_480.domain_a.inst_issued"]
frankenstein_pgi.mpi = "-mpi -mpilibrary=\"-lmpi_usempif08 -lmpi_usempi_ignore_tkr -lmpi_mpifh -lmpi\""  # "-mpi"
frankenstein_pgi.mpiBefore = "mpirun -np 4"
frankenstein_pgi.mpiAfter = ""
# "mpi-tor/openmpi-2.1_pgi-17",
frankenstein_pgi.modules = ["cuda/8.0", "binutils",
                                    "mpi-tor/openmpi-1.8_pgi-14", "gcc/4.9"]
frankenstein_pgi.hdf5 = "/usr/local/packages/hdf5-1.8.8/openmpi-1.5.2_gcc-4.4.5-64bit/"
frankenstein_pgi.pdt_config = " -PGI "
frankenstein_pgi.useOpenMPOMPT = False

frankenstein = ModuleConfiguration("frankenstein", "x86_64")
frankenstein.baseConfig = "-bfd=download"
frankenstein.f90 = "-fortran=gfortran"
#frankenstein.pdt = "-pdt=/usr/local/packages/pdtoolkit-3.17"
frankenstein.cuda = "-cuda=/usr/local/packages/cuda/4.0/"
frankenstein.cupti = "-cupti=/usr/local/packages/cupti-4.0/CUPTI/"
frankenstein.cudatestdir = "/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
frankenstein.ld_library_path = "/usr/local/packages/cuda/4.0/lib64/:/usr/local/packages/cupti-4.0/CUPTI/lib"
frankenstein.metrics = ["CUDA.GeForce_GTX_480.domain_a.inst_issued"]
frankenstein.mpi = "-mpi"
frankenstein.mpiBefore = "mpirun -np 4"
frankenstein.mpiAfter = ""
frankenstein.modules = ["mpi-pbs/openmpi-1.5.2_gcc-4.4.5-64bit"]
frankenstein.hdf5 = "/usr/local/packages/hdf5-1.8.8/openmpi-1.5.2_gcc-4.4.5-64bit/"


hopperPGI = ModuleConfiguration("hopperPGI", "craycnl")
hopperPGI.baseConfig = "-arch=craycnl"
hopperPGI.f90 = ""
#hopperPGI.pdt = "-pdt=/global/homes/w/wspear/bin/pdtoolkit-3.17"
hopperPGI.papi = "-papi=/opt/cray/papi/4.2.0/perf_events/no-cuda/"
hopperPGI.mpi = "-mpi"
hopperPGI.modules = ["java", "papi/4.2.0"]
hopperPGI.mpiBefore = "aprun -n 4"
hopperPGI.mpiAfter = ""
hopperPGI.mpiCommand = "aprun"
hopperPGI.batchUpload = True
hopperPGI.useOpenMPOMPT = False

hopperCray = ModuleConfiguration("hopperCray", "craycnl")
hopperCray.baseConfig = "-arch=craycnl"
hopperCray.f90 = ""
#hopperCray.pdt = "-pdt=/global/homes/w/wspear/bin/pdtoolkit-3.17"
hopperCray.papi = "-papi=/opt/cray/papi/4.2.0/perf_events/no-cuda/"
hopperCray.mpi = "-mpi -DISABLESHARED"
hopperCray.modules = ["java", "papi/4.2.0"]
hopperCray.mpiBefore = "aprun -n 4"
hopperCray.mpiAfter = ""
hopperCray.mpiCommand = "aprun"
hopperCray.batchUpload = True

titanPGI = ModuleConfiguration("titanPGI", "craycnl")
titanPGI.baseConfig = "-arch=craycnl "
titanPGI.f90 = ""
#titanPGI.pdt = "-pdt=/ccs/home/wspear/bin/pdtoolkit-3.19"
titanPGI.papi = "-papi=/opt/cray/papi/5.0.1/perf_events/no-cuda/"
titanPGI.mpi = "-mpi -mpiinc=/opt/cray/mpt/5.6.3/gni/mpich2-pgi/119/include -mpilib=/opt/cray/mpt/5.6.3/gni/mpich2-pgi/119/lib"
titanPGI.modules = ["java", "papi/4.2.0"]
titanPGI.mpiBefore = "aprun -n 4"
titanPGI.mpiAfter = ""
titanPGI.mpiCommand = "aprun"
titanPGI.seqBefore = "aprun "
titanPGI.batchUpload = True
titanPGI.makeExtra = " -j "
# titanPGI.downloadBFD=False
titanPGI.modules = ["papi"]
titanPGI.basedir = "/tmp/work/wspear/"
titanPGI.useOpenMPOMPT = False

titanGNU = ModuleConfiguration("titanGNU", "craycnl")
titanGNU.baseConfig = "-arch=craycnl "
titanGNU.f90 = ""
#titanGNU.pdt = "-pdt=/ccs/home/wspear/bin/pdtoolkit-3.19"
titanGNU.papi = "-papi=/opt/cray/papi/5.0.1/perf_events/no-cuda/"
titanGNU.mpi = "-mpi -mpiinc=/opt/cray/mpt/5.6.3/gni/mpich2-pgi/119/include -mpilib=/opt/cray/mpt/5.6.3/gni/mpich2-pgi/119/lib"
titanGNU.modules = ["java", "papi/4.2.0"]
titanGNU.mpiBefore = "aprun -n 4"
titanGNU.mpiAfter = ""
titanGNU.mpiCommand = "aprun"
titanGNU.seqBefore = "aprun "
titanGNU.batchUpload = True
titanGNU.makeExtra = " -j "
# titanPGI.downloadBFD=False
titanGNU.modules = ["papi"]
titanGNU.basedir = "/tmp/work/wspear/"

titanCray = ModuleConfiguration("titanCray", "craycnl")
titanCray.baseConfig = "-arch=craycnl "
titanCray.f90 = ""
#titanCray.pdt = "-pdt=/ccs/home/wspear/bin/pdtoolkit-3.19 -pdt_c++=g++"
titanCray.papi = "-papi=/opt/cray/papi/5.0.1/perf_events/no-cuda/"
titanCray.mpi = "-mpi -mpiinc=/opt/cray/mpt/5.6.3/gni/mpich2-cray/74/include -mpilib=/opt/cray/mpt/5.6.3/gni/mpich2-cray/74/lib"
titanCray.modules = ["java", "papi/4.2.0"]
titanCray.mpiBefore = "aprun -n 4"
titanCray.mpiAfter = ""
titanCray.mpiCommand = "aprun"
titanCray.seqBefore = "aprun "
titanCray.batchUpload = True
titanCray.makeExtra = " -j "
titanCray.useOpari = False
# titanPGI.downloadBFD=False
titanCray.modules = ["papi"]
titanCray.basedir = "/tmp/work/wspear/"
titanCray.cuda = "-arch=craycnl -cuda=/opt/nvidia/cudatoolkit/5.0.35.102/ -cudalibrary=-L/opt/cray/nvidia/default/lib64"
titanCray.cudametrics = "CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"

surveyor = ModuleConfiguration("surveyor", "bgp")
surveyor.baseConfig = "-arch=bgp -BGPTIMERS"
surveyor.f90 = ""
#surveyor.pdt = "-pdt=/home/wspear/pvfs/bin/pdtoolkit-3.17/ -pdt_c++=xlC"
# surveyor.papi="-papi=/opt/cray/papi/4.1.4/perf_events/no-cuda/ -DISABLESHARED"
surveyor.mpi = "-mpi"
# surveyor.mpiBefore = "cobalt-mpirun -np 4"
surveyor.mpiBefore = "cqwait `qsub -A TAU -q default -n 4 -t 5"
surveyor.mpiAfter = "`"
# surveyor.seqBefore = "cobalt-mpirun -np 1"
surveyor.seqBefore = "cqwait `qsub -A TAU -q default -n 1 -t 5"
surveyor.seqAfter = "`"
surveyor.passEnv = True

windows = ModuleConfiguration("windows", "win32")
windows.baseConfig = ""

aciss_gnu = ModuleConfiguration("aciss_gnu", "x86_64")
aciss_gnu.baseConfig = ""
aciss_gnu.f90 = "-fortran=gfortran"
#aciss_gnu.pdt = "-pdt=/usr/local/packages/pdtoolkit-3.19"
aciss_gnu.mpi = "-mpi"
aciss_gnu.mpiBefore = "mpirun -np 4"
aciss_gnu.mpiAfter = ""
aciss_gnu.papi = "-papi=/usr/local/packages/papi/5.0.1/"
# aciss_gnu.scorep="-scorep=/usr/local/packages/scorep-1.0.2 -bfd=download"
# aciss_gnu.ld_library_path="/usr/local/packages/papi-4.1.3/lib64:/usr/local/packages/scorep-1.0.2/lib"
aciss_gnu.modules = ["mpi-tor/openmpi-1.5.4_gcc-4.5.3", "papi/5.0.1", "java"]

ubuntu64 = ModuleConfiguration("ubuntu64", "x86_64")
ubuntu64.baseConfig = ""
ubuntu64.f90 = "-fortran=gfortran"
#ubuntu64.pdt = "-pdt=/home/wspear/bin/pdtoolkit"
ubuntu64.papi = "-papi=/home/wspear/bin/papi-5.1.1"
# manticore.cuda = "-cuda=/usr/local/packages/cuda/5.0.35 -cudalibrary=\"-L/usr/lib64/nvidia/ -lcuda\" "
# /opt/cuda-4.0.11/"
# manticore.cupti = "-cupti=/opt/cupti-4.1alpha"
# manticore.cudatestdir="/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
# manticore.ld_library_path="/usr/local/packages/cuda/5.0.35/lib64/:/usr/local/packages/cuda/5.0.35/extras/CUPTI/lib64"
ubuntu64.cudametrics = "CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
ubuntu64.mpi = "-mpi"
ubuntu64.mpiBefore = "mpirun -np 4"
ubuntu64.mpiAfter = ""
ubuntu64.downloadBFD = False

# Configuration for testing TAU with MVAPICH
cerberusMVAPICH = ModuleConfiguration("cerberusMVAPICH", "x86_64")
cerberusMVAPICH.baseConfig = ""  # -tag=mvapich2 -c++=mpicxx -cc=mpicc"
#cerberusMVAPICH.f90 = "-fortran=mpif90"
#cerberusMVAPICH.pdt = "-pdt=/usr/local/packages/pdtoolkit-3.22"
cerberusMVAPICH.papi = ""
# -mpiinc=/usr/local/packages/mvapich2/1.9_gcc-4.4/include -mpilib=/usr/local/packages/mvapich2/1.9_gcc-4.4/lib"
cerberusMVAPICH.mpi = "-mpit -mpi"
#cerberusMVAPICH.mpiBefore = "mpirun -n 16"
cerberusMVAPICH.mpiAfter = ""
cerberusMVAPICH.opari = ""
cerberusMVAPICH.mpiCommand = "mpirun"
cerberusMVAPICH.seqBefore = "mpirun"
# --mca btl self,tcp --mca pml ob1   -np 4"
cerberusMVAPICH.mpiBefore = "mpirun -np 4"
cerberusMVAPICH.downloadBFD = True
cerberusMVAPICH.useOpari = False
cerberusMVAPICH.useEBS = False
#cerberusMVAPICH.basedir = "/tmp/work/sramesh"
#cerberusMVAPICH.path = "/usr/local/packages/mvapich2/bin"
#cerberusMVAPICH.ld_library_path = "/usr/local/packages/mvapich2/lib"
cerberusMVAPICH.execMemory = False
#cerberusMVAPICH.modules = [ "mpi/mvapich2-1.9_gcc-4.4" ]


# Configuration for testing TAU with MPC
cerberusMPC = ModuleConfiguration("cerberusMPC", "x86_64")
cerberusMPC.baseConfig = "-c++=mpc_cxx -cc=mpc_cc"
#cerberusMPC.f90 = "-fortran=mpc"
#cerberusMPC.pdt = "-pdt=/home/users/aurelem/tau/pdtoolkit-3.22.1"
#cerberusMPC.papi = ""
#cerberusMPC.mpi = "-mpit -mpi -mpiinc=/usr/local/packages/mvapich2/include -mpilib=/usr/local/packages/mvapich2/lib"
cerberusMPC.mpi = "-mpi"
#cerberusMPC.mpiBefore = "mpirun -n 16"
cerberusMPC.mpiAfter = ""
cerberusMPC.opari = ""
#cerberusMPC.papi = "-papi=/packages/papi/5.5.1"
cerberusMPC.metrics = ""
cerberusMPC.mpiCommand = "mpcrun"
cerberusMPC.seqBefore = "mpcrun"
cerberusMPC.downloadBFD = True
cerberusMPC.useOpari = False
cerberusMPC.useEBS = False
#cerberusMPC.basedir = "/tmp/work/sramesh"
#cerberusMPC.path = "/home/users/aurelem/mpc/mpc2_devel_install/x86_64/x86_64/bin"
#cerberusMPC.ld_library_path = "/home/users/aurelem/mpc/mpc2_devel_install/x86_64/x86_64/lib"
cerberusMPC.execMemory = False


cyclops = ModuleConfiguration("cyclops", "ibm64linux")
cyclops.baseConfig = ""
cyclops.f90 = "-fortran=gfortran"
cyclops.pdt_config = " -GNU "
cyclops.papi = "-papi=/usr/local/packages/papi/5.7.0"
cyclops.libunwind = "-unwind=download"
cyclops.cuda = "-cuda=/usr/local/cuda-10.1"
cyclops.cudatestdir = "/home/users/scottb/NVIDIA_GPU_Computing_SDK/C/bin/linux/release/"
cyclops.cudametrics = "CUDA.Tesla_M2070.domain_d.warps_launched:CUDA.Tesla_M2070.domain_d.active_cycles"
cyclops.mpiAfter = ""
cyclops.modules = [ "cuda/10.1", "cmake"] #"openmpi/4.0.1-gcc7.3" "openmpi/4.0.1-gcc10.1",
