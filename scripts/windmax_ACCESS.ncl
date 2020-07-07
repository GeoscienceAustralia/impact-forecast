;********************
; Calculates the maximum wind speed and the associated wind direction for a given lat/lon point over a timeseries
;********************

; Set output directory 
output_dir  = "/home/548/ss1079/impact_forecasting/Maximum_Wind_Speed/output/"

; Commence file loop 
do file_ix = 0,0; 23

    ; Set input directory
    input_dir = "/g/data1/en0/rjf548/fires/"

    ; Set 'stage' (or model resolution) 
    stage = "stage4"

    ;**********************
    ; Option 1: Run for ensembles - comment out paragraph to run for Option 2 
    ;**********************

    ; List available members
    members = (/"00","01","02","03","04","05","06","07","08","09","10","11","12","13","14","15","16","17","18","19","20","21","22","23"/)

    ; Set current member 
    member = "ens"+members(file_ix)

    ; Set current file 
    input_file = systemfunc("ls " + input_dir + " | grep eastcoastlow." + member)

    ; Set output file 
    output_file = "combined_alltimes_maxwind_"+stage+"_"+member+".nc"

    ; Clean up 
    delete([/members,member/])

    ;**********************
    ; Option 2: Run for deterministic - comment out paragraph to run for Option 1 
    ;**********************

    ; ; List available dates 
    ; dates = (/"2015041903","2015041915","2015042003"/)

    ; ; Set current date 
    ; date = dates(file_ix)

    ; ; Set current file 
    ; input_file = systemfunc("ls " + input_dir + " | grep eastcoastlow." + date)

    ; ; Set output file 
    ; output_file = "combined_alltimes_maxwind_"+stage+"_"+date+".nc"

    ;**********************
    ; Options to skip or remove existing files 
    ;**********************
    
    ; ; Option to remove file if file already exists 
    ; if (fileexists(output_dir+output_file)) then 
    ;     rmv_file = systemfunc("rm -rf "+output_dir+output_file)
    ; end if 

    ; ; Option to skip if file already exists 
    ; if (fileexists(output_dir+output_file)) then 
    ;     print(output_dir+output_file+" already processed! Skipping.")
    ;     continue 
    ; end if 

    ;**********************
    ; Prepare data 
    ;**********************

    ; Set input files
    wspd_file   = input_file + "/combined_alltimes_wspd10m_"+stage+".nc"
    wdir_file   = input_file + "/combined_alltimes_wdir10m_"+stage+".nc"

    ; Print file titles for tracking 
    print(" ")
    print("Currently processing "+input_dir)
    print("     "+wspd_file)
    print("     "+wdir_file)
    print(" ")

    ; Load files 
    wspd_nc     = addfile(input_dir+wspd_file,"r")
    wdir_nc     = addfile(input_dir+wdir_file,"r")

    ; Extract variables 
    wspd        = wspd_nc->$"windspeed"$
    wdir        = wdir_nc->$"winddirn"$
    time        = wspd_nc->$"t"$
    ht          = wspd_nc->$"ht"$
    lats        = wspd_nc->$"latitude"$
    lons        = wspd_nc->$"longitude"$

    time := cd_calendar(time,-4)

    ; Measure variables 
    num_times   = dimsizes(time)
    num_ht      = dimsizes(ht)
    num_lats    = dimsizes(lats)
    num_lons    = dimsizes(lons)

    ;**********************
    ; Calculate maximum wind speed 
    ;**********************

    ; Find maximum wind speed across the timeseries 
    tmp_ind     = dim_maxind(wspd,0) ; Returns ht, lat, lon 

    ; Create output array 
    max_wspd    = new((/num_ht,num_lats,num_lons/),float)
    cor_wdir    = new((/num_ht,num_lats,num_lons/),float)

    ; Commence loop 
    print("Commencing loop ...")
    do ht_ix = 0, num_ht-1
        do lat_ix = 0, num_lats-1
            do lon_ix = 0, num_lons-1
                if (ismissing(tmp_ind(ht_ix,lat_ix,lon_ix))) then 
                    max_wspd(ht_ix,lat_ix,lon_ix) = default_fillvalue("float")
                    cor_wdir(ht_ix,lat_ix,lon_ix) = default_fillvalue("float")   
                else                  
                    max_wspd(ht_ix,lat_ix,lon_ix) = wspd(tmp_ind(ht_ix,lat_ix,lon_ix),ht_ix,lat_ix,lon_ix)
                    cor_wdir(ht_ix,lat_ix,lon_ix) = wdir(tmp_ind(ht_ix,lat_ix,lon_ix),ht_ix,lat_ix,lon_ix)
                end if 
            end do 
        end do 
    end do 

    ; Reassign ht/lat/lon attributes 
    max_wspd!0  = "ht"
    max_wspd&ht = ht 
    max_wspd!1  = "latitude"
    max_wspd&latitude = lats 
    max_wspd!2  = "longitude"
    max_wspd&longitude = lons 

    cor_wdir!0  = "ht"
    cor_wdir&ht = ht 
    cor_wdir!1  = "latitude"
    cor_wdir&latitude = lats 
    cor_wdir!2  = "longitude"
    cor_wdir&longitude = lons 

    ;**********************
    ; Write to NetCDF4
    ;**********************
    print("Writing to netcdf ...")
    nc = addfile(output_dir+output_file,"c")

    ; Set netcdf format to netcdf4 
    setfileoption("nc","Format","NetCDF4")

    ; Declare file definition mode (to improve efficiency)
    setfileoption("nc","DefineMode",True)

    ; Extract original attributes 
    wspd_atts   = getfilevaratts(wspd_nc,"windspeed")
    wdir_atts   = getfilevaratts(wdir_nc,"winddirection")

    ; Assign original attributes to new variables where needed 
    max_wspd@units = wspd@units 
    max_wspd@title = "Maximum Wind Speed"
    max_wspd@long_name = "Maximum Wind Speed"
    max_wspd@_FillValue = default_fillvalue("float")
    cor_wdir@units = wdir@units
    cor_wdir@title = "Wind Direction at Maximum Speed"
    cor_wdir@long_name = "Wind Direction at Maximum Speed (degrees clockwise from north)"
    cor_wdir@_FillValue = default_fillvalue("float")

    ; Create file global attributes 
    file_att = True 
    file_att@creation_date = systemfunc("date")
    file_att@title = "Maximum Wind Speed and Corresponding Wind Direction"
    file_att@long_name = "Maximum Wind Speed and Corresponding Wind Direction"
    file_att@grid_mapping = wspd@grid_mapping 
    file_att@source = wspd@source 

    ; Predefine coordinate variables and dimensionality 
    dim_names = (/"ht","latitude","longitude"/)
    dim_sizes = (/num_ht,num_lats,num_lons/)
    dim_unlim = (/False,False,False/)
    filedimdef(nc,dim_names,dim_sizes,dim_unlim)

    ; Predefine dimensionality of variables 
    filevardef(nc,"max_wspd",typeof(max_wspd),(/"ht","latitude","longitude"/))
    filevardef(nc,"cor_wdir",typeof(cor_wdir),(/"ht","latitude","longitude"/))
    filevardef(nc,"ht",typeof(ht),(/"ht"/))
    filevardef(nc,"latitude",typeof(lats),(/"latitude"/))
    filevardef(nc,"longitude",typeof(lons),(/"longitude"/))

    ; Copy coordinate attributes 
    filevarattdef(nc,"ht",ht)
    filevarattdef(nc,"latitude",lats)
    filevarattdef(nc,"longitude",lons)

    ; Close file deinition mode 
    setfileoption("nc","DefineMode",False)

    ; Write to netcdf4
    nc->max_wspd    = max_wspd
    nc->cor_wdir    = cor_wdir
    nc->ht          = ht 
    nc->latitude    = lats 
    nc->longitude   = lons 

    ; Clean up for next iteration 
    delete([/wspd_file,wdir_file,wspd_nc,wdir_nc,wspd,wdir,time,ht,lats,lons,max_wspd,cor_wdir,nc,tmp_ind/])

    ; Set file permissions
    chmod = systemfunc("chmod 777 "+output_dir+output_file)

    print("Success! File saved as "+output_dir+output_file)

end do 