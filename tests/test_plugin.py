import subprocess
import sys

import pytest

import pytest_ruff
from pytest_ruff._pytest_compat import Stash, get_stash


def test_configure(mocker):
    config = mocker.Mock(
        cache={pytest_ruff.HISTKEY: mocker.sentinel.cache},
        option=mocker.Mock(ruff=True),
        stash=Stash(),
    )
    pytest_ruff.pytest_configure(config)
    assert get_stash(config) == mocker.sentinel.cache


def test_configure_without_ruff(mocker):
    config = mocker.Mock(
        option=mocker.Mock(ruff=False),
        # Mocking to `not hasattr(config, "cache")`.
        spec=["addinivalue_line", "option", "stash"],
    )
    set_stash_mock = mocker.patch("pytest_ruff.set_stash", spec=True)
    pytest_ruff.pytest_configure(config)
    set_stash_mock.assert_not_called()


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
    assert err.decode() == ""
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
    assert err.decode() == ""
    assert "File would be reformatted" not in out.decode("utf-8")


def test_broken_ruff_config():
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            "--ruff",
            "tests/assets/broken_config/empty.py",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = process.communicate()
    assert err.decode() == ""
    assert "unknown field `broken`" in out.decode()
