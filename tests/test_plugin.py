import subprocess
import sys

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
        pytest_ruff.check_file(None, path="tests/assets/check_broken.py")


def test_format_file():
    with pytest.raises(pytest_ruff.RuffError, match=r"File would be reformatted"):
        pytest_ruff.format_file(None, path="tests/assets/format_broken.py")


def test_pytest_ruff():
    out, err = subprocess.Popen(
        [sys.executable, "-m", "pytest", "--ruff", "tests/assets/check_broken.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).communicate()
    out_utf8 = out.decode("utf-8")
    assert "`os` imported but unused" in out_utf8
    assert "force-exclude:1:1: E902 No such file or directory (os error 2)" not in out_utf8


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
    assert "File would be reformatted" not in out.decode("utf-8")
