import serial
import time
from datetime import datetime as dt
import csv
import matplotlib
matplotlib.use("tkAgg")
import matplotlib.pyplot as plt
import numpy as np

ser = serial.Serial(port='/dev/cu.usbmodem1424101', baudrate=9600)
ser.flushInput()
plot_window = 100
y_var = np.array(np.zeros([plot_window]))
x_var = []
#np.array(np.zeros([plot_window]))
for i in range(plot_window):
    x_var.append(dt.now().strftime('%M:%S'))
    #x_var.append(time.asctime(time.time()))
plt.ion()
fig, ax = plt.subplots()
line,  = ax.plot(x_var, y_var)
ax.locator_params(tight=True, nbins=4)

while True:
    try:
        ser_bytes = ser.readline()
        value = float(ser_bytes.strip())
        temperature = value
        with open('test_data.csv', 'a') as f:
            writer = csv.writer(f, delimiter = ',')
            writer.writerow([time.time(), temperature])
        y_var = np.append(y_var, temperature)
        x_var.append(dt.now().strftime('%M:%S'))
        y_var = y_var[1: plot_window + 1]
        x_var = x_var[1: plot_window + 1]
        #print(dt.now().strftime('%M:%S'))
        line.set_ydata(y_var)
        line.set_xdata(x_var)
        ax.relim()
        #ax.set_ylim(0,24)
        ax.autoscale_view()
        ax.set_xticks(x_var[::10])
        ax.set_xticklabels(x_var[::10])
        fig.canvas.draw()
        fig.canvas.flush_events()
    except:
        print('Keyboard Interrupt')
        break
    time.sleep(0.1)

ser.close()
