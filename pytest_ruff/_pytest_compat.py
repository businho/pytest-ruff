from pathlib import Path

# Python<=3.8 don't support typing with builtin dict.
from typing import Dict

import pytest

try:
    from pytest import Stash, StashKey
except ImportError:
    import _pytest.store

    Stash = _pytest.store.Store
    StashKey = _pytest.store.StoreKey

PYTEST_VER = tuple(int(x) for x in pytest.__version__.split(".")[:2])
_MTIMES_STASH_KEY = StashKey[Dict[str, float]]()


def make_path_kwargs(p):
    """
    Make keyword arguments passing either path or fspath, depending on pytest version.

    In pytest 7.0, the `fspath` argument to Nodes has been deprecated, so we pass `path`
    instead.
    """
    return dict(path=Path(p)) if PYTEST_VER >= (7, 0) else dict(fspath=p)


def get_stash_object(config):
    try:
        stash = config.stash
    except AttributeError:
        stash = config._store
    return stash


def get_stash(config):
    missing = object()
    stash = get_stash_object(config).get(_MTIMES_STASH_KEY, default=missing)
    assert stash is not missing
    return stash


def set_stash(config, value):
    get_stash_object(config)[_MTIMES_STASH_KEY] = value
