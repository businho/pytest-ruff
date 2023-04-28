import pytest

import pytest_ruff


def test_configure(mocker):
    config = mocker.Mock(
        cache={pytest_ruff.HISTKEY: mocker.sentinel.cache},
        option=mocker.Mock(ruff=True),
    )
    pytest_ruff.pytest_configure(config)
    assert config._ruffmtimes == mocker.sentinel.cache


def test_configure_without_ruff(mocker):
    config = mocker.Mock(
        option=mocker.Mock(ruff=False),
    )
    pytest_ruff.pytest_configure(config)
    assert hasattr(config, "_ruffmtimes")


def test_check_file():
    with pytest.raises(pytest_ruff.RuffError, match=r"`os` imported but unused"):
        pytest_ruff.check_file("tests/assets/broken.py")
