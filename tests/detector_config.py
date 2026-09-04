"""A plugin declaring detectors, and the refusal or clean load that follows.

Shared by ``test_detector_schema.py`` and ``test_detector_search_paths.py``,
which each carried a private copy of the same helpers until the search-path
separator regression needed room in one without pushing either module past
the ``oversized-file`` gate the dogfood run enforces on tests too.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from habit_hooks.config import load_config
from plugin_fixture import write_plugin, write_project_config

INSTALL = 'install = "brew install jq"'


def declaring(tmp_path: Path, body: str) -> Path:
    """A project running ``alpha``, whose config says whatever ``body`` says."""
    write_project_config(tmp_path, 'plugins = ["alpha"]')
    write_plugin(tmp_path, "alpha", {"config.toml": body})
    return tmp_path


def refusal_for(project_dir: Path) -> str:
    """The refusal from loading ``project_dir``, as the console prints it."""
    with pytest.raises(SystemExit) as failure:
        load_config(project_dir)
    return str(failure.value)


def declaring_search_paths(tmp_path: Path, search_paths: str) -> None:
    """A project whose plugin declares jq, searched wherever ``search_paths`` says."""
    entry = (
        f'{{ name = "jq", kind = "command", {INSTALL}, search_paths = {search_paths} }}'
    )
    declaring(tmp_path, f"detectors = [{entry}]")


def refusing_search_paths(tmp_path: Path, search_paths: str) -> str:
    """The refusal message, already checked to name the detector and the key."""
    declaring_search_paths(tmp_path, search_paths)
    message = refusal_for(tmp_path)
    assert "detector 'jq'" in message
    assert "'search_paths'" in message
    return message


def accepting_search_paths(tmp_path: Path, search_paths: str) -> None:
    """A project declaring jq searched along ``search_paths`` loads cleanly."""
    declaring_search_paths(tmp_path, search_paths)
    load_config(tmp_path)
