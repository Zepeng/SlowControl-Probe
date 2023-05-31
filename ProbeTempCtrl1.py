import serial          #Serial imported for Serial communication
import time
from datetime import datetime as dt
import csv
import matplotlib
matplotlib.use("tkAgg")
import matplotlib.pyplot as plt
from drawnow import *
import numpy as np                   #Required to use delay functions
import PID

#Define arduino ports
port_tip = 'COM7'
port_ceramic = 'COM10'
port_flange = 'COM14'
port_relay = 'COM4'
baudrate = 9600

#Creates a new file to save data
date_time = dt.now().strftime('%m_%d_%Y-%H-%M-%S')
date_time = str(date_time)
fileName = date_time +'.txt'

csvfile = open(fileName, 'w')
writer = csv.writer(csvfile, delimiter=' ')
writer.writerow(['Time', 'Tip', 'Ceramic', 'Flange', 'MV'])
print("Created file.")

#Opens up communication with arduino ports
tip = serial.Serial(port_tip, baudrate)
tip.flushInput()
#print("Tip connected to Arduino port: " + port_tip)

ceramic = serial.Serial(port_ceramic, baudrate)
ceramic.flushInput()
#print("Ceramic connected to Arduino port: " + port_ceramic)

flange = serial.Serial(port_flange, baudrate)
flange.flushInput()
#print("Flange connected to Arduino port: " + port_flange)

#Defines PID
targetT = -35        #Temperature at which the valve closes (C)
P = 1
I = 1
D = 1

controller = PID.PID(P, I, D)        # Create PID control
controller.SetPoint = targetT              #Initialize
controller.setSampleTime(1)
tfinal = 800

relay = serial.Serial(port_relay, baudrate)     #Creates comunication with relay
time.sleep(2)               #Wait for 2 seconds for the communication to get established
relay.flush()

#Create arrays
plot_window = 1000
tip_temps = np.array(np.zeros([plot_window]))
ceramic_temps = np.array(np.zeros([plot_window]))
flange_temps = np.array(np.zeros([plot_window]))
time_stamps = []

for i in range(plot_window):
    time_stamps.append(dt.now().strftime('%H:%M:%S'))

t = 0  

#Creates the window plot
def makeFig():
    #plt.ion()
    #fig, ax = plt.subplots()

    if not tip_temps[i]==0:

        plt.plot(time_stamps, tip_temps,'g', time_stamps, ceramic_temps,'r', time_stamps, flange_temps, 'b')
        #ax.plot(time_stamps, flange_temps, label = 'Flange')
        #plt.locator_params(tight=True, nbins=4)
        plt.legend(['Tip','Ceramic','Flange'])
        plt.xlabel('Time (H:M:S)')
        plt.ylabel('Temperature (C)')
        #plt.ylim([18,28])
        plt.title("Probe temperature control")
        #plt.yscale()
        #plt.relim()
        #plt.autoscale_view()
        plt.xticks(time_stamps[::200])
        #plt.xticklabels(time_stamps[::100])
        plt.grid(True)
        plt.tight_layout()

        #plt2 = plt.twinx()
        #plt2.plot(time_stamps, ceramic_temps, 'g' ,label = 'Ceramic')

T1 = 40
print('Time',' Tip', '   Ceramic', '   Flange', '    MV')

while True:   
    t=t+1
    T_tip = tip.readline()  
    T_ceramic = ceramic.readline()
    T_flange = flange.readline()
    tip.reset_input_buffer()
    ceramic.reset_input_buffer()
    flange.reset_input_buffer()
    while len(T_tip) < 7:
       T_tip = tip.readline()
    while len(T_ceramic) < 7:
       T_ceramic = ceramic.readline()
    while len(T_flange) < 7:
        T_flange = flange.readline()
    
    temp_tip = float(T_tip.strip())
    
    temp_ceramic = float(T_ceramic.strip())

    temp_flange = float (T_flange.strip())
    
    controller.update(temp_tip) # compute manipulated variable
    MV = controller.output # apply

    print(time_stamps[i], temp_tip, temp_ceramic, temp_flange, MV)
    print('**********')
    writer.writerow([time_stamps[i], temp_tip, temp_ceramic, temp_flange, MV]) #Saves data into a file

    tip_temps = np.append(tip_temps, temp_tip)
    ceramic_temps = np.append(ceramic_temps, temp_ceramic)
    flange_temps = np.append(flange_temps,temp_flange)
    time_stamps.append(dt.now().strftime('%H:%M:%S'))

    tip_temps = tip_temps[1: plot_window + 1]
    ceramic_temps = ceramic_temps[1: plot_window + 1]
    flange_temps = flange_temps[1: plot_window + 1]
    time_stamps = time_stamps[1: plot_window + 1]

    drawnow(makeFig)

    #chline.set_ydata(tip_temps)
    #chline.set_xdata(time_stamps)
  
    #fig.canvas.draw()
    #fig.canvas.flush_events()

    #heatexchanger.reset_input_buffer()
    #probe.reset_input_buffer()
    #print(heatexchanger.in_waiting)

    #Opens or closes valve
    if MV > 0:
        relay.write(b'10')
        relay.readline()
        print('CLOSED VALVE')
    else:
        relay.write(b'11')
        relay.readline()

