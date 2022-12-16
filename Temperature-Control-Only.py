"""
@Author: Andrei Gogosha
Python file to run the temperature control of the small cryostat.
Need to update PID control values for faster loop exicution
"""
import time
import csv
import keyboard
import os
import board
import digitalio
import adafruit_max31856
import PID
from datetime import datetime as dt
import numpy as np

def log_temps(f_name,header,data):
    temp_log_w=csv.writer(log_file)
    temp_log_w.writerow(data)

def open_file(file_name,data_header):
    log_file = open(os.path.join(ROOT_DIR, 'Logs', file_name),'w',encoding='UTF8', newline='')     #Open the log file in the Log subfolder of the working directory with the specified filename
    temp_log_w = csv.writer(log_file)
    temp_log_w.writerow(data_header)     # writes the data header for the csv file
    
    return log_file     # returns the log file so it can be saved as a variable and manipulated later

def calibrated_temps(temp, TC):
    if 'HeatExB' in TC:
        RawRange =  121
        ReferenceRange = 126
        ActualTemp = (((temp + 117) * ReferenceRange) / RawRange) - 108
    if 'HeatExF' in TC:
        RawRange = 184
        ReferenceRange = 179
        ActualTemp = (((temp + 174) * ReferenceRange) / RawRange) - 161
    if 'ColdHead' in TC:
        #RawRange = 187
        #ReferenceRange = 185
        #ActualTemp = (((temp + 167) * ReferenceRange) / RawRange) - 171
        #Coldhead was consistent in its measurements, atleast at high temps, so leave it alone (pending more testing)
        ActualTemp = temp
    if 'Chamber' in TC:
        #RawRange = 35
        #ReferenceRange = 35
        #At both high and low temps, Chamber was consistently 8 degrees colder than the thermometer measured
        ActualTemp = temp + 7.6
        
    return ActualTemp

