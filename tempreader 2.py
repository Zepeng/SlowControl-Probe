# SPDX-FileCopyrightText: 2018 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`MAX31856`
====================================================
CircuitPython module for the MAX31856 Universal Thermocouple Amplifier. See
examples/simpletest.py for an example of the usage.
* Author(s): Bryan Siepert
Implementation Notes
--------------------
**Hardware:**
* Adafruit `Universal Thermocouple Amplifier MAX31856 Breakout
  <https://www.adafruit.com/product/3263>`_ (Product ID: 3263)
**Software and Dependencies:**
* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""
import math
from time import sleep
from micropython import const
from adafruit_bus_device.spi_device import SPIDevice

try:
    from typing import Dict, Tuple
    from typing_extensions import Literal
    from busio import SPI
    from digitalio import DigitalInOut
except ImportError:
    pass

try:
    from struct import unpack
except ImportError:
    from ustruct import unpack

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_MAX31856.git"

# Register constants
_MAX31856_CR0_REG = const(0x00)
_MAX31856_CR0_AUTOCONVERT = const(0x80)
_MAX31856_CR0_1SHOT = const(0x40)
_MAX31856_CR0_OCFAULT1 = const(0x20)
_MAX31856_CR0_OCFAULT0 = const(0x10)
_MAX31856_CR0_CJ = const(0x08)
_MAX31856_CR0_FAULT = const(0x04)
_MAX31856_CR0_FAULTCLR = const(0x02)
_MAX31856_CR0_50HZ = const(0x01)

_MAX31856_CR1_REG = const(0x01)
_MAX31856_MASK_REG = const(0x02)
_MAX31856_CJHF_REG = const(0x03)
_MAX31856_CJLF_REG = const(0x04)
_MAX31856_LTHFTH_REG = const(0x05)
_MAX31856_LTHFTL_REG = const(0x06)
_MAX31856_LTLFTH_REG = const(0x07)
_MAX31856_LTLFTL_REG = const(0x08)
_MAX31856_CJTO_REG = const(0x09)
_MAX31856_CJTH_REG = const(0x0A)
_MAX31856_CJTL_REG = const(0x0B)
_MAX31856_LTCBH_REG = const(0x0C)
_MAX31856_LTCBM_REG = const(0x0D)
_MAX31856_LTCBL_REG = const(0x0E)
_MAX31856_SR_REG = const(0x0F)

# fault types
_MAX31856_FAULT_CJRANGE = const(0x80)
_MAX31856_FAULT_TCRANGE = const(0x40)
_MAX31856_FAULT_CJHIGH = const(0x20)
_MAX31856_FAULT_CJLOW = const(0x10)
_MAX31856_FAULT_TCHIGH = const(0x08)
_MAX31856_FAULT_TCLOW = const(0x04)
_MAX31856_FAULT_OVUV = const(0x02)
_MAX31856_FAULT_OPEN = const(0x01)

_AVGSEL_CONSTS = {1: 0x00, 2: 0x10, 4: 0x20, 8: 0x30, 16: 0x40}


class ThermocoupleType:  # pylint: disable=too-few-public-methods
    """An enum-like class representing the different types of thermocouples that the MAX31856 can
    use. The values can be referenced like ``ThermocoupleType.K`` or ``ThermocoupleType.S``
    Possible values are
    - ``ThermocoupleType.B``
    - ``ThermocoupleType.E``
    - ``ThermocoupleType.J``
    - ``ThermocoupleType.K``
    - ``ThermocoupleType.N``
    - ``ThermocoupleType.R``
    - ``ThermocoupleType.S``
    - ``ThermocoupleType.T``
    """

    # pylint: disable=invalid-name
    B = 0b0000
    E = 0b0001
    J = 0b0010
    K = 0b0011
    N = 0b0100
    R = 0b0101
    S = 0b0110
    T = 0b0111
    G8 = 0b1000
    G32 = 0b1100


