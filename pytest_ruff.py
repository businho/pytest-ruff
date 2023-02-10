from subprocess import Popen, PIPE

import pytest
from ruff.__main__ import find_ruff_bin

HISTKEY = "ruff/mtimes"


def pytest_addoption(parser):
    group = parser.getgroup("general")
    group.addoption('--ruff', action='store_true', help="enable checking with ruff")


def pytest_configure(config):
    if config.option.ruff:
        if hasattr(config, 'cache'):
            config._ruffmtimes = config.cache.get(HISTKEY, {})


def pytest_collect_file(file_path, path, parent):
    config = parent.config
    if not config.option.ruff:
        return

    if file_path.suffix != ".py":
        return

    item = RuffFile.from_parent(parent, path=file_path)
    return item


def pytest_unconfigure(config):
    if hasattr(config, "_ruffmtimes"):
        cache = config.cache.get(HISTKEY, {})
        cache.update(config._ruffmtimes)
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
        ruffmtimes = getattr(self.config, "_ruffmtimes", {})
        self._ruffmtime = self.fspath.mtime()
        old = ruffmtimes.get(str(self.fspath))
        if old == self._ruffmtime:
            pytest.skip("file previously passed ruff checks")

    def runtest(self):
        check_file(self.fspath)
        if hasattr(self.config, "_ruffmtimes"):
            self.config._ruffmtimes[str(self.fspath)] = self._ruffmtime

    def repr_failure(self, excinfo):
        if excinfo.errisinstance(RuffError):
            return excinfo.value.args[0].decode()
        return super().repr_failure(excinfo)

    def reportinfo(self):
        return (self.fspath, None, "")


def check_file(path):
    ruff = find_ruff_bin()
    command = f"{ruff} {path} --quiet"
    child = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = child.communicate()
    if stdout:
        raise RuffError(stdout, stderr)
