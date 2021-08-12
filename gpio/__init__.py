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
BCM = None  # Exists for RPi.GPIO compatibility


class GPIOPin(object):
    """Handle pin state.

    Keeps track of file nodes and functions related to a pin.

    Args:
        pin (int): the GPIO pin to set up
    """
    def __init__(self, pin, mode=None, initial=LOW, active_low=None):
        existing = _open_pins.get(pin)
        if existing:
            existing.cleanup()
            del existing

        self.pin = str(pin)
        self.value = None

        self.root = os.path.join(GPIO_ROOT, 'gpio{0}'.format(pin))

        if not os.path.exists(self.root):
            with _export_lock:
                with open(GPIO_EXPORT, 'w') as f:
                    f.write(self.pin)
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
        _open_pins[pin] = self

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
            f.write(str(active_low))
            f.flush()

    def read(self):
        self.value.seek(0)
        # Subtracting 48 converts an ASCII "0" or "1" to an int
        # ord("0") == 48
        return self.value.read()[0] - 48

    def write(self, value):
        # Convert any truthy value explicitly to HIGH and vice versa
        # this is about 3x faster than int(bool(value))
        value = HIGH if value else LOW
        # write as bytes, about 3x faster than string IO
        self.value.write(b'1' if value else b'0')
        # state.value.write(str(value).encode())  # Slow alternate for Python 2

    def cleanup(self):
        # Note: I have not put "cleanup" into the __del__ method since it's not
        # always desireable to unexport pins at program exit.
        self.value.close()

        if os.path.exists(self.root):
            with _export_lock:
                with open(GPIO_UNEXPORT, 'w') as f:
                    f.write(self.pin)
                    f.flush()


def cleanup(pin=None, assert_exists=False):
    """Cleanup the pin by closing and unexporting it.

    Args:
        pin (int, optional): either the pin to clean up or None (default).
            If None, clean up all pins.
        assert_exists: if True, raise a ValueError if the pin was not
            setup. Otherwise, this function is a NOOP.
    """
    if type(pin) in (list, tuple):
        for p in pin:
            cleanup(p, assert_exists=assert_exists)
        return

    if pin is None:
        # Iterate through the open pins, "cleanup" and "del" them.
        for pin in list(_open_pins.keys()):
            _open_pins[pin].cleanup()
            del _open_pins[pin]
        return

    try:
        pin = int(pin)
    except TypeError:
        # This is a white lie, supporting "1" etc is a silent back-compat fix
        raise TypeError("pin must be an int")

    if pin not in _open_pins:
        if assert_exists:
            raise ValueError("pin {} was not set up".format(pin))
        return

    _open_pins[pin].cleanup()
    del _open_pins[pin]


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

    try:
        pin = int(pin)
    except TypeError:
        # This is a white lie, supporting "1" etc is a silent back-compat fix
        raise TypeError("pin must be an int")

    state = _open_pins.get(pin)

    # Attempt to create the pin if not set up
    if state is None:
        # GPIOPin will add itself to _open_pins
        state = GPIOPin(pin)

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

    try:
        pin = int(pin)
    except TypeError:
        # This is a white lie, supporting "1" etc is a silent back-compat fix
        raise TypeError("pin must be an int")

    state = _open_pins.get(pin)
    if not state:
        raise ValueError("pin {} is not set up".format(pin))

    return state.get_direction()


def read(pin):
    '''read the pin value

    Returns:
        bool: 0 or 1
    '''

    # This costs us some read speed performance.
    # If you want things to be faster use a GPIOPin instance directly.
    try:
        pin = int(pin)
    except TypeError:
        # This is a white lie, supporting "1" etc is a silent back-compat fix
        raise TypeError("pin must be an int")

    state = _open_pins.get(pin)
    if not state:
        raise ValueError("pin {} is not set up".format(pin))

    # These function calls lose us a little speed
    # but we're already > 2x faster so...
    # If you want things to be faster use a GPIOPin instance directly.
    return state.read()


def write(pin, value):
    '''set the pin value to 0 or 1'''

    # This costs us about 30KHz but preserves API support for str GPIO numbers
    # If you want things to be faster use a GPIOPin instance directly.
    try:
        pin = int(pin)
    except TypeError:
        # This is a white lie, supporting "1" etc is a silent back-compat fix
        raise TypeError("pin must be an int")

    state = _open_pins.get(pin)
    if not state:
        raise ValueError("pin {} is not set up".format(pin))

    # These function calls lose us a little speed
    # but we're already > 2x faster so...
    # If you want things to be faster use a GPIOPin instance directly.
    state.write(value)


def setwarnings(value):
    '''exists for RPi.GPIO compatibility'''
    pass


def setmode(value):
    '''exists for RPi.GPIO compatibility'''
    pass


input = read
output = write
set = write  # TODO Set should be dropped, since it's a Python reserved word
