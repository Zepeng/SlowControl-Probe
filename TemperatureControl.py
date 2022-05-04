import serial                                                              #Serial imported for Serial communication
import time                                                                #Required to use delay functions
ser = serial.Serial(port='/dev/cu.usbmodem1424101', baudrate=9600)
ser.flushInput()

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

ArduinoUnoSerial = serial.Serial('/dev/cu.usbmodem1424201',9600)       #Create Serial port object called ArduinoUnoSerialData time
time.sleep(2)
ArduinoUnoSerial.flush()
#wait for 2 secounds for the communication to get established
ser_bytes = ser.readline()
value = float(ser_bytes.strip())
T1 = 40
t = 0
while True:
    t = t + 1
    ser_bytes = ser.readline()
    if len(ser_bytes) < 7:
        ser_bytes = ser.readline()
    ser.reset_input_buffer()
    value = float(ser_bytes.strip())
    controller.update(value) # compute manipulated variable
    MV = controller.output # apply
    print(t, value, MV)
    if MV > 0:
        ArduinoUnoSerial.write(b'11')
        ArduinoUnoSerial.readline()
    else:
        ArduinoUnoSerial.write(b'10')
        ArduinoUnoSerial.readline()