class MAX31856:
    """Driver for the MAX31856 Universal Thermocouple Amplifier
    :param ~busio.SPI spi: The SPI bus the MAX31856 is connected to.
    :param ~microcontroller.Pin cs: The pin used for the CS signal.
    :param ~adafruit_max31856.ThermocoupleType thermocouple_type: The type of thermocouple.\
      Default is Type K.
    :param ~int sampling: Number of samples to be averaged [1,2,4,8,16]
    :param ~bool filter_50hz: Filter 50Hz mains frequency instead of 60Hz
    **Quickstart: Importing and using the MAX31856**
        Here is an example of using the :class:`MAX31856` class.
        First you will need to import the libraries to use the sensor
        .. code-block:: python
            import board
            from digitalio import DigitalInOut, Direction
            import adafruit_max31856
        Once this is done you can define your `board.SPI` object and define your sensor object
        .. code-block:: python
            spi = board.SPI()
            cs = digitalio.DigitalInOut(board.D5)  # Chip select of the MAX31856 board.
            sensor = adafruit_max31856.MAX31856(spi, cs)
        Now you have access to the :attr:`temperature` attribute
        .. code-block:: python
            temperature = sensor.temperature
    """

    # A class level buffer to reduce allocations for reading and writing.
    # Tony says this isn't re-entrant or thread safe!
    _BUFFER = bytearray(4)

    def __init__(
        self, spi: SPI, cs: DigitalInOut, thermocouple_type: int = ThermocoupleType.K
    ) -> None:
        self._device = SPIDevice(spi, cs, baudrate=500000, polarity=0, phase=1)

        # assert on any fault
        self._write_u8(_MAX31856_MASK_REG, 0x0)
        # configure open circuit faults
        self._write_u8(_MAX31856_CR0_REG, _MAX31856_CR0_OCFAULT0)

        # set thermocouple type
        self._set_thermocouple_type(thermocouple_type)

    def _set_thermocouple_type(self, thermocouple_type: ThermocoupleType) -> None:
        # get current value of CR1 Reg
        conf_reg_1 = self._read_register(_MAX31856_CR1_REG, 1)[0]
        conf_reg_1 &= 0xF0  # mask off bottom 4 bits
        # add the new value for the TC type
        conf_reg_1 |= int(thermocouple_type) & 0x0F
        self._write_u8(_MAX31856_CR1_REG, conf_reg_1)

    @property
    def averaging(self) -> int:
        """Number of samples averaged together in each result.
        Must be 1, 2, 4, 8, or 16. Default is 1 (no averaging).
        """
        conf_reg_1 = self._read_register(_MAX31856_CR1_REG, 1)[0]
        avgsel = conf_reg_1 & ~0b10001111  # clear bits other than 4-6
        # check which byte this corresponds to
        for key, value in _AVGSEL_CONSTS.items():
            if value == avgsel:
                return key
        raise KeyError(f"AVGSEL bit pattern was not recognised ({avgsel:>08b})")

    @averaging.setter
    def averaging(self, num_samples: int) -> None:
        # This option is set in bits 4-6 of register CR1.
        if num_samples not in _AVGSEL_CONSTS:
            raise ValueError("Num_samples must be one of 1,2,4,8,16")
        avgsel = _AVGSEL_CONSTS[num_samples]
        # get current value of CR1 Reg
        conf_reg_1 = self._read_register(_MAX31856_CR1_REG, 1)[0]
        conf_reg_1 &= 0b10001111  # clear bits 4-6
        # OR the AVGSEL bits (4-6)
        conf_reg_1 |= avgsel
        self._write_u8(_MAX31856_CR1_REG, conf_reg_1)

    @property
    def noise_rejection(self) -> Literal[50, 60]:
        """
        The frequency (Hz) to be used by the noise rejection filter.
        Must be 50 or 60. Default is 60."""
        # this value is stored in bit 0 of register CR0.
        conf_reg_0 = self._read_register(_MAX31856_CR0_REG, 1)[0]
        if conf_reg_0 & _MAX31856_CR0_50HZ:
            return 50
        return 60

    @noise_rejection.setter
    def noise_rejection(self, frequency: Literal[50, 60]) -> None:
        conf_reg_0 = self._read_register(_MAX31856_CR0_REG, 1)[0]
        if frequency == 50:
            conf_reg_0 |= _MAX31856_CR0_50HZ  # set the 50hz bit
        elif frequency == 60:
            conf_reg_0 &= ~_MAX31856_CR0_50HZ  # clear the 50hz bit
        else:
            raise ValueError("Frequency must be 50 or 60")
        self._write_u8(_MAX31856_CR0_REG, conf_reg_0)

    @property
    def temperature(self) -> float:
        """Measure the temperature of the sensor and wait for the result.
        Return value is in degrees Celsius. (read-only)"""
        self._perform_one_shot_measurement()
        return self.unpack_temperature()

    def unpack_temperature(self) -> float:
        """Reads the probe temperature from the register"""
        # unpack the 3-byte temperature as 4 bytes
        raw_temp = unpack(
            ">i", self._read_register(_MAX31856_LTCBH_REG, 3) + bytes([0])
        )[0]

        # shift to remove extra byte from unpack needing 4 bytes
        raw_temp >>= 8

        # effectively shift raw_read >> 12 to convert pseudo-float
        temp_float = raw_temp / 4096.0

        return temp_float

    @property
    def reference_temperature(self) -> float:
        """Wait to retrieve temperature of the cold junction in degrees Celsius. (read-only)"""
        self._perform_one_shot_measurement()
        return self.unpack_reference_temperature()

    def unpack_reference_temperature(self) -> float:
        """Reads the reference temperature from the register"""
        raw_read = unpack(">h", self._read_register(_MAX31856_CJTH_REG, 2))[0]

        # effectively shift raw_read >> 8 to convert pseudo-float
        cold_junction_temp = raw_read / 256.0

        return cold_junction_temp

    @property
    def temperature_thresholds(self) -> Tuple[float, float]:
        """The thermocouple's low and high temperature thresholds
        as a ``(low_temp, high_temp)`` tuple
        """

        raw_low = unpack(">h", self._read_register(_MAX31856_LTLFTH_REG, 2))
        raw_high = unpack(">h", self._read_register(_MAX31856_LTHFTH_REG, 2))

        return (round(raw_low[0] / 16.0, 1), round(raw_high[0] / 16.0, 1))

    @temperature_thresholds.setter
    def temperature_thresholds(self, val: Tuple[float, float]) -> None:

        int_low = int(val[0] * 16)
        int_high = int(val[1] * 16)

        self._write_u8(_MAX31856_LTHFTH_REG, int_high >> 8)
        self._write_u8(_MAX31856_LTHFTL_REG, int_high)

        self._write_u8(_MAX31856_LTLFTH_REG, int_low >> 8)
        self._write_u8(_MAX31856_LTLFTL_REG, int_low)

    @property
    def reference_temperature_thresholds(  # pylint: disable=invalid-name,
        self,
    ) -> Tuple[float, float]:
        """The cold junction's low and high temperature thresholds
        as a ``(low_temp, high_temp)`` tuple
        """
        return (
            float(unpack("b", self._read_register(_MAX31856_CJLF_REG, 1))[0]),
            float(unpack("b", self._read_register(_MAX31856_CJHF_REG, 1))[0]),
        )

    @reference_temperature_thresholds.setter
    def reference_temperature_thresholds(  # pylint: disable=invalid-name,
        self, val: Tuple[float, float]
    ) -> None:

        self._write_u8(_MAX31856_CJLF_REG, int(val[0]))
        self._write_u8(_MAX31856_CJHF_REG, int(val[1]))

    @property
    def fault(self) -> Dict[str, bool]:
        """A dictionary with the status of each fault type where the key is the fault type and the
        value is a bool if the fault is currently active
        ===================   =================================
        Key                   Fault type
        ===================   =================================
        "cj_range"            Cold junction range fault
        "tc_range"            Thermocouple range fault
        "cj_high"             Cold junction high threshold fault
        "cj_low"              Cold junction low threshold fault
        "tc_high"             Thermocouple high threshold fault
        "tc_low"              Thermocouple low threshold fault
        "voltage"             Over/under voltage fault
        "open_tc"             Thermocouple open circuit fault
        ===================   =================================
        """
        faults = self._read_register(_MAX31856_SR_REG, 1)[0]

        return {
            "cj_range": bool(faults & _MAX31856_FAULT_CJRANGE),
            "tc_range": bool(faults & _MAX31856_FAULT_TCRANGE),
            "cj_high": bool(faults & _MAX31856_FAULT_CJHIGH),
            "cj_low": bool(faults & _MAX31856_FAULT_CJLOW),
            "tc_high": bool(faults & _MAX31856_FAULT_TCHIGH),
            "tc_low": bool(faults & _MAX31856_FAULT_TCLOW),
            "voltage": bool(faults & _MAX31856_FAULT_OVUV),
            "open_tc": bool(faults & _MAX31856_FAULT_OPEN),
        }

    def _perform_one_shot_measurement(self) -> None:
        self.initiate_one_shot_measurement()
        # wait for the measurement to complete
        self._wait_for_oneshot()

    def initiate_one_shot_measurement(self) -> None:
        """Starts a one-shot measurement and returns immediately.
        A measurement takes approximately 160ms.
        Check the status of the measurement with `oneshot_pending`; when it is false,
        the measurement is complete and the value can be read with `unpack_temperature`.
        """
        # read the current value of the first config register
        conf_reg_0 = self._read_register(_MAX31856_CR0_REG, 1)[0]

        # and the complement to guarantee the autoconvert bit is unset
        conf_reg_0 &= ~_MAX31856_CR0_AUTOCONVERT
        # or the oneshot bit to ensure it is set
        conf_reg_0 |= _MAX31856_CR0_1SHOT

        # write it back with the new values, prompting the sensor to perform a measurement
        self._write_u8(_MAX31856_CR0_REG, conf_reg_0)

    @property
    def oneshot_pending(self) -> bool:
        """A boolean indicating the status of the one-shot flag.
        A True value means the measurement is still ongoing.
        A False value means measurement is complete."""
        oneshot_flag = (
            self._read_register(_MAX31856_CR0_REG, 1)[0] & _MAX31856_CR0_1SHOT
        )
        return bool(oneshot_flag)

    def _wait_for_oneshot(self) -> None:
        while self.oneshot_pending:
            sleep(0.01)

    def _read_register(self, address: int, length: int) -> bytearray:
        # pylint: disable=no-member
        # Read a 16-bit BE unsigned value from the specified 8-bit address.
        with self._device as device:
            self._BUFFER[0] = address & 0x7F
            device.write(self._BUFFER, end=1)
            device.readinto(self._BUFFER, end=length)
        return self._BUFFER[:length]

    def _write_u8(self, address: int, val: int) -> None:
        # Write an 8-bit unsigned value to the specified 8-bit address.
        with self._device as device:
            self._BUFFER[0] = (address | 0x80) & 0xFF
            self._BUFFER[1] = val & 0xFF
            device.write(self._BUFFER, end=2)  # pylint: disable=no-member
    @property
    def temperature_NIST_K(self) -> float:
        """
        Thermocouple temperature in degrees Celsius, computed using
        raw voltages and NIST approximation for Type K, see:
        https://srdata.nist.gov/its90/download/type_k.tab
        """
        # pylint: disable=invalid-name
        # temperature of remote thermocouple junction
        TR = self.temperature
        # temperature of device (cold junction)
        TAMB = self.reference_temperature
        # thermocouple voltage based on MAX31855's uV/degC for type K (Thermal Characteristics)
        #https://datasheets.maximintegrated.com/en/ds/MAX31855.pdf
        VOUT = 0.041276 * (TR - TAMB)
        # cold junction equivalent thermocouple voltage
        if TAMB <= 0:
            VREF = (
                0.394501280250e-01 * TAMB
                + 0.236223735980e-04 * math.pow(TAMB, 2)
                + -0.328589067840e-06 * math.pow(TAMB, 3)
                + -0.499048287770e-08 * math.pow(TAMB, 4)
                + -0.675090591730e-10 * math.pow(TAMB, 5)
                + -0.574103274280e-12 * math.pow(TAMB, 6)
                + -0.310888728940e-14 * math.pow(TAMB, 7)
                + -0.104516093650e-16 * math.pow(TAMB, 8)
                + -0.198892668780e-19 * math.pow(TAMB, 9)
                + -0.163226974860e-22 * math.pow(TAMB, 10)
            )
        else:
            VREF = (
                -0.176004136860e-01
                + 0.389212049750e-01 * TAMB
                + 0.185587700320e-04 * math.pow(TAMB, 2)
                + -0.994575928740e-07 * math.pow(TAMB, 3)
                + 0.318409457190e-09 * math.pow(TAMB, 4)
                + -0.560728448890e-12 * math.pow(TAMB, 5)
                + 0.560750590590e-15 * math.pow(TAMB, 6)
                + -0.320207200030e-18 * math.pow(TAMB, 7)
                + 0.971511471520e-22 * math.pow(TAMB, 8)
                + -0.121047212750e-25 * math.pow(TAMB, 9)
                + 0.1185976 * math.exp(-0.1183432e-03 * math.pow(TAMB - 0.1269686e03, 2))
            )
        # total thermoelectric voltage
        VTOTAL = VOUT + VREF
        # determine coefficients
        # https://srdata.nist.gov/its90/type_k/kcoefficients_inverse.html
        if -5.891 <= VTOTAL <= 0:
            DCOEF = (
                0.0000000e00,
                2.5173462e01,
                -1.1662878e00,
                -1.0833638e00,
                -8.9773540e-01,
                -3.7342377e-01,
                -8.6632643e-02,
                -1.0450598e-02,
                -5.1920577e-04,
            )
        elif 0 < VTOTAL <= 20.644:
            DCOEF = (
                0.000000e00,
                2.508355e01,
                7.860106e-02,
                -2.503131e-01,
                8.315270e-02,
                -1.228034e-02,
                9.804036e-04,
                -4.413030e-05,
                1.057734e-06,
                -1.052755e-08,
            )
        elif 20.644 < VTOTAL <= 54.886:
            DCOEF = (
                -1.318058e02,
                4.830222e01,
                -1.646031e00,
                5.464731e-02,
                -9.650715e-04,
                8.802193e-06,
                -3.110810e-08,
            )
        else:
            raise RuntimeError(f"Total thermoelectric voltage out of range:{VTOTAL}")
        # compute temperature
        TEMPERATURE = 0
        for n, c in enumerate(DCOEF):
            TEMPERATURE += c * math.pow(VTOTAL, n)
        return TEMPERATURE

    @property
    def temperature_NIST_J(self) -> float:
        """
        Thermocouple temperature in degrees Celsius, computed using
        raw voltages and NIST approximation for Type j, see:
        https://srdata.nist.gov/its90/download/type_j.tab
        """
        # pylint: disable=invalid-name
        # temperature of remote thermocouple junction
        TR = self.temperature
        # temperature of device (cold junction)
        TAMB = self.reference_temperature
        # thermocouple voltage based on MAX31855's uV/degC for type j (Thermal Characteristics)
        # https://datasheets.maximintegrated.com/en/ds/MAX31855.pdf
        VOUT = 0.057953 * (TR - TAMB)
        # cold junction equivalent thermocouple voltage
        if TAMB <= 760:
            VREF = (
                0.503811878150e-01 * TAMB
                + 0.304758369300e-04 * math.pow(TAMB, 2)
                + -0.856810657200e-07 * math.pow(TAMB, 3)
                + 0.132281952950e-09 * math.pow(TAMB, 4)
                + -0.170529583370e-12 * math.pow(TAMB, 5)
                + 0.209480906970e-15 * math.pow(TAMB, 6)
                + -0.125383953360e-18 * math.pow(TAMB, 7)
                + 0.156317256970e-22 * math.pow(TAMB, 8)
            )
        else:
            VREF = (
                0.296456256810e+03,
                + -0.149761277860e+01 * TAMB
                + 0.317871039240e-02 * math.pow(TAMB, 2)
                + -0.318476867010e-05 * math.pow(TAMB, 3)
                + 0.157208190040e-08 * math.pow(TAMB, 4)
                + -0.306913690560e-12 * math.pow(TAMB, 5)
            )
        # total thermoelectric voltage
        VTOTAL = VOUT + VREF
        # determine coefficients
        # https://srdata.nist.gov/its90/type_j/jcoefficients_inverse.html
        if -8.095 <= VTOTAL <= 0:
            DCOEF = (
                0.0000000e00,
                1.9528268e+01,
                -1.2286185e+00,
                -1.0752178e+00,
                -5.9086933e-01,
                -1.7256713e-01,
                -2.8131513e-02,
                -2.3963370e-03,
                -8.3823321e-05,
            )
        elif 0 < VTOTAL <= 42.919:
            DCOEF = (
                0.000000e00,
                1.978425e+01,
                -2.001204e-01,
                1.036969e-02,
                -2.549687e-04,
                3.585153e-06,
                -5.344285e-08,
                5.099890e-10,
            )
        elif 42.919 < VTOTAL <= 69.553:
            DCOEF = (
                -3.11358187e+03,
                3.00543684e+02,
                -9.94773230e+01,
                1.70276630e-01,
                -1.43033468e-03,
                4.73886084e-06,
            )
        else:
            raise RuntimeError(f"Total thermoelectric voltage out of range:{VTOTAL}")
        # compute temperature
        TEMPERATURE = 0
        for n, c in enumerate(DCOEF):
            TEMPERATURE += c * math.pow(VTOTAL, n)
        return TEMPERATURE
    
    @property
    def temperature_NIST_N(self) -> float:
        """
        Thermocouple temperature in degrees Celsius, computed using
        raw voltages and NIST approximation for Type n, see:
        https://srdata.nist.gov/its90/download/type_n.tab
        """
        # pylint: disable=invalid-name
        # temperature of remote thermocouple junction
        TR = self.temperature
        # temperature of device (cold junction)
        TAMB = self.reference_temperature
        # thermocouple voltage based on MAX31855's uV/degC for type n (Thermal Characteristics)
        # https://datasheets.maximintegrated.com/en/ds/MAX31855.pdf
        VOUT = 0.036256 * (TR - TAMB)
        # cold junction equivalent thermocouple voltage
        if TAMB <= 0:
            VREF = (
                0.261591059620e-01 * TAMB
                + 0.109574842280e-04 * math.pow(TAMB, 2)
                + -0.938411115540e-07 * math.pow(TAMB, 3)
                + -0.464120397590e-10 * math.pow(TAMB, 4)
                + -0.263033577160e-11 * math.pow(TAMB, 5)
                + -0.226534380030e-13 * math.pow(TAMB, 6)
                + -0.760893007910e-16 * math.pow(TAMB, 7)
                + -0.934196678350e-19 * math.pow(TAMB, 8)
            )

        else:
            VREF = (
                0.259293946010E-01 * TAMB
                + 0.157101418800E-04 * math.pow(TAMB, 2)
                + 0.438256272370E-07 * math.pow(TAMB, 3)
                + -0.252611697940E-09 * math.pow(TAMB, 4)
                + 0.643118193390E-12 * math.pow(TAMB, 5)
                + -0.100634715190E-14 * math.pow(TAMB, 6)
                + 0.997453389920E-18 * math.pow(TAMB, 7)
                + -0.608632456070E-21 * math.pow(TAMB, 8)
                + 0.208492293390E-24 * math.pow(TAMB, 9)
                + -0.306821961510E-28 * math.pow(TAMB, 10)
            )
            
        # total thermoelectric voltage
        VTOTAL = VOUT + VREF
        # determine coefficients
        # https://srdata.nist.gov/its90/type_n/ncoefficients_inverse.html
        if -3.990 <= VTOTAL <= 0:
            DCOEF = (
                0.0000000e00,
                3.8436847e+01,
                1.1010485e+00,
                5.2229312e+00,
                7.2060525e+00,
                5.8488586e+00,
                2.7754916e+00,
                7.7075166e-01,
                1.1582665e-01,
                7.3138868e-03,
            )
        elif 0 < VTOTAL <= 20.613:
            DCOEF = (
                0.000000e00,
                3.86896e+01,
                -1.08267e+00,
                4.70205e-02,
                -2.12169e-06,
                -1.17272e-04,
                5.39280e-06,
                -7.98156e-08,
            )
        elif 20.613 < VTOTAL <= 47.513:
            DCOEF = (
                1.972485e+01,
                3.300943e+01,
                -3.915159e-01,
                9.855391e-03,
                -1.274371e-04,
                7.767022e-07,
            )
        else:
            raise RuntimeError(f"Total thermoelectric voltage out of range:{VTOTAL}")
        # compute temperature
        TEMPERATURE = 0
        for n, c in enumerate(DCOEF):
            TEMPERATURE += c * math.pow(VTOTAL, n)
        return TEMPERATURE
    
    @property
    def temperature_NIST_T(self) -> float:
        """
        Thermocouple temperature in degrees Celsius, computed using
        raw voltages and NIST approximation for Type t, see:
        https://srdata.nist.gov/its90/download/type_t.tab
        """
        # pylint: disable=invalid-name
        # temperature of remote thermocouple junction
        TR = self.temperature
        # temperature of device (cold junction)
        TAMB = self.reference_temperature
        # thermocouple voltage based on MAX31855's uV/degC for type t (Thermal Characteristics)
        # https://datasheets.maximintegrated.com/en/ds/MAX31855.pdf
        VOUT = 0.05218 * (TR - TAMB)
        # cold junction equivalent thermocouple voltage
        if TAMB <= 0:
            VREF = (
                0.387481063640e-01 * TAMB
                + 0.441944343470e-04 * math.pow(TAMB, 2)
                + 0.118443231050e-06 * math.pow(TAMB, 3)
                + 0.200329735540e-07 * math.pow(TAMB, 4)
                + 0.901380195590e-09 * math.pow(TAMB, 5)
                + 0.226511565930e-10 * math.pow(TAMB, 6)
                + 0.360711542050e-12 * math.pow(TAMB, 7)
                + 0.384939398830e-14 * math.pow(TAMB, 8)
                + 0.282135219250e-16 * math.pow(TAMB, 9)
                + 0.142515947790e-18 * math.pow(TAMB, 10)
                + 0.487686622860e-21 * math.pow(TAMB, 11)
                + 0.107955392700e-23 * math.pow(TAMB, 12)
                + 0.139450270620e-26 * math.pow(TAMB, 13)
                + 0.797951539270e-30 * math.pow(TAMB, 14)
            )

        else:
            VREF = (
                0.387481063640e-01 * TAMB
                + 0.332922278800e-04 * math.pow(TAMB, 2)
                + 0.206182434040e-06 * math.pow(TAMB, 3)
                + -0.218822568460e-08 * math.pow(TAMB, 4)
                + 0.109968809280e-10 * math.pow(TAMB, 5)
                + -0.308157587720e-13 * math.pow(TAMB, 6)
                + 0.454791352900e-16 * math.pow(TAMB, 7)
                + -0.275129016730e-19 * math.pow(TAMB, 8)
            )
            
        # total thermoelectric voltage
        VTOTAL = VOUT + VREF
        # determine coefficients
        # https://srdata.nist.gov/its90/type_t/tcoefficients_inverse.html
        if -5.603 <= VTOTAL <= 0:
            DCOEF = (
                0.0000000e00,
                2.5949192e+01,
                -2.1316967e-01,
                7.9018692e-01,
                4.2527777e-01,
                1.3304473e-01,
                2.0241446e-02,
                1.2668171e-03,
            )
        elif 0 < VTOTAL <= 20.872:
            DCOEF = (
                0.000000e00,
                2.592800e+01,
                -7.602961e-01,
                4.637791e-02,
                -2.165394e-03,
                6.048144e-05,
                -7.293422e-07,
            )
        else:
            raise RuntimeError(f"Total thermoelectric voltage out of range:{VTOTAL}")
        # compute temperature
        TEMPERATURE = 0
        for n, c in enumerate(DCOEF):
            TEMPERATURE += c * math.pow(VTOTAL, n)
        return TEMPERATURE

    @property
    def temperature_NIST_E(self) -> float:
        """
        Thermocouple temperature in degrees Celsius, computed using
        raw voltages and NIST approximation for Type e, see:
        https://srdata.nist.gov/its90/download/type_e.tab
        """
        # pylint: disable=invalid-name
        # temperature of remote thermocouple junction
        TR = self.temperature
        # temperature of device (cold junction)
        TAMB = self.reference_temperature
        # thermocouple voltage based on MAX31855's uV/degC for type e (Thermal Characteristics)
        # https://datasheets.maximintegrated.com/en/ds/MAX31855.pdf
        VOUT = 0.076373 * (TR - TAMB)
        # cold junction equivalent thermocouple voltage
        if TAMB <= 0:
            VREF = (
                0.586655087080e-01 * TAMB
                + 0.454109771240e-04 * math.pow(TAMB, 2)
                + -0.779980486860e-06 * math.pow(TAMB, 3)
                + -0.258001608430e-07 * math.pow(TAMB, 4)
                + -0.594525830570e-09 * math.pow(TAMB, 5)
                + -0.932140586670e-11 * math.pow(TAMB, 6)
                + -0.102876055340e-12 * math.pow(TAMB, 7)
                + -0.803701236210e-15 * math.pow(TAMB, 8)
                + -0.439794973910e-17 * math.pow(TAMB, 9)
                + -0.164147763550e-19 * math.pow(TAMB, 10)
                + -0.396736195160e-22 * math.pow(TAMB, 11)
                + -0.558273287210e-25 * math.pow(TAMB, 12)
                + -0.346578420130e-28 * math.pow(TAMB, 13)
            )

        else:
            VREF = (
                0.586655087100e-01 * TAMB
                + 0.450322755820e-04 * math.pow(TAMB, 2)
                + 0.289084072120e-07 * math.pow(TAMB, 3)
                + -0.330568966520e-09 * math.pow(TAMB, 4)
                + 0.650244032700e-12 * math.pow(TAMB, 5)
                + -0.191974955040e-15 * math.pow(TAMB, 6)
                + -0.125366004970e-17 * math.pow(TAMB, 7)
                + 0.214892175690e-20 * math.pow(TAMB, 8)
                + -0.143880417820e-23 * math.pow(TAMB, 9)
                + 0.359608994810e-27 * math.pow(TAMB, 10)
            )
            
        # total thermoelectric voltage
        VTOTAL = VOUT + VREF
        # determine coefficients
        # https://srdata.nist.gov/its90/type_e/ecoefficients_inverse.html
        if -8.825 <= VTOTAL <= 0:
            DCOEF = (
                0.0000000e00,
                1.6977288e+01,
                -4.3514970e-01,
                -1.5859697e-01,
                -9.2502871e-02,
                -2.6084314e-02,
                -4.1360199e-03,
                -3.4034030e-04,
                -1.1564890e-05,
            )
        elif 0 < VTOTAL <= 76.373:
            DCOEF = (
                0.000000e00,
                1.7057035e+01,
                -2.3301759e-01,
                6.5435585e-03,
                -7.3562749e-05,
                -1.7896001e-06,
                8.4036165e-08,
                -1.3735879e-09,
                1.0629823e-11,
                -3.2447087e-14,
            )
        else:
            raise RuntimeError(f"Total thermoelectric voltage out of range:{VTOTAL}")
        # compute temperature
        TEMPERATURE = 0
        for n, c in enumerate(DCOEF):
            TEMPERATURE += c * math.pow(VTOTAL, n)
        return TEMPERATURE

    @property
    def temperature_NIST_R(self) -> float:
        """
        Thermocouple temperature in degrees Celsius, computed using
        raw voltages and NIST approximation for Type r, see:
        https://srdata.nist.gov/its90/download/type_r.tab
        """
        # pylint: disable=invalid-name
        # temperature of remote thermocouple junction
        TR = self.temperature
        # temperature of device (cold junction)
        TAMB = self.reference_temperature
        # thermocouple voltage based on MAX31855's uV/degC for type r (Thermal Characteristics)
        # https://datasheets.maximintegrated.com/en/ds/MAX31855.pdf
        VOUT = 0.010506 * (TR - TAMB)
        # cold junction equivalent thermocouple voltage
        if TAMB <= 1064.180:
           VREF = (
                0.528961729765e-02 * TAMB
                + 0.528961729765e-02 * math.pow(TAMB, 2)
                + 0.139166589782e-04 * math.pow(TAMB, 3)
                + -0.238855693017e-07 * math.pow(TAMB, 4)
                + 0.356916001063e-10 * math.pow(TAMB, 5)
                + -0.462347666298e-13 * math.pow(TAMB, 6)
                + 0.500777441034e-16 * math.pow(TAMB, 7)
                + -0.373105886191e-19 * math.pow(TAMB, 8)
                + 0.157716482367e-22 * math.pow(TAMB, 9)
                + -0.281038625251e-26 * math.pow(TAMB, 10)
            )
        elif 1064.180 < TAMB <= 1664.500:
             VREF = (
                0.295157925316e+01
                + -0.252061251332e-02 * TAMB
                + 0.159564501865e-04 * math.pow(TAMB, 2)
                + -0.764085947576e-08 * math.pow(TAMB, 3)
                + 0.205305291024e-11 * math.pow(TAMB, 4)
                + -0.293359668173e-15 * math.pow(TAMB, 5)
            )
        else:
            VREF = (
                0.152232118209e+03
                + -0.268819888545e+00 * TAMB
                + 0.171280280471e-03 * math.pow(TAMB, 2)
                + -0.345895706453e-07 * math.pow(TAMB, 3)
                + -0.934633971046e-14 * math.pow(TAMB, 4)
            )
            
        # total thermoelectric voltage
        VTOTAL = VOUT + VREF
        # determine coefficients
        # https://srdata.nist.gov/its90/type_r/rcoefficients_inverse.html
        if -0.226 <= VTOTAL <= 1.923:
            DCOEF = (
                0.0000000e00,
                1.8891380e+02,
                -9.3835290e+01,
                -2.2703580e+02,
                3.5145659e+02,
                -3.8953900e+02,
                2.8239471e+02,
                -1.2607281e+02,
                3.1353611e+01,
                -3.3187769e+00
            )
        elif 1.923 < VTOTAL <= 11.361:
            DCOEF = (
                1.334584505e+01,
                1.472644573e+02,
                -1.844024844e+01,
                4.031129726e+00,
                -6.249428360e-01,
                6.468412046e-02,
                -4.458750426e-03,
                1.994710149e-04,
                -5.313401790e-06,
                6.481976217e-08,

            )
        elif 11.361 < VTOTAL <= 19.739:
            DCOEF = (
                -8.199599416e+01,
                1.553962042e+02,
                -8.342197663e+00,
                4.279433549e-01,
                -1.191577910e-02,
                1.492290091e-04,
            )
        elif 19.739 < VTOTAL <= 21.103:
            DCOEF = (
                3.406177836e+04,
                -7.023729171e+03,
                5.582903813e+02,
                -1.952394635e+01,
                2.560740231e-01,
            )
        else:
            raise RuntimeError(f"Total thermoelectric voltage out of range:{VTOTAL}")
        # compute temperature
        TEMPERATURE = 0
        for n, c in enumerate(DCOEF):
            TEMPERATURE += c * math.pow(VTOTAL, n)
        return TEMPERATURE

    @property
    def temperature_NIST_S(self) -> float:
        """
        Thermocouple temperature in degrees Celsius, computed using
        raw voltages and NIST approximation for Type s, see:
        https://srdata.nist.gov/its90/download/type_s.tab
        """
        # pylint: disable=invalid-name
        # temperature of remote thermocouple junction
        TR = self.temperature
        # temperature of device (cold junction)
        TAMB = self.reference_temperature
        # thermocouple voltage based on MAX31855's uV/degC for type s (Thermal Characteristics)
        # https://datasheets.maximintegrated.com/en/ds/MAX31855.pdf
        VOUT = 0.009587 * (TR - TAMB)
        # cold junction equivalent thermocouple voltage
        if TAMB <= 1064.180:
            VREF = (
                0.540313308631e-02 * TAMB
                + 0.125934289740e-04 * math.pow(TAMB, 2)
                + -0.232477968689e-07 * math.pow(TAMB, 3)
                + 0.322028823036e-10 * math.pow(TAMB, 4)
                + -0.331465196389e-13 * math.pow(TAMB, 5)
                + 0.255744251786e-16 * math.pow(TAMB, 6)
                + -0.125068871393e-19 * math.pow(TAMB, 7)
                + 0.271443176145e-23 * math.pow(TAMB, 8)
            )
        elif 1064.180 < TAMB <= 1664.500:
            VREF = (
                0.132900444085e+01
                + 0.334509311344e-02 * TAMB
                + 0.654805192818e-05 * math.pow(TAMB, 2)
                + -0.164856259209e-08 * math.pow(TAMB, 3)
                + 0.129989605174e-13 * math.pow(TAMB, 4)
            )
        else:
            VREF = (
                0.146628232636e+03
                + -0.258430516752e+00 * TAMB
                + 0.163693574641e-03 * math.pow(TAMB, 2)
                + -0.330439046987e-07 * math.pow(TAMB, 3)
                + -0.943223690612e-14 * math.pow(TAMB, 4)
            )
        # total thermoelectric voltage
        VTOTAL = VOUT + VREF
        # determine coefficients
        # https://srdata.nist.gov/its90/type_s/scoefficients_inverse.html
        if -0.235 <= VTOTAL <= 1.874:
            DCOEF = (
                0.0000000e00,
                1.84949460e+02,
                -8.00504062e+01,
                1.02237430e+02,
                -1.52248592e+02,
                1.88821343e+02,
                -1.59085941e+02,
                8.23027880e+01,
                -2.34181944e+01,
                2.79786260e+00,
            )
        elif 1.874 < VTOTAL <= 10.332:
            DCOEF = (
                1.291507177e+01,
                1.466298863e+02,
                -1.534713402e+01,
                3.145945973e+00,
                -4.163257839e-01,
                3.187963771e-02,
                -1.291637500e-03,
                2.183475087e-05,
                -1.447379511e-07,
                8.211272125e-09,

            )
        elif 10.332 < VTOTAL <= 17.536:
            DCOEF = (
                -8.087801117e+01,
                1.621573104e+0,
                -8.536869453e+00,
                4.719686976e-01,
                -1.441693666e-02,
                2.081618890e-04,
            )
        elif 17.536 < VTOTAL <= 18.693:
            DCOEF = (
                5.333875126e+04,
                -1.235892298e+04,
                1.092657613e+03,
                -4.265693686e+01,
                6.247205420e-01,
            )
        else:
            raise RuntimeError(f"Total thermoelectric voltage out of range:{VTOTAL}")
        # compute temperature
        TEMPERATURE = 0
        for n, c in enumerate(DCOEF):
            TEMPERATURE += c * math.pow(VTOTAL, n)
        return TEMPERATURE