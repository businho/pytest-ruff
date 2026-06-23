import os
import subprocess
import sys
import types

import pytest_ruff
from pytest_ruff._pytest_compat import Stash, get_stash


def _session(item_cls, path):
    # Build a minimal session holding a single ruff item, enough for the batch
    # functions, which only read `session.items` and each item's `fspath`.
    item = item_cls.__new__(item_cls)
    item.fspath = path
    return types.SimpleNamespace(items=[item])


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


def test_batch_check_results():
    path = "tests/assets/check_broken.py"
    session = _session(pytest_ruff.RuffItem, path)
    failures, error = pytest_ruff.batch_check_results(session, None)
    assert error is None
    assert "`os` imported but unused" in failures[os.path.realpath(path)]


def test_batch_format_results():
    path = "tests/assets/format_broken.py"
    session = _session(pytest_ruff.RuffFormatItem, path)
    failing, error = pytest_ruff.batch_format_results(session, None)
    assert error is None
    assert os.path.realpath(path) in failing


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
            "tests/assets/config_broken/empty.py",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = process.communicate()
    assert err.decode() == ""
    assert "unknown field `broken`" in out.decode()


def test_custom_ruff_config():
    # fails with default
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            "--ruff",
            "--ruff-format",
            "tests/assets/long_line.py",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = process.communicate()
    assert err.decode() == ""
    assert "File would be reformatted" in out.decode("utf-8")

    # succeeds with custom
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            "--ruff",
            "--ruff-format",
            "--ruff-config=tests/assets/long_line_config/ruff.toml",
            "tests/assets/long_line.py",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = process.communicate()
    assert err.decode() == ""
    assert "tests/assets/long_line.py ." in out.decode()


def test_without_pytest_cache():
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "pytest",
            "--ruff",
            "-pno:cacheprovider",
            "tests/assets/ok.py",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = process.communicate()
    assert err.decode() == ""
    assert "tests/assets/ok.py ." in out.decode()
