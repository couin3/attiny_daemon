import logging
import os
import sys
import time
import smbus
import struct
from typing import Tuple, Any
from configparser import ConfigParser
from argparse import ArgumentParser, Namespace
from collections.abc import Mapping
from pathlib import Path

class ATTiny:
    REG_LAST_ACCESS          = 0x01
    REG_BAT_VOLTAGE          = 0x11
    REG_EXT_VOLTAGE          = 0x12
    REG_BAT_V_COEFFICIENT    = 0x13
    REG_BAT_V_CONSTANT       = 0x14
    REG_EXT_V_COEFFICIENT    = 0x15
    REG_EXT_V_CONSTANT       = 0x16
    REG_TIMEOUT              = 0x21
    REG_PRIMED               = 0x22
    REG_SHOULD_SHUTDOWN      = 0x23
    REG_FORCE_SHUTDOWN       = 0x24
    REG_LED_OFF_MODE         = 0x25
    REG_RESTART_VOLTAGE      = 0x31
    REG_WARN_VOLTAGE         = 0x32
    REG_UPS_SHUTDOWN_VOLTAGE = 0x33
    REG_TEMPERATURE          = 0x41
    REG_T_COEFFICIENT        = 0x42
    REG_T_CONSTANT           = 0x43
    REG_UPS_CONFIG           = 0x51
    REG_PULSE_LENGTH         = 0x52
    REG_SW_RECOVERY_DELAY    = 0x53
    REG_VEXT_OFF_IS_SHUTDOWN = 0x54
    REG_PULSE_LENGTH_ON      = 0x55
    REG_PULSE_LENGTH_OFF     = 0x56
    REG_VERSION              = 0x80
    REG_FUSE_LOW             = 0x81
    REG_FUSE_HIGH            = 0x82
    REG_FUSE_EXTENDED        = 0x83
    REG_INTERNAL_STATE       = 0x84
    REG_UPTIME               = 0x85
    REG_MCU_STATUS_REG       = 0x86
    REG_INIT_EEPROM          = 0xFF

    _POLYNOME = 0x31

    def __init__(self, bus_number, address, time_const, num_retries):
        self._bus_number = bus_number
        self._address = address
        self._time_const = time_const
        self._num_retries = num_retries

    def addCrc(self, crc, n):
      for bitnumber in range(0,8):
        if ( n ^ crc ) & 0x80 : crc = ( crc << 1 ) ^ self._POLYNOME
        else                  : crc = ( crc << 1 )
        n = n << 1
      return crc & 0xFF

    def calcCRC(self, register, read, len):
      crc = self.addCrc(0, register)
      for elem in range(0, len):
        crc = self.addCrc(crc, read[elem])
      return crc

    def set_timeout(self, timeout):
        return self.set_8bit_value(self.REG_TIMEOUT, timeout)

    def set_primed(self, primed):
        return self.set_8bit_value(self.REG_PRIMED, primed)

    def init_eeprom(self):
        return self.set_8bit_value(self.REG_INIT_EEPROM, 1)

    def set_should_shutdown(self, value):
        return self.set_8bit_value(self.REG_SHOULD_SHUTDOWN, value)

    def set_force_shutdown(self, value):
        return self.set_8bit_value(self.REG_FORCE_SHUTDOWN, value)

    def set_led_off_mode(self, value):
        return self.set_8bit_value(self.REG_LED_OFF_MODE, value)

    def set_ups_configuration(self, value):
        return self.set_8bit_value(self.REG_UPS_CONFIG, value)

    def set_vext_off_is_shutdown(self, value):
        return self.set_8bit_value(self.REG_VEXT_OFF_IS_SHUTDOWN, value)

    def set_8bit_value(self, register, value):
        crc = self.addCrc(0, register)
        crc = self.addCrc(crc, value)

        arg_list = [value, crc]
        for x in range(self._num_retries):
            bus = smbus.SMBus(self._bus_number)
            time.sleep(self._time_const)
            try:
                bus.write_i2c_block_data(self._address, register, arg_list)
                bus.close()
                if (self.get_8bit_value(register)) == value:
                    return True
            except Exception as e:
                logging.debug("Couldn't set 8 bit register " + hex(register) + ". Exception: " + str(e))
        logging.warning("Couldn't set 8 bit register after " + str(x) + " retries.")
        return False

    def set_restart_voltage(self, value):
        return self.set_16bit_value(self.REG_RESTART_VOLTAGE, value)

    def set_warn_voltage(self, value):
        return self.set_16bit_value(self.REG_WARN_VOLTAGE, value)

    def set_ups_shutdown_voltage(self, value):
        return self.set_16bit_value(self.REG_UPS_SHUTDOWN_VOLTAGE, value)

    def set_bat_v_coefficient(self, value):
        return self.set_16bit_value(self.REG_BAT_V_COEFFICIENT, value)

    def set_bat_v_constant(self, value):
        return self.set_16bit_value(self.REG_BAT_V_CONSTANT, value)

    def set_t_coefficient(self, value):
        return self.set_16bit_value(self.REG_T_COEFFICIENT, value)

    def set_t_constant(self, value):
        return self.set_16bit_value(self.REG_T_CONSTANT, value)

    def set_ext_v_coefficient(self, value):
        return self.set_16bit_value(self.REG_EXT_V_COEFFICIENT, value)

    def set_ext_v_constant(self, value):
        return self.set_16bit_value(self.REG_EXT_V_CONSTANT, value)

    def set_pulse_length(self, value):
        return self.set_16bit_value(self.REG_PULSE_LENGTH, value)

    def set_switch_recovery_delay(self, value):
        return self.set_16bit_value(self.REG_SW_RECOVERY_DELAY, value)

    def set_pulse_length_on(self, value):
        return self.set_16bit_value(self.REG_PULSE_LENGTH_ON, value)

    def set_pulse_length_off(self, value):
        return self.set_16bit_value(self.REG_PULSE_LENGTH_OFF, value)

    def set_16bit_value(self, register, value):
        # we interpret every value as a 16-bit signed value
        vals = value.to_bytes(2, byteorder='little', signed=True)
        crc = self.calcCRC(register, vals, 2)

        arg_list = [vals[0], vals[1], crc]

        for x in range(self._num_retries):
            bus = smbus.SMBus(self._bus_number)
            time.sleep(self._time_const)
            try:
                bus.write_i2c_block_data(self._address, register, arg_list)
                bus.close()
                if (self.get_16bit_value(register)) == value:
                    return True
            except Exception as e:
                logging.debug("Couldn't set 16 bit register " + hex(register) + ". Exception: " + str(e))
        logging.warning("Couldn't set 16 bit register after " + str(x) + " retries.")
        return False

    def get_last_access(self):
        return self.get_16bit_value(self.REG_LAST_ACCESS)

    def get_bat_voltage(self):
        return self.get_16bit_value(self.REG_BAT_VOLTAGE)

    def get_ext_voltage(self):
        return self.get_16bit_value(self.REG_EXT_VOLTAGE)

    def get_bat_v_coefficient(self):
        return self.get_16bit_value(self.REG_BAT_V_COEFFICIENT)

    def get_bat_v_constant(self):
        return self.get_16bit_value(self.REG_BAT_V_CONSTANT)

    def get_ext_v_coefficient(self):
        return self.get_16bit_value(self.REG_EXT_V_COEFFICIENT)

    def get_ext_v_constant(self):
        return self.get_16bit_value(self.REG_EXT_V_CONSTANT)

    def get_restart_voltage(self):
        return self.get_16bit_value(self.REG_RESTART_VOLTAGE)

    def get_warn_voltage(self):
        return self.get_16bit_value(self.REG_WARN_VOLTAGE)

    def get_ups_shutdown_voltage(self):
        return self.get_16bit_value(self.REG_UPS_SHUTDOWN_VOLTAGE)

    def get_temperature(self):
        return self.get_16bit_value(self.REG_TEMPERATURE)

    def get_t_coefficient(self):
        return self.get_16bit_value(self.REG_T_COEFFICIENT)

    def get_t_constant(self):
        return self.get_16bit_value(self.REG_T_CONSTANT)

    def get_pulse_length(self):
        return self.get_16bit_value(self.REG_PULSE_LENGTH)

    def get_switch_recovery_delay(self):
        return self.get_16bit_value(self.REG_SW_RECOVERY_DELAY)

    def get_pulse_length_on(self):
        return self.get_16bit_value(self.REG_PULSE_LENGTH_ON)

    def get_pulse_length_off(self):
        return self.get_16bit_value(self.REG_PULSE_LENGTH_OFF)

    def get_16bit_value(self, register):
        for x in range(self._num_retries):
            bus = smbus.SMBus(self._bus_number)
            time.sleep(self._time_const)
            try:
                read = bus.read_i2c_block_data(self._address, register, 3)
                # we interpret every value as a 16-bit signed value
                val = int.from_bytes(read[0:2], byteorder='little', signed=True)
                bus.close()
                if read[2] == self.calcCRC(register, read, 2):
                    return val
                logging.debug("Couldn't read 16 bit register " + hex(register) + " correctly.")
            except Exception as e:
                logging.debug("Couldn't read 16 bit register " + hex(register) + ". Exception: " + str(e))
        logging.warning("Couldn't read 16 bit register after " + str(x) + " retries.")
        return 0xFFFFFFFF

    def get_timeout(self):
        return self.get_8bit_value(self.REG_TIMEOUT)

    def get_primed(self):
        return self.get_8bit_value(self.REG_PRIMED)

    def should_shutdown(self):
        return self.get_8bit_value(self.REG_SHOULD_SHUTDOWN)

    def get_force_shutdown(self):
        return self.get_8bit_value(self.REG_FORCE_SHUTDOWN)

    def get_led_off_mode(self):
        return self.get_8bit_value(self.REG_LED_OFF_MODE)

    def get_ups_configuration(self):
        return self.get_8bit_value(self.REG_UPS_CONFIG)

    def get_vext_off_is_shutdown(self):
        return self.get_8bit_value(self.REG_VEXT_OFF_IS_SHUTDOWN)

    def get_fuse_low(self):
        return self.get_8bit_value(self.REG_FUSE_LOW)

    def get_fuse_high(self):
        return self.get_8bit_value(self.REG_FUSE_HIGH)

    def get_fuse_extended(self):
        return self.get_8bit_value(self.REG_FUSE_EXTENDED)

    def get_internal_state(self):
        return self.get_8bit_value(self.REG_INTERNAL_STATE)

    def get_mcu_status_register(self):
        return self.get_8bit_value(self.REG_MCU_STATUS_REG)

    def get_8bit_value(self, register):
        for x in range(self._num_retries):
            bus = smbus.SMBus(self._bus_number)
            time.sleep(self._time_const)
            try:
                read = bus.read_i2c_block_data(self._address, register, 2)
                val = read[0]
                bus.close()
                if read[1] == self.calcCRC(register, read, 1):
                    return val
                logging.debug("Couldn't read register " + hex(register) + " correctly: " + hex(val))
            except Exception as e:
                logging.debug("Couldn't read 8 bit register " + hex(register) + ". Exception: " + str(e))
        logging.warning("Couldn't read 8 bit register after " + str(x) + " retries.")
        return 0xFFFF

    def get_version(self):
        for x in range(self._num_retries):
            bus = smbus.SMBus(self._bus_number)
            time.sleep(self._time_const)
            try:
                read = bus.read_i2c_block_data(self._address, self.REG_VERSION, 5)
                bus.close()
                if read[4] == self.calcCRC(self.REG_VERSION, read, 4):
                    major = read[2]
                    minor = read[1]
                    patch = read[0]
                    return (major, minor, patch)
                logging.debug("Couldn't read version information correctly.")
            except Exception as e:
                logging.debug("Couldn't read version information. Exception: " + str(e))
        logging.warning("Couldn't read version information after " + str(x) + " retries.")
        return (0xFFFF, 0xFFFF, 0xFFFF)

    def get_uptime(self):
        for x in range(self._num_retries):
            bus = smbus.SMBus(self._bus_number)
            time.sleep(self._time_const)
            try:
                read = bus.read_i2c_block_data(self._address, self.REG_UPTIME, 5)
                bus.close()
                if read[4] == self.calcCRC(self.REG_UPTIME, read, 4):
                    uptime = int.from_bytes(read[0:3], byteorder='little', signed=False)
                    return uptime
                logging.debug("Couldn't read uptime information correctly.")
            except Exception as e:
                logging.debug("Couldn't read uptime information. Exception: " + str(e))
        logging.warning("Couldn't read uptime information after " + str(x) + " retries.")
        return 0xFFFFFFFFFFFF

