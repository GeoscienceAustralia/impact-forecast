#!/bin/bash
#PBS -Pw85
#PBS -qexpress
#PBS -N hazimp
#PBS -m ae
#PBS -M craig.arthur@ga.gov.au
#PBS -lwalltime=02:00:00
#PBS -lmem=16GB,ncpus=16,jobfs=4000MB
#PBS -joe
#PBS -lstorage=gdata/w85
#PBS -v INITTIME

# This job script is used to run the `hazimp.py`
# script on gadi. It has been tailored for use in the
# Impact-based Forecasting for the Coastal Zone Project, which means
# some of the paths and file names are specific to that project
#
#  * To use: 
#  - Ensure there is a correctly specified HazImp configuration
#    file at /g/data/w85/BNHCRC/configuration/hazimp/
#  - make appropriate changes to the PBS options above, specifically
#    consider: 
#
#    #PBS -M <email address>
#    #PBS -lwalltime
#
#  - submit the job with the appropriate value of EVENTID, eg:
#     `qsub -v INITTIME=2019052600 run_hazimp.sh`
# 
# Contact:
# Craig Arthur, craig.arthur@ga.gov.au
# 2020-05-28

module purge
module load pbs
module load dot

module load python3/3.7.4
module load netcdf/4.6.3
module load hdf5/1.10.5
module load geos/3.8.0
module load proj/6.2.1
module load gdal/3.0.2 
module load openmpi/4.0.1

# Need to ensure we get the correct paths to access the local version of gdal bindings. 
# The module versions are compiled against Python3.6, so we can't use them
export PYTHONPATH=/g/data/w85/.local/lib/python3.7/site-packages:$PYTHONPATH

# Add the local Python-based scripts to the path:
export PATH=/g/data/w85/.local/bin:$PATH

# Needs to be resolved, but this suppresses an error related to HDF5 libs
export HDF5_DISABLE_VERSION_CHECK=2

SOFTWARE=/g/data/w85/software

# Add HazImp code to the path:
export PYTHONPATH=$SOFTWARE/hazimp:$PYTHONPATH

cd $SOFTWARE/hazimp/

module list
DATE=`date +%Y%m%d%H%M`

CONFIGFILE=/g/data/w85/BNHCRC/configuration/hazimp/$INITTIME.yaml
OUTPUT=/g/data/w85/BNHCRC/impact/$INITTIME

echo $PYTHONPATH
echo $CONFIGFILE

# Ensure output directory exists. If not, create it:
if [ ! -d "$OUTPUT" ]; then
   mkdir $OUTPUT
fi

if [ ! -f "$CONFIGFILE" ]; then
    echo "Configuration file does not exist:"
    echo $CONFIGFILE
    exit 1
fi

# Run the complete simulation:
python3 $SOFTWARE/hazimp/hazimp/main.py -c $CONFIGFILE > $OUTPUT/$INITTIME.stdout.$DATE 2>&1

cd $OUTPUT
cp $CONFIGFILE ./$INITTIME.$DATE.yaml

