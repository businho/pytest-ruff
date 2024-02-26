import subprocess
import sys

import pytest

try:
    from pytest import Stash
except ImportError:
    from _pytest.store import Store as Stash
import pytest_ruff


def test_configure(mocker):
    config = mocker.Mock(
        cache={pytest_ruff.HISTKEY: mocker.sentinel.cache},
        option=mocker.Mock(ruff=True),
        stash=Stash(),
    )
    pytest_ruff.pytest_configure(config)
    assert config.stash[pytest_ruff._MTIMES_STASH_KEY] == mocker.sentinel.cache


def test_configure_without_ruff(mocker):
    config = mocker.Mock(
        option=mocker.Mock(ruff=False),
        stash=Stash(),
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


def test_pytest_ruff():
    out, err = subprocess.Popen(
        [sys.executable, "-m", "pytest", "--ruff", "tests/assets/check_broken.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).communicate()
    out_utf8 = out.decode("utf-8")
    assert "`os` imported but unused" in out_utf8


def test_pytest_ruff_format():
    out, err = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            "--ruff",
            "--ruff-format",
            "tests/assets/format_broken.py",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).communicate()
    assert err == b""
    assert "File would be reformatted" in out.decode("utf-8")


def test_pytest_ruff_noformat():
    out, err = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            "--ruff",
            "tests/assets/format_broken.py",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).communicate()
    assert err == b""
    assert "File would be reformatted" not in out.decode("utf-8")
