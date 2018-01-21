# -*- coding: utf-8 -*-
# Copyright (c) 2018 Steven P. Goldsmith
# See LICENSE.md for details.

"""
Simple callback using built in button
-------------
Should work on any board with a button built in.
"""

import time
from armbianio.armbianio import *


# Simple callback displays pin and value
def buttonCallback(iPin):
    print "Button state: pin = %d, value = %d" % (iPin, AIOReadGPIO(0))


# Detect SBC
rc = AIOInit()
if rc == 1:
    print "Running on a %s" % AIOGetBoardName()
    if AIOHasButton():
        AIOAddGPIO(0, GPIO_IN)
        # Button callback
        AIOAddGPIOCallback(0, EDGE_BOTH, AIOCALLBACK(buttonCallback))
        print "Press/release button a few times\n"
        time.sleep(10)
        # Remove callback
        AIORemoveGPIOCallback(0)
        # Remove pin (actually you cannot remove the button)
        AIORemoveGPIO(0)
    else:
        print "%s does not have a button" % AIOGetBoardName()
    AIOShutdown()
else:
    print "AIOInit error"
