import serial                                                              #Serial imported for Serial communication
import time
from datetime import datetime as dt
import csv
import matplotlib
matplotlib.use("tkAgg")
import matplotlib.pyplot as plt
import numpy as np                                                               #Required to use delay functions

coldhead = serial.Serial(port='COM3', baudrate=9600)
heatexchanger = serial.Serial(port='COM6', baudrate=9600)
coldhead.flushInput()
heatexchanger.flushInput()

from tclab import clock, setup, Historian, Plotter
import PID

targetT = 35
P = 10
I = 1
D = 1

controller = PID.PID(P, I, D)        # create pid control
controller.SetPoint = targetT              # initialize
controller.setSampleTime(1)
tfinal = 800

relay = serial.Serial('COM4',9600)       #Create Serial port object called ArduinoUnoSerialData time
time.sleep(2)
relay.flush()
#wait for 2 secounds for the communication to get established
temp_ch = float(coldhead.readline().strip())
temp_hex = float(heatexchanger.readline().strip())

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
    t = t + 1
    T_hex = heatexchanger.readline()
    #while len(T_hex) < 8:
    #    T_hex = heatexchanger.readline()
    #heatexchanger.reset_input_buffer()
    temp_hex = float(T_hex.strip())
    T_ch = coldhead.readline()
    #while len(T_ch) < 8:
    #    T_ch = coldhead.readline()
    #coldhead.reset_input_buffer()
    temp_ch = float(T_ch.strip())
    controller.update(temp_hex) # compute manipulated variable
    MV = controller.output # apply
    print(t, temp_hex, temp_ch, MV)
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
    time.sleep(0.5)
    #if MV > 0:
    #    #relay.write(b'11')
    #    relay.readline()
    #else:
    #    #relay.write(b'10')
    #    relay.readline()