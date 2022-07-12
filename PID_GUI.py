# -*- coding: utf-8 -*-
"""
Created on Tue May 24 14:23:16 2022

@author: nohim
"""
from tkinter import *
from tkinter import ttk
import serial                                                              #Serial imported for Serial communication
import time           
from datetime import datetime as dt
import matplotlib
matplotlib.use('QtAgg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation                                            #Required to use delay functions
from tclab import clock, setup, Historian, Plotter
import PID
from itertools import count

"""
This program runs a PID loop to maintain a steady and controlled temperature at the tip of the cryoprobe.
It reads in temperature data from a PT100 RTD into a MAX31865 chip via arduino, and then uses another arduino to 
automatically flip a relay, which allows a heater tape to warm up until the temperature setpoint has been met.
There is a built in GUI for ease of use, as well as a live-plotting function to make it easier to tune the PID constants. 
The plot reads as a relation of temperature vs time. 

"""
ArduinoUnoSerial = serial.Serial('COM5',baudrate = 57600)       #Create Serial port object for arduino that controls relay
time.sleep(2)
ArduinoUnoSerial.flush()                                        #Clear arduino in case theres any leftover data

ser = serial.Serial(port='COM4', baudrate=57600)                #Create Serial port object for arduino that reads in temperature
ser.flushInput()                                                #Clear arduino in case there are any leftover temperature values
ser_bytes = ser.readline()
value = float(ser_bytes.strip())


root = Tk()                                                     #Create frame for window containing PID controls
frm = ttk.Frame(root, padding=10)
frm.grid()

temp_label = ttk.Label(frm, text="Temp Setpoint:")             #Establish buttons/text entry fieldl
temp_label.grid(column = 1, row = 1)
p_gain_label = ttk.Label(frm, text="P Gain:")
p_gain_label.grid(column = 1, row = 2)
i_gain_label = ttk.Label(frm, text="I Gain:")
i_gain_label.grid(column = 1, row = 3)
d_gain_label = ttk.Label(frm, text="D Gain:")
d_gain_label.grid(column = 1, row = 4)


mp = ttk.Entry(frm)
mp.grid(column = 2, row = 1)
p_gain = ttk.Entry(frm)
p_gain.grid(column = 2, row = 2)
i_gain = ttk.Entry(frm)
i_gain.grid(column = 2, row = 3)
d_gain = ttk.Entry(frm)
d_gain.grid(column = 2, row = 4)


def run_PID():                                        
    targetT = int(mp.get())
    P = int(p_gain.get()) 
    I = int(i_gain.get())
    D = int(d_gain.get())
    
   
    
    controller = PID.PID(P, I, D)        # create pid control
    controller.SetPoint = targetT              # initialize

    """ Sample time originally 1"""
    controller.setSampleTime(1)
    
    #wait for 2 secounds for the communication to get established
    
    y_var = []               
    x_var = []

    index = count()

    
    def animate(i):                            #Creates plot of data for temperature vs time
        
        
        t = 0
        t = t + 1
        ser_bytes = ser.readline()
        if len(ser_bytes) < 7:
            ser_bytes = ser.readline()
        ser.reset_input_buffer()
        value = float(ser_bytes.strip())
        controller.update(value) # compute manipulated variable
        MV = controller.output # apply
        print(t, value, MV)
        
        plt.show()
        
    
        if MV > 0:
            ArduinoUnoSerial.write(b'11')
            ArduinoUnoSerial.readline()
        else:
            ArduinoUnoSerial.write(b'10')
            ArduinoUnoSerial.readline()
    
        x_var.append(next(index))
        y_var.append(value)
            
        plt.cla()
        plt.plot(x_var, y_var)
    
    
    ani = FuncAnimation(plt.gcf(), animate, interval = 10)   #Constantly update plot to make live plot

    plt.tight_layout()

    plt.show()   


    
    
ttk.Label(frm, text="Temperature Controller").grid(column=0, row=0)

ttk.Button(frm, text = "Enter", command = run_PID).grid(column = 0, row = 5)

ttk.Button(frm, text="Quit", command = lambda:[root.destroy(), ser.close(), ArduinoUnoSerial.close()]).grid(column=1, row=5
                                                                                                            )
root.mainloop()