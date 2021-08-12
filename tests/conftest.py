import sys

import mock
import pytest


@pytest.fixture
def patch_open():
    mopen = mock.MagicMock()
    bopen = "__builtin__.open" if sys.version_info.major < 3 else "builtins.open"
    with mock.patch(bopen, mopen, create=True):
        yield mopen


@pytest.fixture
def gpio():
    import gpio
    yield gpio
    del sys.modules['gpio']