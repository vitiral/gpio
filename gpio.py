# -*- coding: utf-8 -*-
__version__ = '0.1.0'

import functools
import threading
import os
import sys
import traceback
import pdb

import logging
logging.basicConfig(level=logging.ERROR)
log = logging.getLogger(__name__)


def except_hook(exctype, value, tb):
    traceback.print_tb(tb)
    print(repr(value))
    pdb.post_mortem(tb)

sys.excepthook = except_hook

path = os.path
pjoin = os.path.join

gpio_root = '/sys/class/gpio'
gpiopath = lambda pin: os.path.join(gpio_root, 'gpio{}'.format(pin))
_export_lock = threading.Lock()

_pyset = set

_open = dict()
FMODE = 'w+'

IN, OUT = 'in', 'out'
LOW, HIGH = 'low', 'high'


def _write(f, v):
    log.debug("writing: {}: {}".format(f, v))
    f.write(str(v))


def _read(f):
    log.debug("Reading: {}".format(f))
    f.seek(0)
    return f.read()


def _verify(function):
    """decorator to ensure pin is properly set up"""
    # @functools.wraps
    def wrapped(pin, *args, **kwargs):
        pin = int(pin)
        if pin not in _open:
            ppath = gpiopath(pin)
            if not os.path.exists(ppath):
                log.debug("Creating Pin {}".format(pin))
                with _export_lock:
                    with open(pjoin(gpio_root, 'export'), 'w') as f:
                        _write(f, pin)
            _open[pin] = {
                'value': open(pjoin(ppath, 'value'), FMODE),
                'direction': open(pjoin(ppath, 'direction'), FMODE),
                'drive': open(pjoin(ppath, 'drive'), FMODE),
            }
        return function(pin, *args, **kwargs)
    return wrapped


@_verify
def setup(pin, mode, value=False):
    '''Setup pin with mode IN or OUT.

    Args:
        pin (int):
        mode (str): use either gpio.OUT or gpio.IN
        value (bool, optional): Initial pin value
    '''


    if mode not in {IN, OUT, LOW, HIGH}:
        raise ValueError(mode)
    log.debug("Setup {}: {}".format(pin, mode))
    f = _open[pin]['direction']
    if mode == 'OUT':
        if value:
            mode = LOW
        else:
            mode = HIGH
    _write(f, mode)


@_verify
def mode(pin):
    '''get the pin mode

    Returns:
        str: "in" or "out"
    '''
    f = _open[pin]['direction']
    return _read(f)


@_verify
def read(pin):
    '''read the pin value

    Returns:
        bool: 0 or 1
    '''
    f = _open[pin]['value']
    out = int(_read(f))
    log.debug("Read {}: {}".format(pin, out))
    return out


@_verify
def set(pin, value):
    '''set the pin value to 0 or 1'''
    value = int(bool(value))
    log.debug("Write {}: {}".format(pin, value))
    f = _open[pin]['value']
    _write(f, value)


@_verify
def input(pin):
    '''read the pin. Same as read'''
    return read(pin)


@_verify
def output(pin, value):
    '''set the pin. Same as set'''
    return set(pin)
