# Linux [sysfs](https://www.kernel.org/doc/Documentation/gpio/sysfs.txt) gpio access

This library provides gpio access via the standard linux [sysfs interface](https://www.kernel.org/doc/Documentation/gpio/sysfs.txt)

It is intended to mimick [RPIO](http://pythonhosted.org/RPIO/) as much as possible 
for all features, while also supporting additional (and better named) functionality 
to the same methods.


## Supported Features
- get pin values with `read(pin)` or `input(pin)`
- set pin values with `set(pin, value)` or `output(pin, value)`
- get the pin mode with `mode(pin)`
- set the pin mode with `setup(pin, mode)`
    - `mode` can currently equal `gpio.IN` or `gpio.OUT`