if __name__ == '__main__':
    ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname("Temperature Control Only.py")))

    data_f_name='Temp log {}.csv'.format(dt.now().strftime('%m-%d-%Y, %H-%M'))
    data_header=['Rt', 'temp_ch', 'temp_hex_f', 'temp_hex_b', 'temp_chamber','Heat F','Heat B']
    # header reads [Real time, Cold head temp, Heat exchander front temp, heat exhchanger back temp, champer temp, PID controler 1 output, Heater 1 status, PID controler 2 output, Heater 2 status]
    log_file = open_file(data_f_name,data_header)

    # Create sensor object, communicating over the board's default SPI bus
    spi = board.SPI()

    # allocate a CS pin and set the direction
    cs13 = digitalio.DigitalInOut(board.D13)
    cs13.direction = digitalio.Direction.OUTPUT
    cs16 = digitalio.DigitalInOut(board.D16)
    cs16.direction = digitalio.Direction.OUTPUT
    cs25 = digitalio.DigitalInOut(board.D25)
    cs25.direction = digitalio.Direction.OUTPUT
    cs26 = digitalio.DigitalInOut(board.D26)
    cs26.direction = digitalio.Direction.OUTPUT
    HeaterF = digitalio.DigitalInOut(board.D17)
    HeaterF.direction= digitalio.Direction.OUTPUT
    HeaterB = digitalio.DigitalInOut(board.D18)
    HeaterB.direction = digitalio.Direction.OUTPUT

    # create a thermocouple object with the above pin assignements
    ColdHead = adafruit_max31856.MAX31856(spi, cs13,thermocouple_type=adafruit_max31856.ThermocoupleType.T)
    HeatExF = adafruit_max31856.MAX31856(spi, cs16,thermocouple_type=adafruit_max31856.ThermocoupleType.T)     #Heat exchanger thermocouple facing the coldhead
    HeatExB = adafruit_max31856.MAX31856(spi, cs25,thermocouple_type=adafruit_max31856.ThermocoupleType.T)     #Heat exchanger thermocouple facing the chamber
    Chamber = adafruit_max31856.MAX31856(spi, cs26,thermocouple_type=adafruit_max31856.ThermocoupleType.T)

    HeaterF.value = False
    HeatF_on=False
    targetT1 = -115   #initial inputs for PID control
    P1 = 0.2*0.6
    I1 = 1.2*0.2/60
    D1 = 3*0.2*60/40
    #P1 = 20*0.6
    #I1 = 1.2*20/0.5
    #D1 = 3*20*0.5/40

    controllerF = PID.PID(P1, I1, D1)        # create pid control
    controllerF.SetPoint = targetT1             # initialize the controler
    controllerF.setSampleTime(0.25)

    HeaterB.value = False 
    HeatB_on = False
    targetT2 = -94.5     #initial inputr fot PID control
    P2 = 0.2*0.6
    I2 = 1.2*0.2/60
    D2 = 3*0.2*60/40
    #P2 = 20*0.6
    #I2 = 1.2*20/0.5
    #D2 = 3*20*0.5/40

    controllerB = PID.PID(P2, I2, D2)     #creats the pid control
    controllerB.SetPoint = targetT2     #initialize the controler
    controllerB.setSampleTime(0.25)

    Ledger=np.array([[], [], [], [], [], [], []])

    try:     # try and excep statement used to catch error and log them to a specified file
        runlen=1
        itt_len=2
        while True:
            now = time.time() # keep track of when the loop starts so that we keep a consistant loop runtime 
            if os.stat(os.path.join(ROOT_DIR, 'Logs', data_f_name)).st_size>= 4194304:     #checks if the current log file is 4Mb, if it is it creates a new log file 
                data_f_name='Temp log {}.csv'.format(dt.now().strftime('%m-%d-%Y, %H-%M'))
                log_file.close()
                log_file = open_file(data_f_name, data_header)
            #reads the coldhead, heat exchanger front and back, chamber temepratures
            #t1=time.time()
            ColdHead.initiate_one_shot_measurement()
            HeatExF.initiate_one_shot_measurement()
            HeatExB.initiate_one_shot_measurement()
            Chamber.initiate_one_shot_measurement()
            ColdHead._wait_for_oneshot()
            temp_coldhead=calibrated_temps(ColdHead.unpack_temperature(), 'ColdHead')
            if not HeatExF.oneshot_pending:
                temp_HeatExF=calibrated_temps(HeatExF.unpack_temperature(),'HeatExF')
            else:
                HeatExF._wait_for_oneshot()
                temp_HeatExF=calibrated_temps(HeatExF.unpack_temperature(),'HeatExF')
            if not HeatExB.oneshot_pending:
                temp_HeatExB=calibrated_temps(HeatExB.unpack_temperature(),'HeatExF')
            else:
                HeatExB._wait_for_oneshot()
                temp_HeatExB=calibrated_temps(HeatExB.unpack_temperature(),'HeatExF')
            if not Chamber.oneshot_pending:
                temp_chamber=calibrated_temps(Chamber.unpack_temperature(),'HeatExF')
            else:
                Chamber._wait_for_oneshot()
                temp_chamber=calibrated_temps(Chamber.unpack_temperature(),'HeatExF')
            #t2=time.time()
            controllerF.update(temp_HeatExF) # update the pid controlers
            controllerB.update(temp_HeatExB)
            MV1 = controllerF.output # get the new pid values
            MV2 = controllerB.output
            if MV1 > 0:      #temp too low turn heater on
                HeaterF.value = True
                HeatF_status = 1
            else:     #turn heat off
                HeaterF.value = False
                HeatF_status = 0
            if MV2 > 0:     #temp too low turn heater on
                HeaterB.value = True
                HeatB_status = 1
            else:     #turn heat off
                HeaterB.value = False
                HeatB_status = 0
            time_stamp= dt.now().strftime('%H:%M:%S')     #timestamp used for x axis tick
            #t3 = time.time()
            Ledger=np.append(Ledger,[[time_stamp], [temp_coldhead], [temp_HeatExF], [temp_HeatExB], [temp_chamber], [HeatF_status], [HeatB_status]],axis=1 )
            if runlen==itt_len:     #change to be however many itterations you want before updating logs
                Coldhead_avg=np.average(Ledger[1,-itt_len:].astype('float32'))
                HeatExF_avg=np.average(Ledger[2,-itt_len:].astype('float32'))
                HeatExB_avg=np.average(Ledger[3,-itt_len:].astype('float32'))
                Chamber_avg=np.average(Ledger[4,-itt_len:].astype('float32'))
                log_temps(data_f_name,data_header,[time_stamp, Coldhead_avg, HeatExF_avg, HeatExB_avg, Chamber_avg, HeatF_status , HeatB_status])     #write to temp log file
                log_file.flush() #pushes the data collected this loop to the csv.
                runlen = 0
            if len(Ledger[1])>=itt_len+1:     #only holds onto last itt len +1 temperatures in memory
                Ledger=np.delete(Ledger, obj=0,axis=1)
            #t4=time.time()
            elapsed = time.time() - now # how long was it running?
            #print(t2-t1,t4-t3,elapsed)
            #print(Ledger[:,-1:])
            try:
                time.sleep(0.25-elapsed)     # make the loop run every 1 seconds
            except: 
                time.sleep(0.1)
            runlen += 1
            
    #Opens the relays (stops the heaters) when program interrupted
    except Exception as e:
        HeaterF.value = False
        HeatF_on = False
        HeaterB.value = False
        HeatB_on = False
        
        if e == 'KeyboardInterrupt':
            print('Interrupted')
        else:      #code to write any errors to a specified error log file in the logs subdirectory of the working directory
            if not os.path.exists(os.path.join(ROOT_DIR, 'Logs', 'Error Logs.txt')):
                with open(os.path.join(ROOT_DIR, 'Logs', 'Error Logs'), 'w', encoding='UTF-8') as file:
                    file.write('')
            with open(os.path.join(ROOT_DIR, 'Logs', 'Error Logs'), 'a', encoding='UTF-8') as file:
                file.write('-------------------------------------------------'+'\n')
                file.write(dt.now().strftime('%Y-%m-%d %H:%M:%S')+'\n')
                traceback.print_exc(file=file)
                file.write('\n')
            traceback.print_exc()
