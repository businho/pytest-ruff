import json
import os
from subprocess import PIPE, Popen

import pytest
from ruff.__main__ import find_ruff_bin

from pytest_ruff._pytest_compat import (
    PYTEST_VER,
    get_stash,
    make_path_kwargs,
    set_stash,
)

HISTKEY = "ruff/mtimes"


def pytest_addoption(parser):
    group = parser.getgroup("general")
    group.addoption("--ruff", action="store_true", help="enable checking with ruff")
    group.addoption(
        "--ruff-format", action="store_true", help="enable format checking with ruff"
    )
    group.addoption(
        "--ruff-config",
        action="store",
        type=str,
        help="uses custom ruff config file",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "ruff: Tests which run ruff.")

    if not config.option.ruff or not hasattr(config, "cache"):
        return

    set_stash(config, config.cache.get(HISTKEY, {}))


if PYTEST_VER >= (7, 0):

    def pytest_collect_file(file_path, parent, fspath=None):
        config = parent.config
        if not config.option.ruff:
            return

        if file_path.suffix != ".py":
            return

        return RuffFile.from_parent(parent, **make_path_kwargs(file_path))

else:

    def pytest_collect_file(path, parent, fspath=None):
        config = parent.config
        if not config.option.ruff:
            return

        if path.ext != ".py":
            return

        return RuffFile.from_parent(parent, **make_path_kwargs(path))


def pytest_sessionfinish(session, exitstatus):
    config = session.config

    if not config.option.ruff or not hasattr(config, "cache"):
        return

    # Update cache only in pytest-xdist controller.
    # It works fine if pytest-xdist is not being used.
    if not hasattr(config, "workerinput"):
        cache = config.cache.get(HISTKEY, {})
        cache.update(get_stash(config))
        config.cache.set(HISTKEY, cache)


class RuffError(Exception):
    pass


def _realpath(path):
    return os.path.realpath(str(path))


def _run_ruff(session, item_type, args, config_file):
    """
    Run ruff once over the collected files of `item_type` and return
    `(returncode, stdout, stderr)`. `args` is the ruff subcommand and its
    flags, e.g. ["check", "--output-format=json"].
    """
    paths = [str(i.fspath) for i in session.items if type(i) is item_type]
    command = [find_ruff_bin(), *args, *paths, "--force-exclude"]
    if config_file:
        command.append("--config={}".format(config_file))
    child = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = child.communicate()
    return child.returncode, stdout, stderr


def batch_check_results(session, config_file):
    """
    Run ruff once for every collected file and cache the result on the session,
    so each test item is a lookup instead of its own ruff subprocess.
    """
    # Always return early if we've already run ruff this session
    cached = getattr(session, "_ruff_check", None)
    if cached is not None:
        return cached

    returncode, stdout, stderr = _run_ruff(
        session, RuffItem, ["check", "--quiet", "--output-format=json"], config_file
    )

    # failures maps each failing file to its rendered ruff message(s)
    failures = {}
    error = None

    # returncode 2 means ruff itself failed (e.g. a bad config); report that
    if returncode == 2:
        error = stderr.decode()
    elif stdout.strip():
        # Load the JSON output from ruff and render each violation as a line
        for violation in json.loads(stdout):
            loc = violation["location"]
            fixable = " [*]" if violation.get("fix") else ""
            line = "{}:{}:{}: {}{} {}".format(
                violation["filename"],
                loc["row"],
                loc["column"],
                violation["code"],
                fixable,
                violation["message"],
            )
            failures.setdefault(_realpath(violation["filename"]), []).append(line)

    # Join each file's lines into a single message for the test failure
    failures = {path: "\n".join(lines) for path, lines in failures.items()}
    session._ruff_check = (failures, error)
    return session._ruff_check


def batch_format_results(session, config_file):
    """
    Run ruff format once for every collected file and cache the result on the
    session, so each test item is a lookup instead of its own ruff subprocess.
    """
    cached = getattr(session, "_ruff_format", None)
    if cached is not None:
        return cached

    returncode, stdout, stderr = _run_ruff(
        session, RuffFormatItem, ["format", "--check"], config_file
    )

    failing = set()
    error = None
    if returncode == 2:
        error = stderr.decode()
    else:
        # ruff format --check lists each unformatted file as "Would reformat: ..."
        prefix = "Would reformat: "
        for line in stdout.decode().splitlines():
            if line.startswith(prefix):
                failing.add(_realpath(line[len(prefix) :]))

        # If no files were listed as "Would reformat:" but the return code is 1,
        # treat it as a failure and show what we can
        if returncode == 1 and not failing:
            error = (
                "Ruff format errorss, but not parse ruff format output:\n"
                + stdout.decode()
            )

    session._ruff_format = (failing, error)
    return session._ruff_format


class RuffFile(pytest.File):
    def collect(self):
        collection = []
        config_file = None
        if self.config.option.ruff_config:
            config_file = self.config.option.ruff_config
        if self.config.option.ruff:
            collection.append(
                RuffItem.from_parent(self, name="ruff", config_file=config_file)
            )
        if self.config.option.ruff_format:
            collection.append(
                RuffFormatItem.from_parent(
                    self, name="ruff::format", config_file=config_file
                )
            )
        return collection


def pytest_exception_interact(node, call, report):
    if isinstance(call.excinfo.value, RuffError):
        report.longrepr = str(call.excinfo.value)


class RuffItem(pytest.Item):
    name = "ruff"

    def __init__(self, *k, config_file, **kwargs):
        super().__init__(*k, **kwargs)
        self.add_marker("ruff")
        self._config_file = config_file

    def setup(self):
        ruffmtimes = get_stash(self.config)
        self._ruffmtime = self.fspath.mtime()
        if ruffmtimes:
            old = ruffmtimes.get(str(self.fspath))
            if old == self._ruffmtime:
                pytest.skip("file previously passed ruff checks")

    def runtest(self):
        self.handler(path=self.fspath)

        ruffmtimes = get_stash(self.config)
        if ruffmtimes:
            ruffmtimes[str(self.fspath)] = self._ruffmtime

    def reportinfo(self):
        return (self.fspath, None, "")

    def handler(self, path):
        failures, error = batch_check_results(self.session, self._config_file)
        if error:
            raise RuffError(error)
        message = failures.get(_realpath(path))
        if message:
            raise RuffError(message)


class RuffFormatItem(RuffItem):
    name = "ruff::format"

    def handler(self, path):
        failing, error = batch_format_results(self.session, self._config_file)
        if error:
            raise RuffError(error)
        if _realpath(path) in failing:
            raise RuffError("File would be reformatted")
