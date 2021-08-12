# -*- coding: utf-8 -*-
__version__ = '1.0.0'

from threading import Lock
try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable
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

    Create a singleton instance of a GPIOPin(n) and track its state internally.

    Args:
        pin (int): the pin to configure
        mode (str): use either gpio.OUT or gpio.IN
        initial (bool, optional): Initial pin value. Default is LOW
        active_low (bool, optional): Set the pin to active low. Default
            is None which leaves things as configured in sysfs
    Raises:
        RuntimeError: if pin is already configured
    """
    def __init__(self, pin, direction=None, initial=LOW, active_low=None):
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

        # I hate manually calling .setup()!
        self.setup(direction, initial, active_low)

        # Add class to open pins
        _open_pins[self.pin] = self

    def setup(self, direction=None, initial=LOW, active_low=None):
        if direction is not None:
            self.set_direction(direction)

        if active_low is not None:
            self.set_active_low(active_low)

        if direction == OUT:
            self.write(initial)

    @staticmethod
    def configured(pin, assert_configured=True):
        """Get a configured GPIOPin instance where available.

        Args:
            pin (int): the pin to check
            assert_configured (bool): True to raise exception if pin unconfigured

        Returns:
            object: GPIOPin if configured, otherwise None

        Raises:
            RuntimeError: if pin is not configured
        """
        try:
            # Implicitly convert str to int, ie: "1" -> 1
            pin = int(pin)
        except (TypeError, ValueError):
            raise ValueError("pin must be an int")

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
            mode (str): use either gpio.OUT or gpio.IN
        '''
        if mode not in (IN, OUT, LOW, HIGH):
            raise ValueError("Unsupported pin mode {}".format(mode))

        with open(os.path.join(self.root, 'direction'), FMODE) as f:
            f.write(str(mode))
            f.flush()

    def set_active_low(self, active_low):
        '''Set the polarity of pin

        Args:
            mode (bool): True = active low / False = active high
        '''
        if not isinstance(active_low, bool):
            raise ValueError("active_low must be True or False")

        with open(os.path.join(self.root, 'active_low'), FMODE) as f:
            f.write('1' if active_low else '0')
            f.flush()

    def read(self):
        '''Read pin value

        Returns:
            int: gpio.HIGH or gpio.LOW
        '''
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
        '''Write pin value

        Args:
            value (bool): use either gpio.HIGH or gpio.LOW
        '''
        # write as bytes, about 3x faster than string IO
        self.value.write(b'1' if value else b'0')

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
    # Note: since "pin" is a kwarg in this function, it has not been renamed it to "pins" above
    pins = pin

    if pins is None:
        # Must be converted to a list since _open_pins is potentially modified below
        pins = list(_open_pins.keys())

    if not isinstance(pins, Iterable):
        pins = [pins]

    for pin in pins:
        state = GPIOPin.configured(pin, assert_exists)

        if state is not None:
            state.cleanup()  # GPIOPin will remove itself from _open_pins


# TODO RPi.GPIO uses "pull_up_down", does rpio differ?
def setup(pins, mode, pullup=None, initial=LOW, active_low=None):
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
    if not isinstance(pins, Iterable):
        pins = [pins]

    if pullup is not None:
        raise ValueError("sysfs does not support pull up/down")

    for pin in pins:
        state = GPIOPin.configured(pin, False)

        # Attempt to create the pin if not configured
        if state is None:
            state = GPIOPin(pin)  # GPIOPin will add itself to _open_pins

        state.setup(mode, initial, active_low)


def mode(pin):
    '''get the pin mode

    Returns:
        str: "in" or "out"
    '''
    return GPIOPin.configured(pin).get_direction()


def read(pin):
    '''read the pin value

    Returns:
        bool: either gpio.LOW or gpio.HIGH
    '''
    # These function calls lose us a little speed
    # but we're already > 2x faster so...
    # If you want things to be faster use a GPIOPin instance directly.
    return GPIOPin.configured(pin).read()


def write(pin, value):
    '''set the pin value to LOW or HIGH

    Args:
        pin (int): any configured pin
        value (bool): use gpio.LOW or gpio.HIGH
    '''
    # These function calls lose us a little speed
    # but we're already > 2x faster so...
    # If you want things to be faster use a GPIOPin instance directly.
    GPIOPin.configured(pin).write(value)


input = read
output = write
set = write  # TODO Set should be dropped, since it's a Python reserved word
