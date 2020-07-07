####################################################
#   Given directories for u- and v- wind and maximum wind gust,
#       calculates the maximum wind speed and wind gust over each 
#       24-hour period during the event, plus the maximum for the
#       event itself.
####################################################

# This script requires the following:
# module use /g/data3/hh5/public/modules
# module load conda

# Import modules
import os
import sys
import argparse
from pprint import pprint
from glob import glob as ls
import iris
import warnings
import numpy as np
import datetime
from iris.experimental.equalise_cubes import equalise_attributes
from iris.util import unify_time_units
import iris.coord_categorisation as ct
import time

# Turn off warnings for ease of reading output (Iris complains a lot)
warnings.filterwarnings('ignore')

def parse_args():
    """Parse arguments for the script.

    Returns:
        dict : Dictionary of arguments passed to the script
    """
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)

    # Set up the directory mask
    default_directory_mask = '/g/data/ma05/BARRA_{domain}/{version}'
    default_directory_mask += '/forecast/spec/{variable}/{yyyy}/{mm}/'
    parser.add_argument(
        '--directory_mask',
        help='The directory mask to the data\ndefault=%s\n\n' % default_directory_mask,
        type=str, default=default_directory_mask
    )

    default_filename_mask = '{variable}-fc-spec-PT1H-BARRA_{domain}-{version}-{yyyy}{mm}{dd}T{hh}00Z.sub.nc'
    parser.add_argument(
        '-f', '--filename_mask',
        help='Filename mask\ndefault=%s\n\n' % default_filename_mask,
        type=str, default=default_filename_mask
    )

    # Set up the domains
    domains = 'AD,PH,SY,TA,R'.split(',')
    parser.add_argument(
        '-d', '--domain',
        help='Domain to process\ndefault=SY\n\n',
        choices=domains,
        default='SY'
    )

    # Start date
    default_start_date = '2015041900'
    parser.add_argument(
        '-s', '--start_date',
        help='Start date YYYYMMDDHH\ndefault=%s\n\n' % default_start_date,
        type=str, default=default_start_date
    )

    # End date
    default_end_date = '2015042218'
    parser.add_argument(
        '-e', '--end_date',
        help='End date YYYYMMDDHH\ndefault=%s\n\n' % default_end_date,
        type=str, default=default_end_date
    )

    default_version = 'v1'
    parser.add_argument(
        '-v', '--version',
        help='Version of the data to use\ndefault=%s\n\n' % default_version,
        type=str, default=default_version
    )

    default_output_dir = '/short/w85/BNHCRC/data/BARRA_output/'
    parser.add_argument(
        '-o', '--output_dir',
        help='Output directory\n\ndefault=%s\n\n' % default_output_dir,
        type=str, default=default_output_dir
    )

    # Parse the arguments, convert to dict
    args = vars(parser.parse_args())

    # Convert the dates
    args['start_date_obj'] = datetime.datetime.strptime(args['start_date'], '%Y%m%d%H')
    args['end_date_obj'] = datetime.datetime.strptime(args['end_date'], '%Y%m%d%H')

    # Convert to dictionary and return
    return args


def interpolate_template(template, context):
    """Interpolate context into a template.

    (i.e. replace things in strings without % replacement).

    Args:
        template (str) : String to fill with context
        context (dict) : Dictionary of variables

    Returns:
        str : Populated template
    """
    populated = template
    for key, value in context.items():
        _key = '{%s}' % key
        populated = populated.replace(_key, str(value))

    return populated


def get_filepaths(args, variable, dt=datetime.timedelta(hours=6)):
    """Get all of the filepaths for the variable across directories.

    Args:
        args (dict) : Arguments dictionary from parse_args
        variable (str) : Variable name
        dt (datetime.timedelta) : Interval between files

    Returns:
        list : List of filepaths to load
    """
    # Set an initial context
    context = args

    # Add the variable
    context['variable'] = variable

    # Create an empty list of files
    filepaths = []

    # Loop through until we find all of the files
    current_date = args['start_date_obj']
    while current_date <= args['end_date_obj']:

        # Update the context with the current date
        context['yyyy'] = current_date.strftime('%Y')
        context['mm'] = current_date.strftime('%m')
        context['dd'] = current_date.strftime('%d')
        context['hh'] = current_date.strftime('%H')

        # Work out the filepath
        filepath = os.path.join(
            interpolate_template(args['directory_mask'], context),
            interpolate_template(args['filename_mask'], context)
        )

        # If the file exists, add it to the list
        if os.path.isfile(filepath):
            filepaths.append(filepath)

        # Next time
        current_date += dt

    # Return
    return filepaths


def load_data(variable, filepaths):
    """Load the data.

    Args:
        variable (str) : Name of the variable in the file
        filepaths (list) : List of files from get_filepaths

    Returns:
        iris.cube.CubeList : CubeList of data
    """
    return iris.load(
        filepaths,
        iris.Constraint(cube_func=lambda cube: cube.var_name == variable)
    )


def remove_coord(cube, coord):
    """Remove a coordinate from a cube (when the Iris built-in fails).

    Args:
        cube (iris.cube.Cube) : Cube of data
        coord (str) : Name of the coordinate

    Returns:
        iris.cube.Cube : Updated cube, sans coordinate
    """
    if coord in [c.standard_name for c in cube.coords()]:
        cube.remove_coord(coord)

    return cube


