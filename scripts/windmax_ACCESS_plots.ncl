;********************
; Plots maximum wind speed and corresponding wind direction as vectors 
;********************

; Set output directory 
output_dir  = "/home/548/ss1079/impact_forecasting/Maximum_Wind_Speed/plots/"

; Set output file
output_file = "combined_alltimes_maxwind_stage4_ens12_windspeed"

; Set input directory 
input_dir   = "/home/548/ss1079/impact_forecasting/Maximum_Wind_Speed/output/"

; Set input files
input_file  = "combined_alltimes_maxwind_stage4_ens12.nc"

; Load file
input_nc    = addfile(input_dir+input_file,"r")

; Extract variables 
wspd        = input_nc->$"max_wspd"$
wdir        = input_nc->$"cor_wdir"$
lats        = input_nc->$"latitude"$
lons        = input_nc->$"longitude"$

; Open workspace 
wks = gsn_open_wks("pdf",output_dir+output_file)

; Set plot resources 
res = True 
res@cnLinesOn = False 
res@cnFillOn = True 
res@cnLineLabelsOn = False 
res@cnLevelSelectionMode = "ManualLevels"
res@cnMinLevelValF = 0.
res@cnMaxLevelValF = 30.
res@cnLevelSpacingF = 2.5

; Plot 
plot = gsn_csm_contour(wks,wspd(0,:,:),res)