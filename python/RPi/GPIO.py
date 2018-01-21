# -*- coding: utf-8 -*-
# Copyright (c) 2018 Steven P. Goldsmith
# See LICENSE.md for details.

"""
RPi.GPIO implementation for ArmbianIO
-------------
The goal here is to eliminate one off RPi.GPIO implementations since ArmbianIO
supports many different SBCs. Here we are relying on AIOInit() to decect the
board. Anything not implemented will raise NotImplementedError.

Credit: rm-hull's OPi.GPIO is the basis for this code.
"""

import time
import warnings
from armbianio.armbianio import *

OUT = 0
IN = 1
HIGH = True
LOW = False

RISING = EDGE_RISING
FALLING = EDGE_FALLING
BOTH = EDGE_BOTH
NONE = EDGE_NONE

PUD_OFF = 0
PUD_DOWN = 1
PUD_UP = 2

BOARD = 10
BCM = 11

# Match original version number
VERSION = "0.6.3"

_gpio_warnings = True
_mode = None
_exports = {}
_events = {}


def _check_configured(channel, direction=None):
    configured = _exports.get(channel)
    if configured is None:
        raise RuntimeError("Channel {0} is not configured".format(channel))
    if direction is not None and direction != configured:
        descr = "input" if configured == IN else "output"
        raise RuntimeError("Channel {0} is configured for {1}".format(channel, descr))


def getmode():
    """Get mode.
    """
    return _mode


def setmode(mode):
    """Set mode. We ignore this since we are going to use actual pin numbers
    ArmbianIO style. Be aware that any programs that rely on hard coded pin
    numbers for the Raspberry Pi will not work without pin mapping.
    """
    global _mode
    # Detect SBC when _mode is None
    if _mode is None:
        rc = AIOInit()
        if rc != 1:
            raise RuntimeError("Board not detected")
    assert mode in [BCM, BOARD]
    _mode = mode


def setwarnings(enabled):
    """Set to true to show warnings or False to turn warning off.
    """    
    global _gpio_warnings
    _gpio_warnings = enabled

    
def setup(channel, direction, initial=None, pull_up_down=None):
    """Setup multiple pins as inputs or outputs at once. Pins are added to a
    list by direction (IN or OUT).
    """
    if _mode is None:
        raise RuntimeError("Mode has not been set")
    if pull_up_down is not None:
        if _gpio_warnings:
            warnings.warn("Pull up/down setting are not fully supported, continuing anyway. Use GPIO.setwarnings(False) to disable warnings.", stacklevel=2)
    if isinstance(channel, list):
        for ch in channel:
            setup(ch, direction, initial)
    else:
        if channel in _exports:
            raise RuntimeError("Channel {0} is already configured".format(channel))
        if direction == OUT and initial is not None:
            AIOAddGPIO(channel, initial)
        else:
            AIOAddGPIO(channel, direction)
    _exports[channel] = direction


def input(channel):
    """Read the value of a GPIO pin.
    """
    # Can read from a pin configured for output
    _check_configured(channel)
    return AIOReadGPIO(channel)


def output(channel, state):
    """Set the output state of a GPIO pin.
    """
    if isinstance(channel, list):
        for ch in channel:
            output(ch, state)
    else:
        _check_configured(channel, direction=OUT)
        AIOWriteGPIO(channel, state)


def wait_for_edge(channel, trigger, timeout=-1):
    """Wait for an edge. Pin should be type IN. Edge must be RISING, FALLING
    or BOTH.
    """
    _check_configured(channel, direction=IN)
    assert trigger in [RISING, FALLING, BOTH]
    # See if event already exists        
    if channel in _events:
        raise RuntimeError("Conflicting edge detection already enabled for this GPIO channel")
    AIOWriteGPIOEdge(channel, trigger)
    startTime = time.time()
    # Prime the pump
    originalValue = AIOReadGPIO(channel)
    value = originalValue
    valueExit = False
    timeoutExit = False
    while not valueExit and not timeoutExit:
        value = AIOReadGPIO(channel)
        if value != originalValue:
            if trigger == BOTH:
                valueExit = True
            else:
                valueExit = value == trigger
                originalValue = value
        if timeout > 0:
            timeoutExit = time.time() - startTime > timeout
        # Not sure what the best delay value would be to be CPU friendly
        # I should be able to use a generic callback to handle this instead
        time.sleep(0.1)
    AIOWriteGPIOEdge(channel, NONE)
    return channel


def add_event_detect(channel, trigger, callback=None, bouncetime=None):
    """Enable edge detection events for a particular GPIO channel.  Pin should
    be type IN.  Edge must be RISING, FALLING or BOTH.
    """
    _check_configured(channel, direction=IN)
    assert trigger in [RISING, FALLING, BOTH]
    if bouncetime is not None:
        if _gpio_warnings:
            warnings.warn("bouncetime is not fully supported, continuing anyway. Use GPIO.setwarnings(False) to disable warnings.", stacklevel=2)
    # See if event already exists        
    if channel in _events:
        raise RuntimeError("Conflicting edge detection already enabled for this GPIO channel")
    else:
        _events[channel] = trigger
    # If callback exists then add it via ArmbianIO    
    if callback is not None:
        AIOAddGPIOCallback(channel, trigger, AIOCALLBACK(callback))            


def remove_event_detect(channel):
    """Remove edge detection for a particular GPIO channel. Pin should be type
    IN.
    """
    _check_configured(channel, direction=IN)
    # See if event already exists        
    if channel in _events:
        # Remove callback
        AIORemoveGPIOCallback(channel)
        del _events[channel]
    else:
        raise RuntimeError("No event exists for this GPIO channel")


def add_event_callback(channel, callback, bouncetime=None):
    """Enable edge detection events for a particular GPIO channel. Pin should
    be type IN.  Edge must be RISING, FALLING or BOTH.
    """
    _check_configured(channel, direction=IN)
    if bouncetime is not None:
        if _gpio_warnings:
            warnings.warn("bouncetime is not fully supported, continuing anyway. Use GPIO.setwarnings(False) to disable warnings.", stacklevel=2)
    # See if event exists        
    if channel in _events:
        AIOAddGPIOCallback(channel, _events[channel], AIOCALLBACK(callback))            
    else:
        raise RuntimeError("No event exists for this GPIO channel")


def event_detected(channel):
    """Returns True if an edge has occured on a given GPIO.  You need to enable
    edge detection using add_event_detect() first. Pin should be type IN.
    """
    _check_configured(channel, direction=IN)
    raise NotImplementedError


def cleanup(channel=None):
    """At the end any program, it is good practice to clean up any resources
    you might have used.
    """
    if channel is None:
        cleanup(list(_exports.keys()))
        setwarnings(True)
        global _mode
        _mode = None
        AIOShutdown()
    elif isinstance(channel, list):
        for ch in channel:
            cleanup(ch)
    else:
        _check_configured(channel)
        # Clean up event if it exists
        if _events.get(channel) is not None:
            AIORemoveGPIOCallback(channel)
            del _events[channel]
        # Remove from ArmbianIO
        AIORemoveGPIO(channel)
        del _exports[channel]
