import serial                                                              #Serial imported for Serial communication
import time
from datetime import datetime as dt
import csv
import matplotlib
matplotlib.use("tkAgg")
import matplotlib.pyplot as plt
import numpy as np                                                               #Required to use delay functions

probe = serial.Serial(port='/dev/cu.usbmodem1401', baudrate=9600)
probe.flushInput()

#from tclab import clock, setup, Historian, Plotter
import PID

targetT = 10
P = 10
I = 1
D = 1

controller = PID.PID(P, I, D)        # create pid control
controller.SetPoint = targetT              # initialize
controller.setSampleTime(1)
tfinal = 800

relay = serial.Serial('/dev/cu.usbmodem1301',9600)       #Create Serial port object called ArduinoUnoSerialData time
time.sleep(2)
relay.flush()
#wait for 2 secounds for the communication to get established
temp_probe = float(probe.readline().strip())

plot_window = 1000
probe_temps = np.array(np.zeros([plot_window]))
time_stamps = []
#np.array(np.zeros([plot_window]))
for i in range(plot_window):
    time_stamps.append(dt.now().strftime('%M:%S'))
    #x_var.append(time.asctime(time.time()))
plt.ion()
fig, ax = plt.subplots()
chline,  = ax.plot(time_stamps, probe_temps, label='Probe')

ax.locator_params(tight=True, nbins=4)
ax.legend()
ax.set_xlabel('Time (Min:Sec)')
ax.set_ylabel('Temperature (Celsius)')
T1 = 40
t = 0
while True:
    t = t + 1
    #while len(T_hex) < 8:
    #    T_hex = heatexchanger.readline()
    #heatexchanger.reset_input_buffer()
    T_probe = probe.readline()
    while len(T_probe) < 7:
        T_probe = probe.readline()
    #probe.reset_input_buffer()
    temp_probe = float(T_probe.strip())
    controller.update(temp_probe) # compute manipulated variable
    MV = controller.output # apply
    print(t,temp_probe, MV)
    probe_temps = np.append(probe_temps, temp_probe)
    time_stamps.append(dt.now().strftime('%M:%S'))
    probe_temps = probe_temps[1: plot_window + 1]
    time_stamps = time_stamps[1: plot_window + 1]
    #print(dt.now().strftime('%M:%S'))
    chline.set_ydata(probe_temps)
    chline.set_xdata(time_stamps)
    ax.relim()
    #ax.set_ylim(0,24)
    ax.autoscale_view()
    ax.set_xticks(time_stamps[::100])
    ax.set_xticklabels(time_stamps[::100])
    fig.canvas.draw()
    fig.canvas.flush_events()
    #heatexchanger.reset_input_buffer()
    #probe.reset_input_buffer()
    #print(heatexchanger.in_waiting)
    time.sleep(0.5)
    if MV > 0:
        relay.write(b'10')
        relay.readline()
    else:
        relay.write(b'11')
        relay.readline()