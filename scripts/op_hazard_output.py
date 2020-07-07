# -*- coding: utf-8 -*-
"""
Created on Wed Mar 13 10:45:13 2019

Script loads .nc data gathered from MARS (at this stage via twister) and
outputs hazard grids as separate .nc files computed over forecast 


@author: dwilke
"""

# -*- coding: utf-8 -*-
"""
Created on Tue Oct 22 2019

@author: dwilke
"""


import iris
import iris.pandas
import iris.analysis.cartography
from iris.cube import Cube
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as col
import matplotlib.ticker as tick
import iris.quickplot as qplt
import iris.plot as iplt
import os
import sys
import argparse
from pprint import pprint
from glob import glob as ls
import warnings
import numpy as np
import datetime
from iris.experimental.equalise_cubes import equalise_attributes
from iris.util import unify_time_units
import iris.coord_categorisation as ct
import time

import pandas as pd 
from pandas import DataFrame
import cf_units as unit
import datetime

import glob
import calendar
import datetime

"""
Key:

PIRR - (P)oint event max. (I)nstantaneous (R)ain-(R)ate
P1RR - (P)oint event max. (1)hr (R)ain-(R)ate
N1RR - (N)eighbourhood event max. (1)hr (R)ain-(R)ate
P6RR - (P)oint event max. (6)hr (R)ain-(R)ate
PTEA - (P)oint (T)otal (E)vent rainfall (A)ccumulation

PSWG - (P)oint (S)urface <10m> (W)ind (G)ust
PSMW - (P)oint (S)urface <10m> (M)ean (W)ind
NSWG - (N)eighbourhood (S)urface <10m> (W)ind (G)ust
PGWS - (P)oint (G)radient <900hPa> (W)ind (S)peed

"""

#%% Load all files and create base weather cubes:

file_sfc = 'fc_slvl_20191021_12.nc'
file_upp = 'fc_plvl_20191021_12.nc'
    
lat_S = -34.0
lat_N = -31.5
lon_W = 150.5
lon_E = 153.0 

lat_constraint = iris.Constraint(
            latitude = lambda cell: lat_S <= cell <= lat_N
        )
lon_constraint = iris.Constraint(
            longitude = lambda cell: lon_W <= cell <= lon_E
        )

fc_slvl = iris.load(file_sfc,lat_constraint & lon_constraint)
fc_plvl = iris.load(file_upp,lat_constraint & lon_constraint)

uwnd900 = fc_plvl[1]
vwnd900 = fc_plvl[0]

uwnd10m = fc_slvl[1]
vwnd10m = fc_slvl[0]
wg10m = fc_slvl[3]

# Regrid U onto V
interpolator = iris.analysis.Linear()
vwnd900 = vwnd900.regrid(uwnd900, interpolator)
vwnd10m = vwnd10m.regrid(uwnd10m, interpolator)

# Create a cube of wind speed at surface and 900hPa
ws900 = (uwnd900 ** 2 + vwnd900 ** 2) ** 0.5
ws10m = (uwnd10m ** 2 + vwnd10m ** 2) ** 0.5
ws900.rename('900hPa windspeed')
ws10m.rename('10m windspeed')

ws900 = ws900[:,0,:,:]

# Event maximum
# Point gradient wind speed (event max.)
PGWS = ws900.collapsed('time', iris.analysis.MAX)
# Point surface (10m) mean wind speed (event max.)
PSMW = ws10m.collapsed('time', iris.analysis.MAX)
# Point surface (10m) wind gust (event max.)
PSWG = wg10m.collapsed('time', iris.analysis.MAX)

# Calculate the neighbourhood max. wind gust:
NSWG = PSWG.copy()

print("No. of points:", NSWG.shape[0]*NSWG.shape[1])
for x_A in range (0,len(PSWG.coord('latitude').points)):
    print("Doing: ", x_A, " out of ", len(PSWG.coord('latitude').points))
    for y_A in range (0,len(PSWG.coord('longitude').points)):
        
        # Neighbourhood distance in degrees:
        D = 0.36
        
        # Determine lat/lon of point
        lat = PSWG.coord('latitude').points[x_A]
        lon = PSWG.coord('longitude').points[y_A]
        
        lat_constraintN = iris.Constraint(
            latitude = lambda cell: (lat-D) <= cell <= (lat+D)
        )
        lon_constraintN = iris.Constraint(
            longitude = lambda cell: (lon-D) <= cell <= (lon+D)
        )        
        
        # Slice cube to D * D square:
        current = PSWG.extract(lat_constraintN & lon_constraintN)
        # Save arrays of coordinates
        grid_lon, grid_lat = iris.analysis.cartography.get_xy_grids(current)
        # Determine degree distance point from (lon,lat) in numpy array
        rad = ((grid_lon-lon)**2 + (grid_lat-lat)**2)**0.5
        # Convert cube to df
        current_df = iris.pandas.as_data_frame(current, copy=True)
        # Determine max over region of interest:
        NSWG.data[x_A,y_A] = np.amax(np.where(rad<=D,1,0)*current_df.values)