def clean_data(cubes):
    """There is metadata present that breaks the cube merge, this fixes that.

    Args:
        cubes (iris.cube.CubeList) : List of cubes

    Returns:
        iris.cube.CubeList : Cleaned data that *should* merge
    """
    # Remove offending data
    for cube in cubes:
        cube.coord('time').attributes = {}
        cube.remove_coord('forecast_reference_time')

    # Remove overlapping data
    for i in range(len(cubes) - 1):

        # Get the current and next cubes
        current, next = cubes[i], cubes[i+1]

        # Work out where to slice
        _slice = next.coord('time').cell(0)

        # Build up a constraint to actually slice
        time_constraint = iris.Constraint(
            time = lambda cell: cell < _slice
        )

        # Subset the current cube
        current = current.extract(time_constraint)

        # Remove offending metadata
        frt = 'forecast_reference_time'
        current.coord('time').attributes = {}
        current = remove_coord(current, frt)

        # Replace cube in list with an updated one
        cubes[i] = current

    # Remove the offending metadata on the last one (for some reason it lives?)
    cubes[-1].coord('time').attributes = {}
    cubes[-1] = remove_coord(cubes[-1], frt)

    # Equalise metadata (delete anything that isn't consistent)
    equalise_attributes(cubes)

    # Unify the time units
    unify_time_units(cubes)

    # Should be clean enough to merge now
    return cubes


if __name__ == '__main__':

    start_time = time.time()

    # Get the arguments, print them pretty
    args = parse_args()
    pprint(args)

    # Get the filepaths
    print('Getting filepaths')
    uwnd10m_filepaths = get_filepaths(args, 'uwnd10m')
    vwnd10m_filepaths = get_filepaths(args, 'vwnd10m')
    max_wndgust10m_filepaths = get_filepaths(args, 'max_wndgust10m')

    # List the numebr of files
    print('uwnd10m_filepaths = %s' % len(uwnd10m_filepaths))
    print('vwnd10m_filepaths = %s' % len(vwnd10m_filepaths))
    print('max_wndgust10m_filepaths = %s' % len(max_wndgust10m_filepaths))

    # Load the data
    print('Loading uwnd10m, this may take a while...')
    uwnd10m = load_data('uwnd10m', uwnd10m_filepaths)
    print('Loading vwnd10m, this may take a while...')
    vwnd10m = load_data('vwnd10m', vwnd10m_filepaths)
    print('Loading max_wndgust10m, this may take a while...')
    max_wndgust10m = load_data('max_wndgust10m', max_wndgust10m_filepaths)

    # Clean the data
    print('Cleaning data...')
    uwnd10m = clean_data(uwnd10m)
    vwnd10m = clean_data(vwnd10m)
    max_wndgust10m = clean_data(max_wndgust10m)

    # Concatenate into single cubes
    print('Concatenating cubes...')
    uwnd10m = uwnd10m.concatenate_cube()
    vwnd10m = vwnd10m.concatenate_cube()
    max_wndgust10m = max_wndgust10m.concatenate_cube()

    # Regrid U onto V
    print('Regridding U onto V (so they align in space)...')
    interpolator = iris.analysis.Linear()
    vwnd10m = vwnd10m.regrid(uwnd10m, interpolator)

    # Create a cube of wind speed
    print('Calculating wind speed...')
    windspeed = (uwnd10m ** 2 + vwnd10m ** 2) ** 0.5
    windspeed.rename('windspeed')
    
    # Create extra coordinate for daily statistics
    ct.add_day_of_year(windspeed, 'time')
    ct.add_day_of_year(max_wndgust10m, 'time')

    print('Calculating max wind speed...')
    max_speed = windspeed.aggregated_by(['day_of_year'], iris.analysis.MAX)

    print('Calculating max (max) gust...')
    max_gust = max_wndgust10m.aggregated_by(['day_of_year'], iris.analysis.MAX)

    # Event maximum
    print('Calculating event maxima...')
    event_max_speed = max_speed.collapsed('time', iris.analysis.MAX)
    event_max_gust = max_gust.collapsed('time', iris.analysis.MAX)

    # Save the calculation
    print('Saving calculations...')

    # Build an output filepath (so that it is a bit unique)
    max_speed_output_filepath = os.path.join(
        args['output_dir'],
        'max_speed_%(domain)s_%(start_date)s_%(end_date)s.nc' % args
    )

    # Build an output filepath (so that it is a bit unique)
    max_gust_output_filepath = os.path.join(
        args['output_dir'],
        'max_gust_%(domain)s_%(start_date)s_%(end_date)s.nc' % args
    )

    # Make the output directory
    print('Making output directory')
    os.makedirs(args['output_dir'], exist_ok=True)

    # Rename things
    print('Renaming variables...')
    max_speed.rename('max_windspeed')
    event_max_speed.rename('event_max_windspeed')
    max_gust.rename('max_gust')
    event_max_gust.rename('event_max_gust')

    iris.save([max_speed, event_max_speed], max_speed_output_filepath)
    print('Data written to %s' % max_speed_output_filepath)

    iris.save([max_gust, event_max_gust], max_gust_output_filepath)
    print('Data written to %s' % max_gust_output_filepath)

    print('DONE')
    end_time = time.time()
    print('Time elapsed = %s seconds' % (end_time - start_time))