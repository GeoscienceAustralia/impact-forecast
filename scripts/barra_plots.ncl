
; Subset around domain for plotting  
min_lat = -38.0
max_lat = -28.0
min_lon = 146.0
max_lon = 155.0

; Set input files
wind_file = "/short/w85/BNHCRC/data/BARRA_output/max_speed_SY_2015041900_2015042218.nc"
gust_file = "/short/w85/BNHCRC/data/BARRA_output/max_gust_SY_2015041900_2015042218.nc"

; Load files
wind_nc = addfile(wind_file,"r")
gust_nc = addfile(gust_file,"r")

; Extract variables
wind = wind_nc->max_windspeed(:,{min_lat:max_lat},{min_lon:max_lon})
gust = gust_nc->max_gust(:,{min_lat:max_lat},{min_lon:max_lon})
event_maxwind = wind_nc->event_max_windspeed({min_lat:max_lat},{min_lon:max_lon})
event_maxgust = gust_nc->event_max_gust({min_lat:max_lat},{min_lon:max_lon})
time = wind_nc->time
lats = wind_nc->latitude
lons = wind_nc->longitude

; Convert time 
time := cd_calendar(time,-2)

; Count number of days - currently configured for 5, will need to adjust plots and panels below if different.
num_days = dimsizes(time)

; Open workspace
wks = gsn_open_wks("ps","BARRA_201504_ECL_HunterValley")
gsn_define_colormap(wks,"GMT_wysiwygcont")

; Set number of plots 
plots = new((num_days+1)*2,graphic)

; Set resources
res = True
res@gsnDraw = False
res@gsnFrame = False
; Turn off contour lines 
res@cnLinesOn = False
; Turn on contour fill 
res@cnFillOn = True
; Turn off information label 
res@cnInfoLabelOn = False
; Turn off line labels 
res@cnLineLabelsOn = False
; Set manual plotting levels 
res@cnLevelSelectionMode = "ManualLevels"
res@cnMinLevelValF = 0.0
res@cnMaxLevelValF = 45.0
res@cnLevelSpacingF = 1.0
; Remove cyclic feature as not using global data 
res@gsnAddCyclic = False
; Turn off individual label bars 
res@lbLabelBarOn = False
; Set to raster mode (high res data)
res@cnFillMode = "RasterFill"

; Set panel resources
pres = True
; Set panel label bar 
pres@gsnPanelLabelBar = True
; Remove separating lines in label bar 
pres@lbBoxSeparatorLinesOn = False

; Plot wind speed and gust 
count = 0 
do day_ix = 0, num_days-1

    ; Plot wind speed first 
    res@tiMainString = "Max Wind Speed (" + time(day_ix) + ")"
    plots(count) = gsn_csm_contour(wks,wind(day_ix,:,:),res)

    ; Plot gust second 
    res@tiMainString = "Max Wind Gust (" + time(day_ix) + ")"
    plots(count+1) = gsn_csm_contour(wks,gust(day_ix,:,:),res)

    ; Increase count 
    count = count + 2

end do 

; Add event maxima 
res@tiMainString = "Event Maximum Wind Speed"
plots((num_days*2)) = gsn_csm_contour(wks,event_maxwind,res)

res@tiMainString = "Event Maximum Wind Gust"
plots((num_days*2)+1) = gsn_csm_contour(wks,event_maxgust,res) 

; Panel plots 
gsn_panel(wks,plots,(/3,4/),pres)