# save files:
iris.save(PGWS, 'op_PGWS_10min.nc')
iris.save(PSMW, 'op_PSMW_10min.nc')
iris.save(PSWG, 'op_PSWG_10min.nc')
iris.save(NSWG, 'op_NSWG_10min.nc') 





# Load hrly files into cubes (at 900hPa level in lat/lon range):
# These files have no overlapping data:
uwnd900 = iris.load(files_u_prs,iris.Constraint(pressure=900) & lat_constraint & lon_constraint)
vwnd900 = iris.load(files_v_prs,iris.Constraint(pressure=900) & lat_constraint & lon_constraint)

# Load 10min files into cubes (in lat/lon range):
# Important- these files need to be sliced to remove the first timestep of each cube which overlaps 
rain = iris.load(files_rain,lat_constraint & lon_constraint)
uwnd10m = iris.load(files_u_10m,lat_constraint & lon_constraint)
vwnd10m = iris.load(files_v_10m,lat_constraint & lon_constraint)
gust = iris.load(files_gust,lat_constraint & lon_constraint)

# Clean and concatenate wind data (10min rain data needs to be re-cubed due to timing):
uwnd900 = clean_data(uwnd900)
uwnd900 = uwnd900.concatenate_cube()

vwnd900 = clean_data(vwnd900)
vwnd900 = vwnd900.concatenate_cube()

uwnd10m = clean_data(uwnd10m)
uwnd10m = remove_first_timestep(uwnd10m)
uwnd10m = uwnd10m.concatenate_cube()

vwnd10m = clean_data(vwnd10m)
vwnd10m = remove_first_timestep(vwnd10m)
vwnd10m = vwnd10m.concatenate_cube()

gust = clean_data(gust)
gust = remove_first_timestep(gust)
gust = gust.concatenate_cube()

# Regrid U onto V
interpolator = iris.analysis.Linear()
vwnd900 = vwnd900.regrid(uwnd900, interpolator)
vwnd10m = vwnd10m.regrid(uwnd10m, interpolator)

# Create a cube of wind speed
ws900 = (uwnd900 ** 2 + vwnd900 ** 2) ** 0.5
ws10m = (uwnd10m ** 2 + vwnd10m ** 2) ** 0.5
ws900.rename('900hPa windspeed')
ws10m.rename('10m windspeed')

# Create list of rain cube differences, removing first from each file
rain_list = iris.cube.CubeList([])
for i in range (0,len(rain)):
    print(i)
    for j in range (1,rain[i].shape[0]):
        current = rain[i][j,:,:]-rain[i][j-1,:,:]
        time_coord = iris.coords.DimCoord(rain[i].coord('time').bounds[j,1], standard_name='time', units='s')
        latitude_coord = current.coords('latitude')[0]
        longitude_coord = current.coords('longitude')[0]
        data = np.zeros((1,current.shape[0],current.shape[1]))
        data[0,:,:] = current.data
        cube = Cube(data, units="kg m-2", dim_coords_and_dims=[(time_coord, 0),(latitude_coord, 1),(longitude_coord, 2)])
        #cube.add_aux_coord(time_aux_coord)
        rain_list.append(cube)

rain = rain_list.concatenate_cube()

#%% Rain hazard grids:  

# Max 10min (instantaneous) rainfall rate: 
PIRR = rain.collapsed('time', iris.analysis.MAX) 

# Point total event accum
PTEA = rain.collapsed('time', iris.analysis.SUM)

