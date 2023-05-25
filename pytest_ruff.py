from subprocess import Popen, PIPE

import pytest
from ruff.__main__ import find_ruff_bin

HISTKEY = "ruff/mtimes"
_mtimes_stash_key = pytest.StashKey[dict[str, float]]()


def pytest_addoption(parser):
    group = parser.getgroup("general")
    group.addoption("--ruff", action="store_true", help="enable checking with ruff")


def pytest_configure(config):
    config.addinivalue_line("markers", "ruff: Tests which run ruff.")
    if config.option.ruff and hasattr(config, "cache"):
            config.stash[_mtimes_stash_key] = config.cache.get(HISTKEY, {})


def pytest_collect_file(file_path, path, parent):
    config = parent.config
    if not config.option.ruff:
        return

    if file_path.suffix != ".py":
        return

    return RuffFile.from_parent(parent, path=file_path)


def pytest_sessionfinish(session, exitstatus):
    config = session.config

    if not config.option.ruff:
        return

    # Update cache only in pytest-xdist controller.
    # It works fine if pytest-xdist is not being used.
    if not hasattr(config, "workerinput"):
        cache = config.cache.get(HISTKEY, {})
        cache.update(config.stash[_mtimes_stash_key])
        config.cache.set(HISTKEY, cache)


class RuffError(Exception):
    pass


class RuffFile(pytest.File):
    def collect(self):
        return [RuffItem.from_parent(self, name="ruff")]


class RuffItem(pytest.Item):
    def __init__(self, *k, **kwargs):
        super().__init__(*k, **kwargs)
        self.add_marker("ruff")

    def setup(self):
        ruffmtimes = self.config.stash.get(_mtimes_stash_key, {})
        self._ruffmtime = self.fspath.mtime()
        old = ruffmtimes.get(str(self.fspath))
        if old == self._ruffmtime:
            pytest.skip("file previously passed ruff checks")

    def runtest(self):
        check_file(self.fspath)
        ruffmtimes = self.config.stash.get(_mtimes_stash_key, None)
        if ruffmtimes:
            ruffmtimes[str(self.fspath)] = self._ruffmtime

    def reportinfo(self):
        return (self.fspath, None, "")


def check_file(path):
    ruff = find_ruff_bin()
    command = f"{ruff} {path} --quiet --show-source"
    child = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, _ = child.communicate()
    if stdout:
        raise RuffError(stdout.decode())
