from distutils.log import error
import board
import digitalio
import adafruit_max31856
import time
from datetime import datetime as dt
import csv
import matplotlib
matplotlib.use("tkAgg")
import matplotlib.pyplot as plt
import numpy as np
import keyboard
from tclab import clock, setup, Historian, Plotter
import PID

def log_error(f_name,error,time,first):
    if first==True:
        with open(f_name,'w',encoding='UTF8',newline='') as err_log_file:
            err_log_file.write('')
    else:
        with open(f_name,'a',encoding='UTF8',newline='') as err_log_file:
            err_log_file.write("\n".join('{} at t= {}'.format(error,str(time))))

def log_temps(f_name,header,data,first):
    if first==True:
        with open(f_name,'w',encoding='UTF8', newline='') as temp_log_file:
            temp_log_w=csv.writer(temp_log_file)    #temperature log file
            temp_log_w.writerow(header)
    else:
        with open(f_name,'a',encoding='UTF8', newline='') as temp_log_file:
            temp_log_w=csv.writer(temp_log_file)    #temperature log file
            temp_log_w.writerow(data)

err_log_f_name='Log File {}.txt'.format(dt.now().strftime('%m-%d-%Y, %H-%M'))
data_f_name='Temp log {}.csv'.format(dt.now().strftime('%m-%d-%Y, %H-%M'))
data_header=['Rt', 't', 'temp_hex', 'temp_ch' , 'temp_chamber', 'MV','Heater On']

# Create sensor object, communicating over the board's default SPI bus
spi = board.SPI()

# allocate a CS pin and set the direction
cs5 = digitalio.DigitalInOut(board.D5)
cs5.direction = digitalio.Direction.OUTPUT
cs25 = digitalio.DigitalInOut(board.D25)
cs25.direction = digitalio.Direction.OUTPUT
cs24 = digitalio.DigitalInOut(board.D24)
cs24.direction = digitalio.Direction.OUTPUT
Heater = digitalio.DigitalInOut(board.D30)
Heater.direction= digitalio.Direction.Output

# create a thermocouple object with the above
HeatEx = adafruit_max31856.MAX31856(spi, cs5,thermocouple_type=1)
Chamber = adafruit_max31856.MAX31856(spi, cs25,thermocouple_type=3)
ColdHead = adafruit_max31856.MAX31856(spi, cs24,thermocouple_type=1)
Heater.value = False

targetT = 26    #initial inputs for PID control
P = 10
I = 1
D = 1

controller = PID.PID(P, I, D)        # create pid control
controller.SetPoint = targetT              # initialize
controller.setSampleTime(1)
tfinal = 800


log_error(err_log_f_name,'temp_ch float error','0',True)    #Create the log files for the run
log_temps(data_f_name,data_header,[0,0,0,0,0,0],True)

temp_coldhead=ColdHead.temperature
temp_chamber=Chamber.temperature
temp_heatex=HeatEx.temperature

log_temps(data_f_name,data_header,[dt.now().strftime('%Y-%m-%d %H:%M:%S'), 0, temp_heatex, temp_coldhead, temp_chamber, controller.output,"False"],False) #push the temperature readings to the log file

plot_window = 1000
coldhead_temps = np.array(np.zeros([plot_window]))
heatex_temps = np.array(np.zeros([plot_window]))
chamber_temps = np.array(np.zeros([plot_window]))
time_stamps = []
#np.array(np.zeros([plot_window]))
for i in range(plot_window):
    time_stamps.append(dt.now().strftime('%M:%S'))
    #x_var.append(time.asctime(time.time()))
plt.ion()
fig, ax = plt.subplots()
chline,  = ax.plot(time_stamps, coldhead_temps, label='Cold Head')
hexline, = ax.plot(time_stamps, heatex_temps, label='Heat Exchanger')
chamberline, =ax.plot(time_stamps, chamber_temps, label='Chamber')

ax.locator_params(tight=True, nbins=4)
ax.legend()
ax.set_xlabel('Time (Min:Sec)')
ax.set_ylabel('Temperature (Celsius)')
t=0
Heat_on=True
# measure the temperature! (takes approx 160ms)
while True:
    if keyboard.is_pressed('a'):    #hopefully a key interupt to the program, this sort of works by the way
        print('exitit key pressed')
        break
    t += 1
    temp_coldhead=ColdHead.temperature
    temp_chamber=Chamber.temperature
    temp_heatex=HeatEx.temperature
    if (np.abs(heatex_temps[-1]-temp_heatex)>= 2 or np.abs(chamber_temps[-1]-temp_chamber)>= 2 or np.abs(coldhead_temps[-1]-temp_coldhead)>= 2) and t!=1:
        log_error(err_log_f_name,"Error in reported temperature vaule",t,False)
        error+=1
        continue
    if error==0:    #extra insurance that the plot won't get updated if an error occurs
        controller.update(temp_heatex) # compute manipulated variable
        MV = controller.output # apply
        if MV > 0:
           Heater.value = True
           Heat_on=True
           # write to event log that heater turned on/off
        else:
           Heater.value = False
           Heat_on=False
    if Heat_on:
            log_temps(data_f_name,data_header,[dt.now().strftime('%Y-%m-%d %H:%M:%S'), t, temp_heatex, temp_chamber, temp_chamber, MV,'On'],False)   #push the temperature readings to the log file
            print(t, temp_heatex, temp_chamber, temp_chamber, MV,"On") #print out the temperature readings
    else:
        log_temps(data_f_name,data_header,[dt.now().strftime('%Y-%m-%d %H:%M:%S'), t, temp_heatex, temp_chamber, temp_chamber, MV,'Off'],False)
        print(t, temp_heatex, temp_chamber, temp_chamber, MV,"Off") #print out the temperature readings
        ch_temps = np.append(ch_temps, temp_chamber)
        hex_temps = np.append(hex_temps, temp_heatex)
        chamber_temps = np.append(chamber_temps, temp_chamber)
        time_stamps.append(dt.now().strftime('%M:%S'))
        ch_temps = ch_temps[1: plot_window + 1]
        hex_temps = hex_temps[1:plot_window+1]
        chamber_temps = chamber_temps[1:plot_window+1]
        time_stamps = time_stamps[1: plot_window + 1]
        #print(dt.now().strftime('%M:%S'))
        chline.set_ydata(ch_temps)
        hexline.set_ydata(hex_temps)
        chline.set_xdata(time_stamps)
        hexline.set_xdata(time_stamps)
        chamberline.set_ydata(chamber_temps)
        chamberline.set_xdata(time_stamps)
        ax.relim()
        #ax.set_ylim(0,24)
        ax.autoscale_view()
        ax.set_xticks(time_stamps[::100])
        ax.set_xticklabels(time_stamps[::100])
        fig.canvas.draw()
        fig.canvas.flush_events()
        #print(heatexchanger.in_waiting)
        time.sleep(5)