# Calculate max 1hr rainfall rate:
N = len(rain.coord('time').points)
# Initialise empty list of cubes to store 6hr data:
cube_list_1hr = iris.cube.CubeList([])
# loop over cubes:
for i in range (3,N-2):
    time_start = iris.Constraint(
            time = lambda cell: cell >= rain.coord('time').cell(i-3)
        )
        
    time_end = iris.Constraint(
            time = lambda cell: cell <= rain.coord('time').cell(i+2)
        )

    # Find a cube with appropriate 1hr rainfall data
    current = rain.extract(time_start)
    current = current.extract(time_end)

    # Sum across 1hr to have one time dimension
    current = current.collapsed('time', iris.analysis.SUM)
    # add to list
    cube_list_1hr.append(current)

cube_1hr = cube_list_1hr.merge_cube() 

# Determine max 1hr rain-rate:
P1RR = cube_1hr.collapsed('time', iris.analysis.MAX)

# Calculate max 6hr rainfall rate:
# Initialise empty list of cubes to store 6hr data:
cube_list_6hr = iris.cube.CubeList([])
# loop over cubes:
for i in range (18,N-17):
    time_start = iris.Constraint(
            time = lambda cell: cell >= rain.coord('time').cell(i-18)
        )
        
    time_end = iris.Constraint(
            time = lambda cell: cell <= rain.coord('time').cell(i+17)
        )
    
    # Find a cube with appropriate 1hr rainfall data
    current = rain.extract(time_start)
    current = current.extract(time_end)

    # Sum across 6hrs to have one time dimension
    current = current.collapsed('time', iris.analysis.SUM)
    # add to list
    cube_list_6hr.append(current)

cube_6hr = cube_list_6hr.merge_cube() 

# Determine max 6hr rain-rate:
P6RR = cube_6hr.collapsed('time', iris.analysis.MAX)

# Determine the neighbourhood 1hr rain-rate:
N1RR = P1RR.copy()

print("No. of points:", N1RR.shape[0]*N1RR.shape[1])
for x_A in range (0,len(P1RR.coord('latitude').points)):
    print("Doing: ", x_A, " out of ", len(P1RR.coord('latitude').points))
    for y_A in range (0,len(P1RR.coord('longitude').points)):
        
        # Neighbourhood distance in degrees:
        D = 0.36
        
        # Determine lat/lon of point
        lat = P1RR.coord('latitude').points[x_A]
        lon = P1RR.coord('longitude').points[y_A]
        
        lat_constraintN = iris.Constraint(
            latitude = lambda cell: (lat-D) <= cell <= (lat+D)
        )
        lon_constraintN = iris.Constraint(
            longitude = lambda cell: (lon-D) <= cell <= (lon+D)
        )        
        
        # Slice cube to D * D square:
        current = P1RR.extract(lat_constraintN & lon_constraintN)
   
        # Save arrays of coordinates
        grid_lon, grid_lat = iris.analysis.cartography.get_xy_grids(current)
        # Determine degree distance point from (lon,lat) in numpy array
        rad = ((grid_lon-lon)**2 + (grid_lat-lat)**2)**0.5
        # Convert cube to df
        current_df = iris.pandas.as_data_frame(current, copy=True)
        # Determine max over region of interest:
        N1RR.data[x_A,y_A] = np.amax(np.where(rad<=D,1,0)*current_df.values)
   

#%% Wind hazard grids:

# Event maximum
# Point gradient wind speed (event max.)
PGWS = ws900.collapsed('time', iris.analysis.MAX)
# Point surface (10m) mean wind speed (event max.)
PSMW = ws10m.collapsed('time', iris.analysis.MAX)
# Point surface (10m) wind gust (event max.)
PSWG = gust.collapsed('time', iris.analysis.MAX)

# Calculate the neighbourhood max. wind gust:
NSWG = PSWG.copy()

print("No. of points:", NSWG.shape[0]*NSWG.shape[1])
for x_A in range (0,len(PSWG.coord('latitude').points)):
    print("Doing: ", x_A, " out of ", len(PSWG.coord('latitude').points))
    for y_A in range (0,len(PSWG.coord('longitude').points)):
        
        # Neighbourhood distance in degrees:
        D = 0.36
        
        # Determine lat/lon of point
        lat = PSWG.coord('latitude').points[x_A]
        lon = PSWG.coord('longitude').points[y_A]
        
        lat_constraintN = iris.Constraint(
            latitude = lambda cell: (lat-D) <= cell <= (lat+D)
        )
        lon_constraintN = iris.Constraint(
            longitude = lambda cell: (lon-D) <= cell <= (lon+D)
        )        
        
        # Slice cube to D * D square:
        current = PSWG.extract(lat_constraintN & lon_constraintN)
        # Save arrays of coordinates
        grid_lon, grid_lat = iris.analysis.cartography.get_xy_grids(current)
        # Determine degree distance point from (lon,lat) in numpy array
        rad = ((grid_lon-lon)**2 + (grid_lat-lat)**2)**0.5
        # Convert cube to df
        current_df = iris.pandas.as_data_frame(current, copy=True)
        # Determine max over region of interest:
        NSWG.data[x_A,y_A] = np.amax(np.where(rad<=D,1,0)*current_df.values)




