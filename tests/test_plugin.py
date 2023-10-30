import pytest

import pytest_ruff


def test_configure(mocker):
    config = mocker.Mock(
        cache={pytest_ruff.HISTKEY: mocker.sentinel.cache},
        option=mocker.Mock(ruff=True),
        stash=pytest.Stash(),
    )
    pytest_ruff.pytest_configure(config)
    assert config.stash[pytest_ruff._MTIMES_STASH_KEY] == mocker.sentinel.cache


def test_configure_without_ruff(mocker):
    config = mocker.Mock(
        option=mocker.Mock(ruff=False),
        stash=pytest.Stash(),
        # Mocking to `not hasattr(config, "cache")`.
        spec=["addinivalue_line", "option", "stash"],
    )
    pytest_ruff.pytest_configure(config)
    with pytest.raises(KeyError):
        config.stash[pytest_ruff._MTIMES_STASH_KEY]


def test_check_file():
    with pytest.raises(pytest_ruff.RuffError, match=r"`os` imported but unused"):
        pytest_ruff.check_file("tests/assets/check_broken.py")


def test_format_file():
    with pytest.raises(pytest_ruff.RuffError, match=r"File would be reformatted"):
        pytest_ruff.format_file("tests/assets/format_broken.py")
