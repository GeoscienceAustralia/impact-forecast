#!/bin/bash -l
#$ -N PFT_daily
#$ -S /bin/ksh

## Set run flags for individual components of the script.  Value of 1 causes the component to run
##    This is for testing purposes.  All run flags should be set to 1 when the script is operational

START_CLEAN=1        # Remove the previous work directory and start afresh
MARS_RUN=1           # Extract data from MARS
GRIB2NET=1           # Convert data extrated from MARS (grib format) to NetCDF
PYTH_VTS=1           # Run the first application of the python plotting script
PYTH_NSW=1
PYTH_SA=1
PYTH_WA=1
PYTH_QLD=1
PYTH_AUS=1
EMAIL=1              # E-mail pdf files to interested parties
CLEANUP=1            # Remove week-old files from the file storage

## Set python and fortran directories
PYTHON=/home/toryk/pyroCb/Python
FORTRAN=/home/toryk/pyroCb/HeatFluxDiagnostic
MOD=/apps/Modules/modulefiles

STORE=/home/toryk/pyroCb/PlotStore

## Make work directory
WRKDIR=/home/toryk/WORK
if [ $START_CLEAN -eq 1 ]; then
  rm -fr ${WRKDIR}
fi
mkdir -p ${WRKDIR}

## Copy fortran code and python scripts to work directory
PYTHON_SCRIPT=plot_heatflux.py
cp ${FORTRAN}/fortranbit.so $WRKDIR
cp ${PYTHON}/${PYTHON_SCRIPT} $WRKDIR
cp ${PYTHON}/Australia_medium.mat $WRKDIR

CDATE=`date +%Y%m%d`
CTIME=`date +%k`
echo 'Current date and time' ${CDATE} ${CTIME}

### Determine the date and time four hours ago (This should be enough time for ACCESS-R to run.)
DATE=`date --date='4 hour ago' +%Y%m%d`
HOUR=`date --date='4 hour ago' +%k`

### Calculate the most recent run (00, 06, 12, 18)
REM=$(( HOUR % 6 ))           # This is a modulus function
## typeset -Z2 TIME              # Ensure time is a 2-digit number $$$ Doesn't seem to work anymore
TIME=$(( HOUR - REM ))

###DATE=20190124
###TIME=0000

echo 'Model date and time' ${DATE} ${TIME}

## Go to the work directory
cd $WRKDIR

## Load Mars and Grib modules (these are for data from late 2016)
module load mars/2.0.3 # for mars
module load bomGribTools/2.0.3 # for g2nc2 conversion
module load grib_table_data/NMOC_1.0.2

## Load python modules
. /g/ns/rd/rdshare/modules/enable
module load python/2.7.13
module load gcc/6.3.0

## Load imagemagick
module load imagemagick

## Create MARS extraction scripts

cat > MARS_extract_pressure_level_data << EOF_p
RETRIEVE,
    CLASS      = OD,
    TYPE       = FC, # analysis, FC for forecast
    STREAM     = ACCESS-R,
    EXPVER     = 0001,
    LEVTYPE    = PL, # pressure levels, SFC for surface
    DATABASE   = marsop,
    LEVELIST   = 100/150/175/200/225/250/275/300/350/400/450/500/600/700/750/800/850/900/925/950/975/1000,
    PARAM      = 132/157/130/134/131,
    DATE       = ${DATE},
    TIME       = ${TIME},
    STEP       = 06/12/18/24/30/36,
    TARGET     = 'fc_p.grb' # name of the output file in grib2 format, then convert to netcdf with g2nc2
EOF_p

cat > MARS_extract_surface_level_data << EOF_sfc
RETRIEVE,
    CLASS      = OD,
    TYPE       = FC, # analysis, FC for forecast
    STREAM     = ACCESS-R,
    EXPVER     = 0001,
    LEVTYPE    = sfc, # pressure levels, SFC for surface
    DATABASE   = marsop,
    PARAM      = 165/166/81/167/134,
    DATE       = ${DATE},
    TIME       = ${TIME},
    STEP       = 06/12/18/24/30/36,
    TARGET     = 'fc_sfc.grb' # name of the output file in grib2 format, then convert to netcdf with g2nc2
EOF_sfc

