import board
import digitalio
import adafruit_max31856

# Create sensor object, communicating over the board's default SPI bus
spi = board.SPI()

# allocate a CS pin and set the direction
cs5 = digitalio.DigitalInOut(board.D5)
cs5.direction = digitalio.Direction.OUTPUT
cs25 = digitalio.DigitalInOut(board.D25)
cs25.direction = digitalio.Direction.OUTPUT
cs24 = digitalio.DigitalInOut(board.D24)
cs24.direction = digitalio.Direction.OUTPUT

# create a thermocouple object with the above
thermocouple1 = adafruit_max31856.MAX31856(spi, cs5,thermocouple_type=1)
thermocouple2 = adafruit_max31856.MAX31856(spi, cs25,thermocouple_type=3)
thermocouple3 = adafruit_max31856.MAX31856(spi, cs24,thermocouple_type=1)

# measure the temperature! (takes approx 160ms)
while True:
    print(thermocouple1.temperature,thermocouple2.temperature,thermocouple3.temperature)

