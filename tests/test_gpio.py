import mock
import pytest


def test_setup_rpio(gpio, patch_open):
    gpio.setup(10, gpio.OUT)

    patch_open.assert_any_call('/sys/class/gpio/export', 'w+')
    patch_open().__enter__().write.assert_any_call('10')

    patch_open.assert_any_call('/sys/class/gpio/gpio10/value', 'wb+', buffering=0)
    patch_open.assert_any_call('/sys/class/gpio/gpio10/direction', 'w+')
    patch_open().__enter__().write.assert_any_call('out')


def test_setup_class(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT)

    patch_open.assert_any_call('/sys/class/gpio/export', 'w+')
    patch_open().__enter__().write.assert_any_call('10')

    patch_open.assert_any_call('/sys/class/gpio/gpio10/value', 'wb+', buffering=0)
    patch_open.assert_any_call('/sys/class/gpio/gpio10/direction', 'w+')
    patch_open().__enter__().write.assert_any_call('out')


def test_class_already_setup(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT)

    with pytest.raises(RuntimeError):
        gpio.GPIOPin(10, gpio.OUT)


def test_rpio_already_setup(gpio, patch_open):
    gpio.setup(10, gpio.OUT)

    with pytest.raises(RuntimeError):
        gpio.GPIOPin(10, gpio.OUT)


def test_setup_class_registers_self(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT)
    assert gpio.GPIOPin.configured(10) == pin


def test_cleanup_class_unexports_pin(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT)
    patch_open.reset_mock()
    pin.root = "/dev/null"  # Pass os.path.exists check
    pin.cleanup()

    patch_open.assert_any_call('/sys/class/gpio/unexport', 'w+')
    patch_open().__enter__().write.assert_any_call('10')


def test_cleanup_class_unregisters_self(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT)
    patch_open.reset_mock()
    pin.cleanup()
    assert gpio.GPIOPin.configured(10) == None


def test_set_direction(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT)
    patch_open.reset_mock()
    pin.set_direction(gpio.OUT)
    pin.set_direction(gpio.IN)
    patch_open().__enter__().write.assert_any_call('out')
    patch_open().__enter__().write.assert_any_call('in')


def test_set_active_low(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT)

    patch_open.reset_mock()
    pin.set_active_low(False)
    patch_open.assert_has_calls((
        mock.call().__enter__().write('0'),
        mock.call().__enter__().flush(),
    ))

    patch_open.reset_mock()
    pin.set_active_low(True)
    patch_open.assert_has_calls((
        mock.call().__enter__().write('1'),
        mock.call().__enter__().flush(),
    ))


def test_write(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT)

    patch_open.reset_mock()
    pin.write(False)
    patch_open.assert_has_calls((
        mock.call().write(b'0'),
    ))

    patch_open.reset_mock()
    pin.write(True)
    patch_open.assert_has_calls((
        mock.call().write(b'1'),
    ))


def test_read(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.IN)

    patch_open().read.return_value = b'1\n'
    value = pin.read()
    assert value == gpio.HIGH

    patch_open().read.return_value = b'0\n'
    value = pin.read()
    assert value == gpio.LOW
