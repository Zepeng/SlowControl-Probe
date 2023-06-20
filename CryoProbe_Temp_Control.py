"""
@Author: Andrei Gogosha, Peter Knauss, Melissa Medina-P.
Python file to run the temperature control of the CryoProbe
Need to update PID control values for faster loop exicution
"""
import time
import csv
import keyboard
import os
import board
import digitalio
import adafruit_max31865
import PID
from datetime import datetime as dt
import numpy as np
import signal
import sys
import traceback

def log_temps(f_name,header,data):
    temp_log_w=csv.writer(log_file)
    temp_log_w.writerow(data)

def open_file(file_name,data_header):
    log_file = open(os.path.join(ROOT_DIR, 'Logs', file_name),'w',encoding='UTF8', newline='')     #Open the log file in the Log subfolder of the working directory with the specified filename
    temp_log_w = csv.writer(log_file)
    temp_log_w.writerow(data_header)     # writes the data header for the csv file
    
    return log_file     # returns the log file so it can be saved as a variable and manipulated later

def calibrated_temps(temp, TC):
    #if temp > 35:
    #    raise Exception('Temperature has reached too high on TC {}'.format(TC))
    if 'Tip' in TC:
        RawRange = 124.8
        ReferenceRange = 116.3
        ActualTemp = (((temp + 112.6) * ReferenceRange) / RawRange) - 96.7
    if 'Ceramic' in TC:
        RawRange = 179.7
        ReferenceRange = 169.5
        ActualTemp = (((temp + 159.9) * ReferenceRange) / RawRange) - 150.9
    if 'Flange' in TC:
        RawRange = 179
        ReferenceRange = 169.1
        ActualTemp = (((temp + 159.6) * ReferenceRange) / RawRange) - 149.2
        
    return ActualTemp
    
def signal_handler(signum, frame):
    raise KeyboardInterrupt

signal.signal(signal.SIGINT, signal_handler) # Raspberry Pi had unreliable Ctrl-C handling, catch independently

