# -*- coding: utf-8 -*-
__version__ = '0.2.1'

import threading
import os
import sys
import traceback
import pdb

import logging
log = logging.getLogger(__name__)
# Log errors only:
log.debug = lambda *x: None
logging.basicConfig(level=logging.ERROR)
# Log errors and debug messages:
# logging.basicConfig(level=logging.DEBUG)


def except_hook(exctype, value, tb):
    traceback.print_tb(tb)
    print(repr(value))
    pdb.post_mortem(tb)


class PinState(object):
    """An ultra simple pin-state object.

    Keeps track data related to each pin.

    Args:
        value: the file pointer to set/read value of pin.
        direction: the file pointer to set/read direction of the pin.
    """
    def __init__(self, value, direction):
        self.value = value
        self.direction = direction

sys.excepthook = except_hook

path = os.path
pjoin = os.path.join

gpio_root = '/sys/class/gpio'
gpiopath = lambda pin: os.path.join(gpio_root, 'gpio{0}'.format(pin))
_export_lock = threading.Lock()

_pyset = set

_open = dict()
FMODE = 'w+'

IN, OUT = 'in', 'out'
LOW, HIGH = 0, 1


def _write(f, v):
    log.debug("writing: %s: %s", f, v)
    f.write(v)
    f.flush()


def _read(f):
    log.debug("Reading: %s", f)
    f.seek(0)
    return f.read().strip()


def cleanup(pin=None, assert_exists=False):
    """Cleanup the pin by closing and unexporting it.

    Args:
        pin (int, optional): either the pin to clean up or None (default).
            If None, clean up all pins.
        assert_exists: if True, raise a ValueError if the pin was not
            setup. Otherwise, this function is a NOOP.
    """
    if pin is None:
        # Take a list of keys because we will be deleting from _open
        for pin in list(_open):
            cleanup(pin)
        return
    if not isinstance(pin, int):
        raise TypeError("pin must be an int, got: %s", pin)

    state = _open.get(pin)
    if state is None:
        if assert_exists:
            raise ValueError("pin %d was not setup", pin)
        return
    state.value.close()
    state.direction.close()
    if os.path.exists(gpiopath(pin)):
        log.debug("Unexporting pin %d", pin)
        with _export_lock:
            with open(pjoin(gpio_root, 'unexport'), 'w') as f:
                _write(f, str(pin))

    del _open[pin]


def setup(pin, mode, pullup=None, initial=False):
    '''Setup pin with mode IN or OUT.

    Args:
        pin (int):
        mode (str): use either gpio.OUT or gpio.IN
        pullup (optional): rpio compatibility. If anything but None, raises
            value Error
        initial (bool, optional): Initial pin value. Default is False
    '''
    if not isinstance(pin, int):
        raise TypeError("pin must be an int, got: %s", pin)
    if pin not in _open:
        ppath = gpiopath(pin)
        if not os.path.exists(ppath):
            log.debug("Creating Pin %d", pin)
            with _export_lock:
                with open(pjoin(gpio_root, 'export'), 'w') as f:
                    _write(f, str(pin))
        value = open(pjoin(ppath, 'value'), FMODE)
        direction = open(pjoin(ppath, 'direction'), FMODE)
        _open[pin] = PinState(value=value, direction=direction)

    if pullup is not None:
        raise ValueError("sysfs does not support pullups")

    if mode not in (IN, OUT):
        raise ValueError(mode)

    log.debug("Setup %d: %s", pin, mode)
    f = _open[pin].direction
    _write(f, mode)
    if mode == OUT:
        if initial:
            set(pin, HIGH)
        else:
            set(pin, LOW)


def mode(pin):
    '''get the pin mode

    Returns:
        str: "in" or "out"
    '''
    f = _open[pin].direction
    return _read(f)


def input(pin):
    '''read the pin value

    Returns:
        bool: 0 or 1
    '''
    f = _open[pin].value
    f.seek(0)
    out = (HIGH if f.read() == '1' else LOW)
    log.debug("Read %d: %d", pin, out)
    return out


def output(pin, value):
    '''set the pin value to 0 or 1'''
    log.debug("Write %d: %s", pin, value)
    f = _open[pin].value
    f.write('1' if value else '0')
    f.flush()


read = input


set = output


def setwarnings(value):
    '''exists for rpio compatibility'''
    pass


def setmode(value):
    '''exists for rpio compatibility'''
    pass


BCM = None  # rpio compatibility
