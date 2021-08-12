# -*- coding: utf-8 -*-
__version__ = '1.0.0'

from threading import Lock
import os


_export_lock = Lock()
_open_pins = {}


GPIO_ROOT = '/sys/class/gpio'
GPIO_EXPORT = os.path.join(GPIO_ROOT, 'export')
GPIO_UNEXPORT = os.path.join(GPIO_ROOT, 'unexport')
FMODE = 'w+'  # w+ overwrites and truncates existing files
IN, OUT = 'in', 'out'
LOW, HIGH = 0, 1


class GPIOPin(object):
    """Handle pin state.

    Keeps track of file nodes and functions related to a pin.

    Args:
        pin (int): the GPIO pin to configure
    """
    def __init__(self, pin, mode=None, initial=LOW, active_low=None):
        #  .configured() will raise a TypeError if "pin" is not convertable to int
        if GPIOPin.configured(pin, False) is not None:
            raise RuntimeError("pin {} is already configured".format(pin))

        self.value = None
        self.pin = int(pin)
        self.root = os.path.join(GPIO_ROOT, 'gpio{0}'.format(self.pin))

        if not os.path.exists(self.root):
            with _export_lock:
                with open(GPIO_EXPORT, FMODE) as f:
                    f.write(str(self.pin))
                    f.flush()

        # Using unbuffered binary IO is ~ 3x faster than text
        self.value = open(os.path.join(self.root, 'value'), 'wb+', buffering=0)

        if mode is not None:
            self.set_direction(mode)

        if active_low is not None:
            self.set_active_low(active_low)

        if mode == OUT:
            self.write(initial)

        # Add class to open pins
        _open_pins[self.pin] = self

    @staticmethod
    def configured(pin, assert_configured=True):
        """Get a configured GPIOPin instance where available.

        Args:
            pin (int): the GPIO pin to configured
            assert_configured (bool): True to raise exception if pin unconfigured

        Returns:
            object: GPIOPin if configured, otherwise None

        Raises:
            RuntimeError: if pin is not configured
        """
        try:
            # Implicitly convert str to int, ie: "1" -> 1
            pin = int(pin)
        except TypeError:
            raise TypeError("pin must be an int")

        if pin not in _open_pins and assert_configured:
            raise RuntimeError("pin {} is not configured".format(pin))

        return _open_pins.get(pin)

    def get_direction(self):
        '''Get the direction of pin

        Returns:
            str: "in" or "out"
        '''
        with open(os.path.join(self.root, 'direction'), FMODE) as f:
            return f.read().strip()

    def set_direction(self, mode):
        '''Set the direction of pin

        Args:
            mode (str): "in" or "out"
        '''
        if mode not in (IN, OUT, LOW, HIGH):
            raise ValueError("Unsupported pin mode {}".format(mode))

        with open(os.path.join(self.root, 'direction'), FMODE) as f:
            f.write(str(mode))
            f.flush()

    def set_active_low(self, active_low):
        '''Set the direction of pin

        Args:
            mode (bool): True/False
        '''
        if not isinstance(active_low, bool):
            raise ValueError("active_low must be True or False")

        with open(os.path.join(self.root, 'active_low'), FMODE) as f:
            f.write('1' if active_low else '0')
            f.flush()

    def read(self):
        '''Read pin value'''
        self.value.seek(0)
        value = self.value.read()
        try:
            # Python > 3 - bytes
            # Subtracting 48 converts an ASCII "0" or "1" to an int
            # ord("0") == 48
            return value[0] - 48
        except TypeError:
            # Python 2.x - str
            return int(value)

    def write(self, value):
        '''Write pin value'''
        # Convert any truthy value explicitly to HIGH and vice versa
        # this is about 3x faster than int(bool(value))
        value = HIGH if value else LOW
        # write as bytes, about 3x faster than string IO
        self.value.write(b'1' if value else b'0')
        # state.value.write(str(value).encode())  # Slow alternate for Python 2

    def cleanup(self):
        '''Clean up pin

        Unexports the pin and deletes it from the open list.

        '''
        # Note: I have not put "cleanup" into the __del__ method since it's not
        # always desireable to unexport pins at program exit.
        # Additionally "open" can be deleted *before* the GPIOPin instance.
        self.value.close()

        if os.path.exists(self.root):
            with _export_lock:
                with open(GPIO_UNEXPORT, FMODE) as f:
                    f.write(str(self.pin))
                    f.flush()

        del _open_pins[self.pin]


def cleanup(pin=None, assert_exists=False):
    """Cleanup the pin by closing and unexporting it.

    Args:
        pin (int, optional): either the pin to clean up or None (default).
            If None, clean up all pins.
        assert_exists: if True, raise a ValueError if the pin was not
            setup. Otherwise, this function is a NOOP.
    """
    if pin is None:
        pin = list(_open_pins.keys())

    if type(pin) not in (list, tuple):
        pin = [pin]

    for p in pin:
        state = GPIOPin.configured(p, assert_exists)

        if state is not None:
            state.cleanup()


def setup(pin, mode, pullup=None, initial=LOW, active_low=None):
    '''Setup pin with mode IN or OUT.

    Args:
        pin (int):
        mode (str): use either gpio.OUT or gpio.IN
        pullup (None): rpio compatibility. If anything but None, raises
            value Error
        initial (bool, optional): Initial pin value. Default is LOW
        active_low (bool, optional): Set the pin to active low. Default
            is None which leaves things as configured in sysfs
    '''
    if type(pin) in (list, tuple):
        for p in pin:
            setup(p, mode, pullup=pullup, initial=initial, active_low=active_low)
        return

    state = GPIOPin.configured(pin, False)

    # Attempt to create the pin if not configured
    if state is None:
        state = GPIOPin(pin)  # GPIOPin will add itself to _open_pins

    if pullup is not None:
        raise ValueError("sysfs does not support pull up/down")

    state.set_direction(mode)

    if active_low is not None:
        state.set_active_low(active_low)

    # RPi.GPIO accepts an "initial" pin state value of HIGH or LOW
    # and sets the pin to that value during setup()
    if mode == OUT:
        set(pin, initial)


def mode(pin):
    '''get the pin mode

    Returns:
        str: "in" or "out"
    '''
    return GPIOPin.configured(pin).get_direction()


def read(pin):
    '''read the pin value

    Returns:
        bool: LOW or HIGH
    '''
    # These function calls lose us a little speed
    # but we're already > 2x faster so...
    # If you want things to be faster use a GPIOPin instance directly.
    return GPIOPin.configured(pin).read()


def write(pin, value):
    '''set the pin value to LOW or HIGH

    Args:
        pin (int): any configured pin
        value (bool): LOW or HIGH
    '''
    # These function calls lose us a little speed
    # but we're already > 2x faster so...
    # If you want things to be faster use a GPIOPin instance directly.
    GPIOPin.configured(pin).write(value)


input = read
output = write
set = write  # TODO Set should be dropped, since it's a Python reserved word