if __name__ == '__main__':
    ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname("CryoProbe_Temp_Control.py")))

    data_f_name='Temp log {}.csv'.format(dt.now().strftime('%m-%d-%Y, %H-%M'))
    data_header=['Rt', 'temp_tip', 'temp_ceramic', 'temp_flange','Relay']
    # header reads [Real time, Cold head temp, Heat exchander front temp, heat exhchanger back temp, champer temp, Heater 1 status, Heater 2 status]
    log_file = open_file(data_f_name,data_header)

    # Create sensor object, communicating over the board's default SPI bus
    spi = board.SPI()

    # allocate a CS pin and set the direction
    cs16 = digitalio.DigitalInOut(board.D16)
    cs21 = digitalio.DigitalInOut(board.D21)
    cs19 = digitalio.DigitalInOut(board.D19)
    Relay = digitalio.DigitalInOut(board.D17)
    Relay.direction= digitalio.Direction.OUTPUT

    #Create a thermocouple object with the above pin assignements
    Tip = adafruit_max31865.MAX31865(spi, cs16, wires=2)
    Ceramic = adafruit_max31865.MAX31865(spi, cs21, wires=2)   
    Flange = adafruit_max31865.MAX31865(spi, cs19, wires=2)   
    #Chamber = adafruit_max31865.MAX31865(spi, cs19, wires=2)

    Relay.value = False
    Relay_status = 0
    targetT1 = -35   #initial inputs for PID control
    P1 = 0.2*0.6
    I1 = 1.2*0.2/60
    D1 = 3*0.2*60/40
    #P1 = 20*0.6
    #I1 = 1.2*20/0.5
    #D1 = 3*20*0.5/40

    controllerF = PID.PID(P1, I1, D1)        # create pid control
    controllerF.SetPoint = targetT1             # initialize the controler
    controllerF.setSampleTime(0.25)

    Ledger=np.array([[], [], [], [], []])

    try:     # try and excep statement used to catch error and log them to a specified file
        runlen=1
        loop_time = 0.25 #set time for loop in seconds
        itt_len=20 #number of loops that get averaged to the log
        while True:
            now = time.time() # keep track of when the loop starts so that we keep a consistant loop runtime 
            if os.stat(os.path.join(ROOT_DIR, 'Logs', data_f_name)).st_size>= 4194304:     #checks if the current log file is 4Mb, if it is it creates a new log file 
                data_f_name='Temp log {}.csv'.format(dt.now().strftime('%m-%d-%Y, %H-%M'))
                log_file.close()
                log_file = open_file(data_f_name, data_header)
            #Reads the tip, ceramic and flange temperatures
            #t1=time.time()
            #Tip.initiate_one_shot_measurement()
            #Ceramic.initiate_one_shot_measurement()
            #Flange.initiate_one_shot_measurement()

            #print(Tip.unpack_temperature(), ' ', Ceramic.unpack_temperature(), ' ', Flange.unpack_temperature())
            #Tip._wait_for_oneshot()
            print(Tip.temperature, Tip.resistance, Ceramic.temperature, Ceramic.resistance, Flange.temperature, Flange.resistance)
            temp_Tip= Tip.temperature #calibrated_temps(Tip.temperature, 'Tip')
            temp_Ceramic= Ceramic.temperature #calibrated_temps(Ceramic.temperature,'Ceramic')
            temp_Flange=Flange.temperature #calibrated_temps(Flange.temperature,'Flange')

            #if not HeatExF.oneshot_pending:
            #    temp_HeatExF=calibrated_temps(HeatExF.temperature,'HeatExF')
            #else:
            #    #HeatExF._wait_for_oneshot()
            #    temp_HeatExF=calibrated_temps(HeatExF.temperature,'HeatExF')
            #if not HeatExB.oneshot_pending:
            #    temp_HeatExB=calibrated_temps(HeatExB.temperature,'HeatExB')
            #else:
            #    #HeatExB._wait_for_oneshot()
            #    temp_HeatExB=calibrated_temps(HeatExB.temperature,'HeatExB')
            #t2=time.time()
            
            controllerF.update(temp_Tip) # update the pid controlers

            MV1 = 10
            #MV1 = controllerF.output # get the new pid values
            if MV1 > 0:      #temp too low close valve
                Relay.value = True
                Rel_status = 11
            else:     #turn heat off
                Relay.value = False
                Rel_status = 10
            time_stamp= dt.now().strftime('%H:%M:%S')     #timestamp used for x axis tick
            #t3 = time.time()
            Ledger=np.append(Ledger,[[time_stamp], [temp_Tip], [temp_Ceramic], [temp_Flange], [Rel_status]],axis=1 )
            if runlen==itt_len:     #change to be however many itterations you want before updating logs
                Tip_avg=np.average(Ledger[1,-itt_len:].astype('float32'))
                Ceramic_avg=np.average(Ledger[2,-itt_len:].astype('float32'))
                Flange_avg=np.average(Ledger[3,-itt_len:].astype('float32'))
                log_temps(data_f_name,data_header,[time_stamp, Tip_avg, Ceramic_avg, Flange_avg, Rel_status ])     #write to temp log file
                log_file.flush() #pushes the data collected this loop to the csv.
                runlen = 0
            if len(Ledger[1])>=itt_len+1:     #only holds onto last itt len +1 temperatures in memory
                Ledger=np.delete(Ledger, obj=0,axis=1)
            #t4=time.time()
            #print(t2-t1,t4-t3,elapsed)
            #print('{}, {}, {}'.format(Tip.temperature, Ceramic.temperature, Flange.temperature))
            #print(Ledger[:,-1:])
            runlen += 1
            elapsed = time.time() - now # how long was it running?
            if elapsed < loop_time: time.sleep(loop_time-elapsed) #make loop run every 0.25 seconds
            else: time.sleep(0.1)
            
    #Opens the relay when program interrupted and writes to error log if need be
    except KeyboardInterrupt:
        print('\n')
        print('Interrupted')
    except Exception as e:
        if not os.path.exists(os.path.join(ROOT_DIR, 'Logs', 'Error Logs')):
            with open(os.path.join(ROOT_DIR, 'Logs', 'Error Logs'), 'w', encoding='UTF-8') as file:
                file.write('')
        with open(os.path.join(ROOT_DIR, 'Logs', 'Error Logs'), 'a', encoding='UTF-8') as file:
            file.write('-------------------------------------------------'+'\n')
            file.write(dt.now().strftime('%Y-%m-%d %H:%M:%S')+'\n')
            traceback.print_exc(file=file)
            file.write('\n')
        traceback.print_exc()
    finally:
        Relay.value = False

        
