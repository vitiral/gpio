import mock
import pytest


def test_setup_rpio(gpio, patch_open):
    gpio.setup(10, gpio.OUT)

    patch_open.assert_any_call('/sys/class/gpio/export', 'w+')
    patch_open().__enter__().write.assert_any_call('10')

    patch_open.assert_any_call('/sys/class/gpio/gpio10/value', 'wb+', buffering=0)
    patch_open.assert_any_call('/sys/class/gpio/gpio10/direction', 'w+')
    patch_open().__enter__().write.assert_any_call(str(gpio.OUT))


def test_setup_class(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT)

    patch_open.assert_any_call('/sys/class/gpio/export', 'w+')
    patch_open().__enter__().write.assert_any_call('10')

    patch_open.assert_any_call('/sys/class/gpio/gpio10/value', 'wb+', buffering=0)
    patch_open.assert_any_call('/sys/class/gpio/gpio10/direction', 'w+')
    patch_open().__enter__().write.assert_any_call(str(gpio.OUT))


def test_setup_rpio_list(gpio, patch_open):
    gpio.setup([9, 10, 11], gpio.OUT)


def test_setup_rpio_tuple(gpio, patch_open):
    gpio.setup((9, 10, 11), gpio.OUT)


def test_setup_rpio_generator(gpio, patch_open):
    pins = {9: 9, 10: 10, 11: 11}
    gpio.setup(pins.keys(), gpio.OUT)


def test_setup_with_pull(gpio, patch_open):
    with pytest.raises(ValueError):
        gpio.setup(10, gpio.OUT, pullup=1)


def test_class_already_setup(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT)

    with pytest.raises(RuntimeError):
        gpio.GPIOPin(10, gpio.OUT)


def test_rpio_already_setup(gpio, patch_open):
    gpio.setup(10, gpio.OUT)
    # Running gpio.setup again should not raise an error
    # in RPi.GPIO this may raise a warning
    gpio.setup(10, gpio.OUT)

    with pytest.raises(RuntimeError):
        gpio.GPIOPin(10, gpio.OUT)


def test_rpio_cleanup_all(gpio, patch_open):
    gpio.setup(10, gpio.OUT)
    gpio.setup(11, gpio.OUT)
    gpio.cleanup()
    assert gpio.GPIOPin.configured(10, False) is None
    assert gpio.GPIOPin.configured(11, False) is None


def test_rpio_cleanup_list(gpio, patch_open):
    gpio.setup(10, gpio.OUT)
    gpio.setup(11, gpio.OUT)
    gpio.setup(12, gpio.OUT)
    gpio.cleanup([10, 11])
    assert gpio.GPIOPin.configured(10, False) is None
    assert gpio.GPIOPin.configured(11, False) is None
    assert gpio.GPIOPin.configured(12, False) is not None


def test_rpio_invalid_cleanup(gpio, patch_open):
    with pytest.raises(RuntimeError):
        gpio.cleanup(10, True)


def test_rpio_invalid_cleanup_list(gpio, patch_open):
    gpio.setup(10, gpio.OUT)
    with pytest.raises(RuntimeError):
        gpio.cleanup([10, 11], True)


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


def test_setup_pin_is_not_int(gpio, patch_open):
    with pytest.raises(ValueError):
        gpio.setup(None, gpio.OUT)

    with pytest.raises(ValueError):
        pin = gpio.GPIOPin(None, gpio.OUT)


def test_cleanup_class_unregisters_self(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT)
    patch_open.reset_mock()
    pin.cleanup()
    assert gpio.GPIOPin.configured(10, False) == None


def test_set_direction(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT)
    patch_open.reset_mock()
    pin.set_direction(gpio.OUT)
    pin.set_direction(gpio.IN)
    patch_open().__enter__().write.assert_any_call(str(gpio.OUT))
    patch_open().__enter__().write.assert_any_call(str(gpio.IN))


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

    with pytest.raises(ValueError):
        pin.set_active_low(None)


def test_setup_active_low(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT, active_low=False)
    patch_open.assert_has_calls((
        mock.call().__enter__().write('0'),
        mock.call().__enter__().flush(),
    ))
    pin.cleanup()

    patch_open.reset_mock()
    pin = gpio.GPIOPin(10, gpio.OUT, active_low=True)
    patch_open.assert_has_calls((
        mock.call().__enter__().write('1'),
        mock.call().__enter__().flush(),
    ))


def test_get_direction(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.IN)

    patch_open().__enter__().read.return_value = 'in\n'
    assert pin.get_direction() == gpio.IN
    assert gpio.mode(10) == gpio.IN

    patch_open().__enter__().read.return_value = 'out\n'
    assert pin.get_direction() == gpio.OUT
    assert gpio.mode(10) == gpio.OUT


def test_set_direction(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.IN)

    for direction in (gpio.IN, gpio.OUT):
        patch_open.reset_mock()
        pin.set_direction(direction)
        patch_open.assert_has_calls((
            mock.call().__enter__().write(direction),
        ))

    with pytest.raises(ValueError):
        pin.set_direction(None)


def test_unconfigured_runtimeerror(gpio, patch_open):
    with pytest.raises(RuntimeError):
        pin = gpio.GPIOPin.configured(10)


def test_write(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.OUT)

    patch_open.reset_mock()
    pin.write(False)
    patch_open.assert_has_calls((
        mock.call().write(b'0'),
    ))

    patch_open.reset_mock()
    gpio.write(10, False)
    patch_open.assert_has_calls((
        mock.call().write(b'0'),
    ))

    patch_open.reset_mock()
    pin.write(True)
    patch_open.assert_has_calls((
        mock.call().write(b'1'),
    ))

    patch_open.reset_mock()
    gpio.write(10, True)
    patch_open.assert_has_calls((
        mock.call().write(b'1'),
    ))


def test_read(gpio, patch_open):
    pin = gpio.GPIOPin(10, gpio.IN)

    patch_open().read.return_value = b'1\n'
    assert pin.read() == gpio.HIGH
    assert gpio.read(10) == gpio.HIGH

    patch_open().read.return_value = b'0\n'
    assert pin.read() == gpio.LOW
    assert gpio.read(10) == gpio.LOW
