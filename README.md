# Linux [sysfs](https://www.kernel.org/doc/Documentation/gpio/sysfs.txt) gpio access

This library provides gpio access via the standard linux [sysfs interface](https://www.kernel.org/doc/Documentation/gpio/sysfs.txt)

It is intended to mimic [RPIO](http://pythonhosted.org/RPIO/) as much as possible 
for all features, while also supporting additional (and better named) functionality 
to the same methods.

## Supported Features

- get pin values with `read(pin)` or `input(pin)`
- set pin values with `write(pin, value)`, `set(pin, value)` or `output(pin, value)`
- get the pin mode with `mode(pin)`
- set the pin mode with `setup(pin, mode)`
    - `mode` can currently equal `gpio.IN` or `gpio.OUT`
- create a `GPIOPin` class directly to `write` and `read` a pin

## Examples

### RPi.GPIO Drop-in

Good for up to 130KHz pin toggle on a Pi 400.

```python
import time

import gpio as GPIO

GPIO.setup(14, GPIO.OUT)

while True:
    GPIO.output(14, GPIO.HIGH)
    time.sleep(1.0)
    GPIO.output(14, GPIO.LOW)
    time.sleep(1.0)
```

### Use GPIOPin directly

Good for up to 160KHz pin toggle on a Pi 400.

This gives you a class instance you can manipulate directly, eliminating the lookup:

```python
import gpio

pin = gpio.GPIOPin(14, gpio.OUT)

while True:
    pin.write(14, GPIO.HIGH)
    time.sleep(1.0)
    pin.write(14, GPIO.LOW)
    time.sleep(1.0)
```
