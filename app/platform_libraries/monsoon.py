# Edited by Kurt Jensen <Kurt.Jensen@wdc.com>
# Added support for OSX

# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Interface for a USB-connected Monsoon power meter.
http://msoon.com/LabEquipment/PowerMonitor/
Currently Unix-only. Relies on fcntl, /dev, and /tmp.
"""
import collections
import logging
import os
import select
import struct
import time
from sys import platform as _platform
import common_utils
#from telemetry.core import util
#util.AddDirToPythonPath(util.GetTelemetryDir(), 'third_party', 'pyserial')

import serial  # pylint: disable=F0401

class Monsoon(object):
  """Provides a simple class to use the power meter.
  mon = monsoon.Monsoon()
  mon.SetVoltage(3.7)
  mon.StartDataCollection()
  mydata = []
  while len(mydata) < 1000:
    mydata.extend(mon.CollectData())
  mon.StopDataCollection()
  """
  
  def __init__(self, device=None, serialno=None, wait=False):
    """Establish a connection to a Monsoon.
    By default, opens the first available port, waiting if none are ready.
    A particular port can be specified with 'device', or a particular Monsoon
    can be specified with 'serialno' (using the number printed on its back).
    With wait=False, IOError is thrown if a device is not immediately available.
    """
    self._coarse_ref = self._fine_ref = self._coarse_zero = self._fine_zero = 0
    self._coarse_scale = self._fine_scale = 0
    self._last_seq = 0
    self._voltage_multiplier = 125.0 / 10**6
    self.log = common_utils.create_logger('monsoon')
    if device:
      self.ser = serial.Serial(device, timeout=1)
      self.log.info('Opened device: ' + device)
      return
    if _platform.startswith('linux'):
      devicePath = 'ttyACM'
    elif _platform == 'darwin':
      devicePath = 'tty.usbmodem'
    print 'No power monitor device path given, searching..'
    while 1:  # Try all /dev/ttyACM* until we find one we can use.
      for dev in os.listdir('/dev'):
        if not dev.startswith(devicePath):
          continue
        tmpname = '/tmp/monsoon.%s.%s' % (os.uname()[0], dev)
        self._tempfile = open(tmpname, 'w')
        try:  # Use a lockfile to ensure exclusive access.
          # Put the import in here to avoid doing it on unsupported platforms.
          import fcntl
          fcntl.lockf(self._tempfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
          self.log.error('device %s is in use', dev)
          continue
        try:  # Try to open the device.
          self.ser = serial.Serial('/dev/%s' % dev, timeout=1)
          self.log.info('Opened device: /dev/' + dev)
          self.StopDataCollection()  # Just in case.
          self._FlushInput()  # Discard stale input.
          status = self.GetStatus()
        except IOError, e:
          self.log.error('error opening device %s: %s', dev, e)
          continue
        if not status:
          self.log.error('no response from device %s', dev)
        elif serialno and status['serialNumber'] != serialno:
          self.log.error('device %s is #%d', dev, status['serialNumber'])
        else:
          if status['hardwareRevision'] == 1:
            self._voltage_multiplier = 62.5 / 10**6
          else:
            self._voltage_multiplier = 125.0 / 10**6
          return
      self._tempfile = None
      if not wait:
        self.log.error('No device found')
        raise IOError('No device found')
      self.log.info('waiting for device...')
      time.sleep(1)
  def GetStatus(self):
    """Requests and waits for status.  Returns status dictionary."""
    # status packet format
    STATUS_FORMAT = '>BBBhhhHhhhHBBBxBbHBHHHHBbbHHBBBbbbbbbbbbBH'
    STATUS_FIELDS = [
        'packetType', 'firmwareVersion', 'protocolVersion',
        'mainFineCurrent', 'usbFineCurrent', 'auxFineCurrent', 'voltage1',
        'mainCoarseCurrent', 'usbCoarseCurrent', 'auxCoarseCurrent', 'voltage2',
        'outputVoltageSetting', 'temperature', 'status', 'leds',
        'mainFineResistor', 'serialNumber', 'sampleRate',
        'dacCalLow', 'dacCalHigh',
        'powerUpCurrentLimit', 'runTimeCurrentLimit', 'powerUpTime',
        'usbFineResistor', 'auxFineResistor',
        'initialUsbVoltage', 'initialAuxVoltage',
        'hardwareRevision', 'temperatureLimit', 'usbPassthroughMode',
        'mainCoarseResistor', 'usbCoarseResistor', 'auxCoarseResistor',
        'defMainFineResistor', 'defUsbFineResistor', 'defAuxFineResistor',
        'defMainCoarseResistor', 'defUsbCoarseResistor', 'defAuxCoarseResistor',
        'eventCode', 'eventData',
    ]
    self._SendStruct('BBB', 0x01, 0x00, 0x00)
    while 1:  # Keep reading, discarding non-status packets.
      data = self._ReadPacket()
      if not data:
        return None
      if len(data) != struct.calcsize(STATUS_FORMAT) or data[0] != '\x10':
        self.log.debug('wanted status, dropped type=0x%02x, len=%d',
                      ord(data[0]), len(data))
        continue
      status = dict(zip(STATUS_FIELDS, struct.unpack(STATUS_FORMAT, data)))
      assert status['packetType'] == 0x10
      for k in status.keys():
        if k.endswith('VoltageSetting'):
          status[k] = 2.0 + status[k] * 0.01
        elif k.endswith('FineCurrent'):
          pass  # Needs calibration data.
        elif k.endswith('CoarseCurrent'):
          pass  # Needs calibration data.
        elif k.startswith('voltage') or k.endswith('Voltage'):
          status[k] = status[k] * 0.000125
        elif k.endswith('Resistor'):
          status[k] = 0.05 + status[k] * 0.0001
          if k.startswith('aux') or k.startswith('defAux'):
            status[k] += 0.05
        elif k.endswith('CurrentLimit'):
          status[k] = 8 * (1023 - status[k]) / 1023.0
      return status
  def SetVoltage(self, v):
    """Set the output voltage, 0 to disable."""
    self.log.info('set output voltage: ' + str(v))
    if v == 0:
      self._SendStruct('BBB', 0x01, 0x01, 0x00)
    else:
      self._SendStruct('BBB', 0x01, 0x01, int((v - 2.0) * 100))
  def DisableVout(self):
    """Disable Vout"""
    self._SendStruct('BBB', 0x01, 0x01, 0x00)
  def SetMaxCurrent(self, i):
    """Set the max output current."""
    assert i >= 0 and i <= 8
    val = 1023 - int((i/8)*1023)
    self._SendStruct('BBB', 0x01, 0x0a, val & 0xff)
    self._SendStruct('BBB', 0x01, 0x0b, val >> 8)
  def SetUsbPassthrough(self, val):
    """Set the USB passthrough mode: 0 = off, 1 = on,  2 = auto."""
    self.log.info('set usb passthrough: ' + str(val))
    self._SendStruct('BBB', 0x01, 0x10, val)
  def StartDataCollection(self, hz=1):
    """Tell the device to start collecting and sending measurement data."""
    self._SendStruct('BBB', 0x01, 0x1b, 0x01)  # Mystery command.
    self._SendStruct('BBBBBBB', 0x02, 0xff, 0xff, 0xff, 0xff, 0x03, 0xe8)
  def StopDataCollection(self):
    """Tell the device to stop collecting measurement data."""
    self._SendStruct('BB', 0x03, 0x00)  # Stop.
  def CollectData(self):
    """Return some current samples.  Call StartDataCollection() first."""
    while 1:  # Loop until we get data or a timeout.
      data = self._ReadPacket()
      if not data:
        return None
      if len(data) < 4 + 8 + 1 or data[0] < '\x20' or data[0] > '\x2F':
        self.log.debug('wanted data, dropped type=0x%02x, len=%d',
            ord(data[0]), len(data))
        continue
      seq, packet_type, x, _ = struct.unpack('BBBB', data[:4])
      data = [struct.unpack(">hhhh", data[x:x+8])
              for x in range(4, len(data) - 8, 8)]
      if self._last_seq and seq & 0xF != (self._last_seq + 1) & 0xF:
        self.log.info('data sequence skipped, lost packet?')
      self._last_seq = seq
      if packet_type == 0:
        if not self._coarse_scale or not self._fine_scale:
          self.log.info('waiting for calibration, dropped data packet')
          continue
        out = []
        for main, usb, _, voltage in data:          
          main_voltage_v = self._voltage_multiplier * (voltage & ~3)
          sample = 0.0
          if main & 1:
            sample += ((main & ~1) - self._coarse_zero) * self._coarse_scale
          else:
            sample += (main - self._fine_zero) * self._fine_scale
          # if usb & 1:
          #   sample += ((usb & ~1) - self._coarse_zero) * self._coarse_scale
          # else:
          #   sample += (usb - self._fine_zero) * self._fine_scale
          out.append(sample)
        return out
      elif packet_type == 1:
        self._fine_zero = data[0][0]
        self._coarse_zero = data[1][0]
      elif packet_type == 2:
        self._fine_ref = data[0][0]
        self._coarse_ref = data[1][0]
      else:
        self.log.debug('discarding data packet type=0x%02x', packet_type)
        continue
      if self._coarse_ref != self._coarse_zero:
        self._coarse_scale = 2.88 / (self._coarse_ref - self._coarse_zero)
      if self._fine_ref != self._fine_zero:
        self._fine_scale = 0.0332 / (self._fine_ref - self._fine_zero)
  def _SendStruct(self, fmt, *args):
    """Pack a struct (without length or checksum) and send it."""
    data = struct.pack(fmt, *args)
    data_len = len(data) + 1
    checksum = (data_len + sum(struct.unpack('B' * len(data), data))) % 256
    out = struct.pack('B', data_len) + data + struct.pack('B', checksum)
    self.ser.write(out)
  def _ReadPacket(self):
    """Read a single data record as a string (without length or checksum)."""
    len_char = self.ser.read(1)
    if not len_char:
      self.log.error('timeout reading from serial port')
      return None
    data_len = struct.unpack('B', len_char)
    data_len = ord(len_char)
    if not data_len:
      return ''
    result = self.ser.read(data_len)
    if len(result) != data_len:
      return None
    body = result[:-1]
    checksum = (data_len + sum(struct.unpack('B' * len(body), body))) % 256
    if result[-1] != struct.pack('B', checksum):
      self.log.error('invalid checksum from serial port')
      return None
    return result[:-1]
  def _FlushInput(self):
    """Flush all read data until no more available."""
    self.ser.flush()
    flushed = 0
    while True:
      ready_r, _, ready_x = select.select([self.ser], [], [self.ser], 0)
      if len(ready_x) > 0:
        self.log.error('exception from serial port')
        return None
      elif len(ready_r) > 0:
        flushed += 1
        self.ser.read(1)  # This may cause underlying buffering.
        self.ser.flush()  # Flush the underlying buffer too.
      else:
        break
    if flushed > 0:
      self.log.debug('dropped >%d bytes', flushed)
