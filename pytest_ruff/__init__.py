from subprocess import Popen, PIPE

import pytest

from ruff.__main__ import find_ruff_bin

from pytest_ruff._pytest_compat import get_stash, make_path_kwargs, set_stash

HISTKEY = "ruff/mtimes"


def pytest_addoption(parser):
    group = parser.getgroup("general")
    group.addoption("--ruff", action="store_true", help="enable checking with ruff")
    group.addoption(
        "--ruff-format", action="store_true", help="enable format checking with ruff"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "ruff: Tests which run ruff.")

    if not config.option.ruff or not hasattr(config, "cache"):
        return

    set_stash(config, config.cache.get(HISTKEY, {}))


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


class RuffFile(pytest.File):
    def collect(self):
        collection = []
        if self.config.option.ruff:
            collection.append(RuffItem)
        if self.config.option.ruff_format:
            collection.append(RuffFormatItem.from_parent(self, name="ruff::format"))
        return [Item.from_parent(self, name=Item.name) for Item in collection]


def check_file(path):
    ruff = find_ruff_bin()
    command = [ruff, "check", path, "--quiet", "--show-source", "--force-exclude"]
    child = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, _ = child.communicate()
    if stdout:
        raise RuffError(stdout.decode())


def format_file(path):
    ruff = find_ruff_bin()
    command = [ruff, "format", path, "--quiet", "--check", "--force-exclude"]
    with Popen(command) as child:
        pass

    if child.returncode == 1:
        raise RuffError("File would be reformatted")


class RuffItem(pytest.Item):
    name = "ruff"

    def __init__(self, *k, **kwargs):
        super().__init__(*k, **kwargs)
        self.add_marker("ruff")

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
        return check_file(path)


class RuffFormatItem(RuffItem):
    name = "ruff::format"

    def handler(self, path):
        return format_file(path)