cat > MARS_extract_surface_level_data_an << EOF_sfc
RETRIEVE,
    CLASS      = OD,
    TYPE       = AN, # analysis, FC for forecast
    STREAM     = ACCESS-R,
    EXPVER     = 0001,
    LEVTYPE    = sfc, # pressure levels, SFC for surface
    DATABASE   = marsop,
    PARAM      = 228156,
    DATE       = ${DATE},
    TIME       = ${TIME},
    TARGET     = 'an_sfc.grb' # name of the output file in grib2 format, then convert to netcdf with g2nc2
EOF_sfc

## Extract data from MARS
if [ $MARS_RUN -eq 1 ]; then
  echo 'Extracting data from MARS'
  mars MARS_extract_surface_level_data
  mars MARS_extract_pressure_level_data
  mars MARS_extract_surface_level_data_an
fi

## Convert grib data to NetCDF
if [ $GRIB2NET -eq 1 ]; then
  echo 'Converting from grib to netcdf'
  g2nc2 fc_sfc.grb fc_sfc.nc
  g2nc2 fc_p.grb fc_p.nc
  g2nc2 an_sfc.grb an_sfc.nc
fi
## Run PFT plotter
if [ $PYTH_VTS -eq 1 ]; then
  echo 'Running python script Vic-Tas'
  python ${PYTHON_SCRIPT} 140.5 151.5 -44.0 -33.0

  ## Create low-resolution pdf output file
  convert  -scale '65%' PFT_*.png PFT_${DATE}_${TIME}_lo_VTS.pdf
  convert  -scale '65%' PFT2_*.png PFT2_${DATE}_${TIME}_lo_VTS.pdf

  ## Copy output files to storage
  echo 'Copying image files to storage'
  cp *lo_VTS.pdf $STORE
fi

if [ $PYTH_NSW -eq 1 ]; then
  echo 'Running python script NSW'
  python ${PYTHON_SCRIPT} 141.0 154.0 -39.0 -26.0

  ## Create low-resolution pdf output file
  convert  -scale '65%' PFT_*.png PFT_${DATE}_${TIME}_lo_NSW.pdf
  convert  -scale '65%' PFT2_*.png PFT2_${DATE}_${TIME}_lo_NSW.pdf

  ## Copy output files to storage
  echo 'Copying image files to storage'
  cp *lo_NSW.pdf $STORE
fi

if [ $PYTH_WA -eq 1 ]; then
  echo 'Running python script WA'
  python ${PYTHON_SCRIPT} 113.0 126.0 -36.0 -23.0

  ## Create low-resolution pdf output file
  convert  -scale '65%' PFT_*.png PFT_${DATE}_${TIME}_lo_WA.pdf
  convert  -scale '65%' PFT2_*.png PFT2_${DATE}_${TIME}_lo_WA.pdf

  ## Copy output files to storage
  echo 'Copying image files to storage'
  cp *lo_WA.pdf $STORE
fi

if [ $PYTH_SA -eq 1 ]; then
  echo 'Running python script SA'
  python ${PYTHON_SCRIPT} 129.0 142.0 -39.0 -26.0

  ## Create low-resolution pdf output file
  convert  -scale '65%' PFT_*.png PFT_${DATE}_${TIME}_lo_SA.pdf
  convert  -scale '65%' PFT2_*.png PFT2_${DATE}_${TIME}_lo_SA.pdf

  ## Copy output files to storage
  echo 'Copying image files to storage'
  cp *lo_SA.pdf $STORE
fi

if [ $PYTH_QLD -eq 1 ]; then
  echo 'Running python script Qld'
  python ${PYTHON_SCRIPT} 137.0 154.0 -30.0 -13.0

  ## Create low-resolution pdf output file
  convert  -scale '65%' PFT_*.png PFT_${DATE}_${TIME}_lo_QLD.pdf
  convert  -scale '65%' PFT2_*.png PFT2_${DATE}_${TIME}_lo_QLD.pdf

  ## Copy output files to storage
  echo 'Copying image files to storage'
  cp *lo_QLD.pdf $STORE
fi

if [ $PYTH_AUS -eq 1 ]; then
  echo 'Running python script Aus'
  python ${PYTHON_SCRIPT} 112.7 153.7 -45.0 -4.0

  ## Create low-resolution pdf output file
  convert  -scale '65%' PFT_*.png PFT_${DATE}_${TIME}_lo_AUS.pdf
  convert  -scale '65%' PFT2_*.png PFT2_${DATE}_${TIME}_lo_AUS.pdf

  ## Copy output files to storage
  echo 'Copying image files to storage'
  cp *lo_AUS.pdf $STORE
