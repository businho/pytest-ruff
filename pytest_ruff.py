from subprocess import Popen, PIPE
# Python<=3.8 don't support typing with builtin dict.
from typing import Dict

import pytest
from ruff.__main__ import find_ruff_bin

HISTKEY = "ruff/mtimes"
_MTIMES_STASH_KEY = pytest.StashKey[Dict[str, float]]()


def pytest_addoption(parser):
    group = parser.getgroup("general")
    group.addoption("--ruff", action="store_true", help="enable checking with ruff")
    group.addoption("--ruff-format", action="store_true", help="enable format checking with ruff")


def pytest_configure(config):
    config.addinivalue_line("markers", "ruff: Tests which run ruff.")

    if not config.option.ruff or not hasattr(config, "cache"):
        return

    config.stash[_MTIMES_STASH_KEY] = config.cache.get(HISTKEY, {})


def pytest_collect_file(file_path, path, parent):
    config = parent.config
    if not config.option.ruff:
        return

    if file_path.suffix != ".py":
        return

    return RuffFile.from_parent(parent, path=file_path)


def pytest_sessionfinish(session, exitstatus):
    config = session.config

    if not config.option.ruff or not hasattr(config, "cache"):
        return

    # Update cache only in pytest-xdist controller.
    # It works fine if pytest-xdist is not being used.
    if not hasattr(config, "workerinput"):
        cache = config.cache.get(HISTKEY, {})
        cache.update(config.stash[_MTIMES_STASH_KEY])
        config.cache.set(HISTKEY, cache)


class RuffError(Exception):
    pass


class RuffFile(pytest.File):
    def collect(self):
        return [
            RuffItem.from_parent(self, name="ruff"),
            RuffFormatItem.from_parent(self, name="ruff::format"),
        ]


def check_file(path):
    ruff = find_ruff_bin()
    command = [ruff, "check", path, '--quiet', '--show-source']
    child = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, _ = child.communicate()
    if stdout:
        raise RuffError(stdout.decode())


def format_file(path):
    ruff = find_ruff_bin()
    command = [ruff, "format", path, '--quiet', '--check']
    with Popen(command) as child:
        pass

    if child.returncode == 1:
        raise RuffError("File would be reformatted")


class RuffItem(pytest.Item):
    handler = check_file

    def __init__(self, *k, **kwargs):
        super().__init__(*k, **kwargs)
        self.add_marker("ruff")

    def setup(self):
        ruffmtimes = self.config.stash.get(_MTIMES_STASH_KEY, {})
        self._ruffmtime = self.fspath.mtime()
        old = ruffmtimes.get(str(self.fspath))
        if old == self._ruffmtime:
            pytest.skip("file previously passed ruff checks")

    def runtest(self):
        self.handler(self.fspath)

        ruffmtimes = self.config.stash.get(_MTIMES_STASH_KEY, None)
        if ruffmtimes:
            ruffmtimes[str(self.fspath)] = self._ruffmtime

    def reportinfo(self):
        return (self.fspath, None, "")


class RuffFormatItem(RuffItem):
    handler = format_file