#%% Determine rainfall 48hr to 09am 22/04/2015 (201504192300 to 201504212300)

# Convert a time to epoch time for slicing:
t_start = datetime.datetime(2015, 4, 19, 23)
t_end = datetime.datetime(2015, 4, 21, 23)
# Convert a time to epoch time for slicing:
t_start = (calendar.timegm(t_start.timetuple()))/60/60
t_end = (calendar.timegm(t_end.timetuple()))/60/60

time_constraint = iris.Constraint(
            time = lambda cell: t_start < cell.point <= t_end
        )

rain_sub = rain.extract(time_constraint)

# Point total event accum
PTEA_sub = rain_sub.collapsed('time', iris.analysis.SUM)


#%% Save/load files:

iris.save(rain, 'rain.nc')

iris.save(PIRR, 'dungog_PIRR_10min.nc')
iris.save(P1RR, 'dungog_P1RR_10min.nc')
iris.save(P6RR, 'dungog_P6RR_10min.nc')
iris.save(PTEA, 'dungog_PTEA_10min.nc')
iris.save(N1RR, 'dungog_N1RR_10min.nc')

iris.save(PGWS, 'dungog_PGWS_10min.nc')
iris.save(PSMW, 'dungog_PSMW_10min.nc')
iris.save(PSWG, 'dungog_PSWG_10min.nc')
iris.save(NSWG, 'dungog_NSWG_10min.nc')   

PIRR = iris.load_cube('dungog_PIRR_10min.nc')
P1RR = iris.load_cube('dungog_P1RR_10min.nc')
P6RR = iris.load_cube('dungog_P6RR_10min.nc')
PTEA = iris.load_cube('dungog_PTEA_10min.nc')
N1RR = iris.load_cube('dungog_N1RR_10min.nc')

PGWS = iris.load_cube('dungog_PGWS_10min.nc')
PSMW = iris.load_cube('dungog_PSMW_10min.nc')
PSWG = iris.load_cube('dungog_PSWG_10min.nc')
NSWG = iris.load_cube('dungog_NSWG_10min.nc')  


# Load files:
#P1RR_1hr = iris.load_cube('dungog_P1RR_1hr.nc')
#P6RR_1hr = iris.load_cube('dungog_P6RR_1hr.nc')
#PTEA_1hr = iris.load_cube('dungog_PTEA_1hr.nc')
#N1RR_1hr = iris.load_cube('dungog_N1RR_1hr.nc')

#%% Rain animation
print(len(rain.coord('time').points))
for i in range (0,len(rain.coord('time').points)):
    print(i)
    fig = plt.figure(i)
    plt.clf()
    title_text = "10min rainfall (%s UTC)" % (time.strftime('%m/%d/%Y %H:%M:%S',  time.gmtime(rain.coord('time').cell(i).point*60*60)))
    plt.suptitle(title_text)
# , brewer_cmap.N, cmap=brewer_cmap
    #plt.subplot(2,1,1)
    iplt.contourf(rain[i,:,:], np.arange(2,31,1))
    plt.gca().coastlines('10m')
    plt.plot(151.7524,-32.4047, color='red', marker='o')
    plt.plot(151.7817,-32.9283, color='red', marker='d')
    #plt.axis([145.5,151,-39, -35])
    #plt.xticks([146,148,150])
    #plt.yticks([-36,-38])
    #plt.plot(149.8191,-36.6722, color='blue', marker='.')
    #plt.plot(149.2336,-37.0016, color='red', marker='.')
    #plt.plot(146.9509,-36.0690, color='black', marker='.')
    #plt.title('Relative humidity')
    cbar=plt.colorbar(shrink=1)
    cbar.set_label('kg m-2')
    fig.set_size_inches(10,7)

    filename = "animation/rain_10min_%03d.png" % (i)
    plt.savefig(filename,dpi=150)
    plt.clf()    

