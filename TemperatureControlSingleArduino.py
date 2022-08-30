# -*- coding: utf-8 -*-

import sys
import serial                                                              #Serial imported for Serial communication
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
        with open(f_name,'w',encoding='UTF8', newline='') as err_log_file:
            err_log_file.write('')
    else:
        with open(f_name,'a',encoding='UTF8', newline='') as err_log_file:
            err_log_file.write('{} at t= {}'.formt(error,str(time)))

def log_temps(f_name,header,data,first):
    if first==True:
        with open(f_name,'w',encoding='UTF8', newline='') as temp_log_file:
            temp_log_w=csv.writer(temp_log_file)    #temperature log file
            temp_log_w.writerow(header)
    else:
        with open(f_name,'a',encoding='UTF8', newline='') as temp_log_file:
            temp_log_w=csv.writer(temp_log_file)    #temperature log file
            temp_log_w.writerow(data)
                       
err_log_f_name='Log File {}.csv'.format(dt.now().strftime('%m-%d-%Y, %H-%M'))
data_f_name='Temp log {}.csv'.format(dt.now().strftime('%m-%d-%Y, %H-%M'))
data_header=['t','temp_hex','temp_ch','MV']
    
#Required to use delay functions
try:
    temp_reader=serial.Serial(port='COM7', baudrate=115200) #Connect to Arduino
except:
    print("Temp Sensor Arduino aquisition error")
    sys.exit()

temp_reader.flushInput()

targetT = 35
P = 10
I = 1
D = 1

controller = PID.PID(P, I, D)        # create pid control
controller.SetPoint = targetT              # initialize
controller.setSampleTime(1)
tfinal = 800
# relay = serial.Serial('COM4',9600)       #Create Serial port object called ArduinoUnoSerialData time
#time.sleep(10)
# relay.flush()
#wait for 2 secounds for the communication to get established

#initialize saving errors and data to log files
log_error(err_log_f_name,'temp_ch float error','0',True)    #Create the log files for the run
log_temps(data_f_name,data_header,[0,0,0,0,0],True)
first_line=temp_reader.readline().strip()   #handles the thermalcouple initializing statement
try:
    sensor_reading = str(temp_reader.readline().strip()).strip('b\'').split(' , ')  #read the arduino serial output and break it up into the 3 temperature readings
    print(sensor_reading)
except:
        print("error reading serial port")
        log_error('error reading serial port','0',False)
try:
    temp_ch=float(sensor_reading[0])
except:
    print("temp_ch float error")
    log_error('temp_coldhead float error','0',False)
    print('wrote to err_log')
try:
    temp_chamber=float(sensor_reading[1])
except:
    print("temp_hex float error")
    log_error('temp_chamber float error','0',False)
    print('wrote to err_log')
try:
    temp_hex=float(sensor_reading[2])
except:
        print("temp_hex float error")
        log_error('temp_hex float error','0',False)
        print('wrote to err_log')

log_temps(data_f_name,data_header,[0, temp_hex, temp_ch,temp_chamber, 0],False) #push the temperature readings to the log file
plot_window = 1000
ch_temps = np.array(np.zeros([plot_window]))
hex_temps = np.array(np.zeros([plot_window]))
time_stamps = []
#np.array(np.zeros([plot_window]))
for i in range(plot_window):
    time_stamps.append(dt.now().strftime('%M:%S'))
    #x_var.append(time.asctime(time.time()))
plt.ion()
fig, ax = plt.subplots()
chline,  = ax.plot(time_stamps, ch_temps, label='Cold Head')
hexline, = ax.plot(time_stamps, hex_temps, label='Heat Exchanger')

ax.locator_params(tight=True, nbins=4)
ax.legend()
ax.set_xlabel('Time (Min:Sec)')
ax.set_ylabel('Temperature (Celsius)')
T1 = 40
t = 0

while True:
    if keyboard.is_pressed('a'):    #hopefully a key interupt to the program, this sort of works by the way
        print('exitit key pressed')
        break
    t = t + 1
    try:
        sensor_reading = str(temp_reader.readline().strip()).strip('b\'').split(' , ')  #read the arduino serial output and break it up into the 3 temperature readings
    except:
            print("error reading serial port")
            log_error('error reading serial port',t,False)
            continue
    try:
        temp_ch=float(sensor_reading[0])
    except:
        print("temp_hex float error")
        log_error('temp_coldhead float error','0',False)
        continue
    try:
        temp_chamber=float(sensor_reading[1])
    except:
        print("temp_hex float error")
        log_error('temp_chamber float error','0',False)
        continue
    try:
        temp_hex=float(sensor_reading[2])
    except:
            print("temp_hex float error")
            log_error('temp_hex float error','0',False)
            continue
    controller.update(temp_hex) # compute manipulated variable
    MV = controller.output # apply
    print(t, temp_hex, temp_ch, MV) #print out the temperature readins
    log_temps(data_f_name,data_header,[t, temp_hex, temp_ch, temp_chamber, MV],False)   #push the temperature readings to the log file
    ch_temps = np.append(ch_temps, temp_ch)
    hex_temps = np.append(hex_temps, temp_hex)
    time_stamps.append(dt.now().strftime('%M:%S'))
    ch_temps = ch_temps[1: plot_window + 1]
    hex_temps = hex_temps[1:plot_window+1]
    time_stamps = time_stamps[1: plot_window + 1]
    #print(dt.now().strftime('%M:%S'))
    chline.set_ydata(ch_temps)
    hexline.set_ydata(hex_temps)
    chline.set_xdata(time_stamps)
    hexline.set_xdata(time_stamps)
    ax.relim()
    #ax.set_ylim(0,24)
    ax.autoscale_view()
    ax.set_xticks(time_stamps[::100])
    ax.set_xticklabels(time_stamps[::100])
    fig.canvas.draw()
    fig.canvas.flush_events()
    #heatexchanger.reset_input_buffer()
    #coldhead.reset_input_buffer()
    #print(heatexchanger.in_waiting)
    #print('wrote to temp log')
    time.sleep(5)
    #if MV > 0:
    #    #relay.write(b'11')
    #    relay.readline()
    #else:
    #    #relay.write(b'10')
    #    relay.readline()
