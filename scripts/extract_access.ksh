#!/bin/bash -l
#$ -S /bin/ksh

DATE='20191021'
TIME='12'

## Load Mars and Grib modules (these are for data from late 2016)
module load mars/2.0.3 # for mars
module load bomGribTools/2.0.3 # for g2nc2 conversion
module load grib_table_data/NMOC_1.0.2

## Load python modules
#. /g/ns/rd/rdshare/modules/enable
#module load python/2.7.13
#module load gcc/6.3.0

## Create MARS extraction scripts

cat > MARS_extract_pressure_level_data << EOF_p
RETRIEVE,
    CLASS      = OD,
    TYPE       = FC, # analysis, FC for forecast
    STREAM     = ACCESS-SY,
    EXPVER     = 0001,
    LEVTYPE    = PL, # pressure levels, SFC for surface
    DATABASE   = marsop,
    LEVELIST   = 900,
    PARAM      = 132/131,
    DATE       = ${DATE},
    TIME       = ${TIME},
    STEP       = 06/12/18/24/30/36,
    TARGET     = '/cw/flush/dwilke/fc_p.grb' # name of the output file in grib2 format, then convert to netcdf with g2nc2
EOF_p

cat > MARS_extract_surface_level_data << EOF_sfc
RETRIEVE,
    CLASS      = OD,
    TYPE       = FC, # analysis, FC for forecast
    STREAM     = ACCESS-SY,
    EXPVER     = 0001,
    LEVTYPE    = sfc, # pressure levels, SFC for surface
    DATABASE   = marsop,
    PARAM      = 165/166/49/228061,
    DATE       = ${DATE},
    TIME       = ${TIME},
    STEP       = 06/12/18/24/30/36,
    TARGET     = '/cw/flush/dwilke/fc_sfc.grb' # name of the output file in grib2 format, then convert to netcdf with g2nc2
EOF_sfc

# cat > MARS_extract_surface_level_data_an << EOF_sfc
# RETRIEVE,
    # CLASS      = OD,
    # TYPE       = AN, # analysis, FC for forecast
    # STREAM     = ACCESS-SY,
    # EXPVER     = 0001,
    # LEVTYPE    = sfc, # pressure levels, SFC for surface
    # DATABASE   = marsop,
    # PARAM      = 228156,
    # DATE       = ${DATE},
    # TIME       = ${TIME},
    # TARGET     = '/cw/flush/dwilke/an_sfc.grb' # name of the output file in grib2 format, then convert to netcdf with g2nc2
# EOF_sfc

## Extract data from MARS

echo 'Extracting data from MARS'
mars MARS_extract_surface_level_data
mars MARS_extract_pressure_level_data
#mars MARS_extract_surface_level_data_an


## Convert grib data to NetCDF
echo 'Converting from grib to netcdf'
g2nc2 /cw/flush/dwilke/fc_sfc.grb /cw/flush/dwilke/fc_slvl_${DATE}_${TIME}.nc
g2nc2 /cw/flush/dwilke/fc_p.grb /cw/flush/dwilke/fc_plvl_${DATE}_${TIME}.nc
#g2nc2 /cw/flush/dwilke/an_sfc.grb /cw/flush/dwilke/an_sfc.nc

rm /cw/flush/dwilke/fc_sfc.grb
rm /cw/flush/dwilke/fc_p.grb