#%% Gust animation
print(len(gust.coord('time').points))
for i in range (0,len(gust.coord('time').points)):
    print(i)
    fig = plt.figure(i)
    plt.clf()
    title_text = "Instantaneous 10m wind gust (%s UTC)" % (gust.coord('time').cell(i).point)
    plt.suptitle(title_text)
# , brewer_cmap.N, cmap=brewer_cmap
    #plt.subplot(2,1,1)
    iplt.contourf(gust[i,:,:], np.arange(5,60,1))
    plt.gca().coastlines('10m')
    plt.plot(151.7524,-32.4047, color='red', marker='o')
    plt.plot(151.7817,-32.9283, color='red', marker='d')
    #plt.axis([145.5,151,-39, -35])
    #plt.xticks([146,148,150])
    #plt.yticks([-36,-38])
    #plt.plot(149.8191,-36.6722, color='blue', marker='.')
    #plt.plot(149.2336,-37.0016, color='red', marker='.')
    #plt.plot(146.9509,-36.0690, color='black', marker='.')
    #plt.title('Relative humidity')
    cbar=plt.colorbar(shrink=1)
    cbar.set_label('m s-1')
    fig.set_size_inches(10,7)

    filename = "animation/gust_10min_%02d.png" % (i)
    plt.savefig(filename,dpi=150)
    plt.clf()

#% windspeed animation
print(len(ws10m.coord('time').points))
for i in range (0,len(ws10m.coord('time').points)):
    print(i)
    fig = plt.figure(i)
    plt.clf()
    title_text = "Instantaneous 10m windspeed (%s UTC)" % (ws10m.coord('time').cell(i).point)
    plt.suptitle(title_text)
# , brewer_cmap.N, cmap=brewer_cmap
    #plt.subplot(2,1,1)
    iplt.contourf(ws10m[i,:,:], np.arange(5,35,1))
    plt.gca().coastlines('10m')
    plt.plot(151.7524,-32.4047, color='red', marker='o')
    plt.plot(151.7817,-32.9283, color='red', marker='d')
    #plt.axis([145.5,151,-39, -35])
    #plt.xticks([146,148,150])
    #plt.yticks([-36,-38])
    #plt.plot(149.8191,-36.6722, color='blue', marker='.')
    #plt.plot(149.2336,-37.0016, color='red', marker='.')
    #plt.plot(146.9509,-36.0690, color='black', marker='.')
    #plt.title('Relative humidity')
    cbar=plt.colorbar(shrink=1)
    cbar.set_label('m s-1')
    fig.set_size_inches(10,7)

    filename = "animation/windspeed_10min_%02d.png" % (i)
    plt.savefig(filename,dpi=150)  
    
#% 900hpa windspeed animation
print(len(ws900.coord('time').points))
for i in range (0,len(ws900.coord('time').points)):
    print(i)
    fig = plt.figure(i)
    plt.clf()
    title_text = "Instantaneous 900hPa windspeed (%s UTC)" % (ws900.coord('time').cell(i).point)
    plt.suptitle(title_text)
# , brewer_cmap.N, cmap=brewer_cmap
    #plt.subplot(2,1,1)
    iplt.contourf(ws900[i,:,:], np.arange(5,35,1))
    plt.gca().coastlines('10m')
    plt.plot(151.7524,-32.4047, color='red', marker='o')
    plt.plot(151.7817,-32.9283, color='red', marker='d')
    #plt.axis([145.5,151,-39, -35])
    #plt.xticks([146,148,150])
    #plt.yticks([-36,-38])
    #plt.plot(149.8191,-36.6722, color='blue', marker='.')
    #plt.plot(149.2336,-37.0016, color='red', marker='.')
    #plt.plot(146.9509,-36.0690, color='black', marker='.')
    #plt.title('Relative humidity')
    cbar=plt.colorbar(shrink=1)
    cbar.set_label('m s-1')
    fig.set_size_inches(10,7)

    filename = "animation/windspeed_900hpa_%02d.png" % (i)
    plt.savefig(filename,dpi=150)      

#%% Compare:

fig = plt.figure(1)
plt.clf()
plt.suptitle('Rainfall hazard grids (10min data)')

plt.subplot(1,5,1)
qplt.contourf(PTEA, np.arange(20,560,20))
plt.gca().coastlines('10m')
plt.plot(151.7524,-32.4047, color='white', marker='o')
plt.plot(151.7817,-32.9283, color='white', marker='d')
#plt.axis([148,154,-36, -30])
#plt.xticks([148,150,152,154])
#plt.yticks([-38,-36,-34,-32,-30])
#plt.colorbar()
plt.title('Point total event accum.')