fi



## E-mail low resolution output file
if [ $EMAIL -eq 1 ]; then
  cat > email_body.txt << EOF_emb
  Script initialised at ${CDATE} ${CTIME} for model run beginning ${DATE} ${TIME}
EOF_emb
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_VTS.pdf -a PFT2_${DATE}_${TIME}_lo_VTS.pdf kevin.tory@bom.gov.au < email_body.txt 
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_NSW.pdf -a PFT2_${DATE}_${TIME}_lo_NSW.pdf kevin.tory@bom.gov.au < email_body.txt
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_WA.pdf -a PFT2_${DATE}_${TIME}_lo_WA.pdf kevin.tory@bom.gov.au < email_body.txt
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_SA.pdf -a PFT2_${DATE}_${TIME}_lo_SA.pdf kevin.tory@bom.gov.au < email_body.txt
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_QLD.pdf -a PFT2_${DATE}_${TIME}_lo_QLD.pdf kevin.tory@bom.gov.au < email_body.txt
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_AUS.pdf -a PFT2_${DATE}_${TIME}_lo_AUS.pdf kevin.tory@bom.gov.au < email_body.txt

  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_NSW.pdf -a PFT2_${DATE}_${TIME}_lo_NSW.pdf zach.porter@bom.gov.au < email_body.txt
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_NSW.pdf -a PFT2_${DATE}_${TIME}_lo_NSW.pdf david.wilke@bom.gov.au < email_body.txt

  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_VTS.pdf -a PFT2_${DATE}_${TIME}_lo_VTS.pdf james.pescott@bom.gov.au < email_body.txt
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_NSW.pdf -a PFT2_${DATE}_${TIME}_lo_NSW.pdf james.pescott@bom.gov.au < email_body.txt
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_WA.pdf -a PFT2_${DATE}_${TIME}_lo_WA.pdf james.pescott@bom.gov.au < email_body.txt
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_SA.pdf -a PFT2_${DATE}_${TIME}_lo_SA.pdf james.pescott@bom.gov.au < email_body.txt
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_QLD.pdf -a PFT2_${DATE}_${TIME}_lo_QLD.pdf james.pescott@bom.gov.au < email_body.txt

  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_QLD.pdf -a PFT2_${DATE}_${TIME}_lo_QLD.pdf david.grant@bom.gov.au < email_body.txt

  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_VTS.pdf -a PFT2_${DATE}_${TIME}_lo_VTS.pdf kevin.parkyn@bom.gov.au < email_body.txt

  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_VTS.pdf -a PFT2_${DATE}_${TIME}_lo_VTS.pdf dean.sgarbossa@bom.gov.au < email_body.txt
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_NSW.pdf -a PFT2_${DATE}_${TIME}_lo_NSW.pdf dean.sgarbossa@bom.gov.au < email_body.txt
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_WA.pdf -a PFT2_${DATE}_${TIME}_lo_WA.pdf dean.sgarbossa@bom.gov.au < email_body.txt
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_SA.pdf -a PFT2_${DATE}_${TIME}_lo_SA.pdf dean.sgarbossa@bom.gov.au < email_body.txt
  mailx -s "PFT output" -a PFT_${DATE}_${TIME}_lo_QLD.pdf -a PFT2_${DATE}_${TIME}_lo_QLD.pdf dean.sgarbossa@bom.gov.au < email_body.txt

fi

## Remove older files to avoid filling the disk (repeat for 8-10 days ago in case script fails for a few days).
if [ $CLEANUP -eq 1 ]; then
  echo 'Removing 7--10 day-old files from storage'
  DATE7=`date --date='7 day ago' +%Y%m%d`
  DATE8=`date --date='8 day ago' +%Y%m%d`
  DATE9=`date --date='9 day ago' +%Y%m%d`
  DATE10=`date --date='10 day ago' +%Y%m%d`
  rm $STORE/PFT*_${DATE7}_*
  rm $STORE/PFT*_${DATE8}_*
  rm $STORE/PFT*_${DATE9}_*
  rm $STORE/PFT*_${DATE10}_*
fi