plt.subplot(1,5,2)
qplt.contourf(P6RR, np.arange(20,360,20))
plt.gca().coastlines('10m')
plt.plot(151.7524,-32.4047, color='white', marker='o')
plt.plot(151.7817,-32.9283, color='white', marker='d')
#plt.axis([148,154,-36, -30])
#plt.xticks([148,150,152,154])
#plt.yticks([-38,-36,-34,-32,-30])
#plt.colorbar()
plt.title('Point 6hr max. rain')

plt.subplot(1,5,3)
qplt.contourf(P1RR, np.arange(10,160,10))
plt.gca().coastlines('10m')
plt.plot(151.7524,-32.4047, color='white', marker='o')
plt.plot(151.7817,-32.9283, color='white', marker='d')
#plt.axis([148,154,-36, -30])
#plt.xticks([148,150,152,154])
#plt.yticks([-38,-36,-34,-32,-30])
#plt.colorbar()
plt.title('Point 1hr max. rain')

plt.subplot(1,5,4)
qplt.contourf(N1RR, np.arange(10,160,10))
plt.gca().coastlines('10m')
plt.plot(151.7524,-32.4047, color='white', marker='o')
plt.plot(151.7817,-32.9283, color='white', marker='d')
#plt.axis([148,154,-36, -30])
#plt.xticks([148,150,152,154])
#plt.yticks([-38,-36,-34,-32,-30])
#plt.colorbar()
plt.title('Neighbourhood 1hr max. rain')

plt.subplot(1,5,5)
qplt.contourf(PIRR, np.arange(0,40,5))
plt.gca().coastlines('10m')
plt.plot(151.7524,-32.4047, color='white', marker='o')
plt.plot(151.7817,-32.9283, color='white', marker='d')
#plt.axis([148,154,-36, -30])
#plt.xticks([148,150,152,154])
#plt.yticks([-38,-36,-34,-32,-30])
#plt.colorbar()
plt.title('Point 10min max. rain')

fig.set_size_inches(24,6)
plt.subplots_adjust(hspace=0.0,wspace=0.3)
plt.savefig('dungog_rain_hazard_10min.png',dpi=150)


       
fig = plt.figure(2)
plt.clf()
plt.suptitle('Wind hazard grids (10min data)')

plt.subplot(1,4,1)
qplt.contourf(PSMW, np.arange(0,40,5))
plt.gca().coastlines('10m')
plt.plot(151.7524,-32.4047, color='white', marker='o')
plt.plot(151.7817,-32.9283, color='white', marker='d')
#plt.axis([150,153,-34, -31])
#plt.xticks([150,152])
#plt.yticks([-34,-32])
#plt.colorbar()
plt.title('Point 10m max. wind')


plt.subplot(1,4,2)
qplt.contourf(PSWG, np.arange(0,70,10))
plt.gca().coastlines('10m')
plt.plot(151.7524,-32.4047, color='white', marker='o')
plt.plot(151.7817,-32.9283, color='white', marker='d')
#plt.axis([150,153,-34, -31])
#plt.xticks([150,152])
#plt.yticks([-34,-32])
#plt.colorbar()
plt.title('Point 10m max. wind gust')

plt.subplot(1,4,3)
qplt.contourf(NSWG, np.arange(0,70,10))
plt.gca().coastlines('10m')
plt.plot(151.7524,-32.4047, color='white', marker='o')
plt.plot(151.7817,-32.9283, color='white', marker='d')
#plt.axis([150,153,-34, -31])
#plt.xticks([150,152])
#plt.yticks([-34,-32])
#plt.colorbar()
plt.title('Neighbourhood 10m max. wind gust')

plt.subplot(1,4,4)
qplt.contourf(PGWS, np.arange(0,70,5))
plt.gca().coastlines('10m')
plt.plot(151.7524,-32.4047, color='white', marker='o')
plt.plot(151.7817,-32.9283, color='white', marker='d')
#plt.axis([150,153,-34, -31])
#plt.xticks([150,152])
#plt.yticks([-34,-32])
#plt.colorbar()
plt.title('Point 900hPa max. wind')

fig.set_size_inches(24,6)
plt.subplots_adjust(hspace=0.0,wspace=0.3)
plt.savefig('dungog_wind_hazard_10min.png',dpi=150)
