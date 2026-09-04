"""A detector's ``search_paths``: what they may say, and what they then find.

A detector may name directories under the project its tool is looked for in
ahead of the default search path — bundler's ``bin``, which is not every
project's to have searched. An entry that is not a non-empty string staying
under the project is refused rather than loaded and silently searched nowhere,
and answers the same on every platform because a config travels.

The refusals a detector earns anywhere else are ``test_detector_schema.py``;
where a bare command name is resolved along the default path is
``test_tool_resolution.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from bare_machine import machine_bin, project_with_no_tools
from detector_config import accepting_search_paths, refusing_search_paths
from executable_stub import write_stub
from habit_hooks.detectors import COMMAND_KIND, NODE_MODULE_KIND, Detector
from habit_hooks.missing_tools import missing_tools
from habit_hooks.project_paths import tool_executable
from habit_hooks.sensors.named_tools import DeclaredTools

RUBOCOP = Detector(name="rubocop", kind=COMMAND_KIND, install="gem install rubocop")
BUNDLED_RUBOCOP = Detector(
    name="rubocop",
    kind=COMMAND_KIND,
    install="gem install rubocop",
    search_paths=("bin",),
)
BUNDLED_NODE = Detector(
    name="node", kind=COMMAND_KIND, install="brew install node", search_paths=("bin",)
)
TS_MORPH = Detector(name="ts-morph", kind=NODE_MODULE_KIND, install="npm i -D ts-morph")


def test_a_command_only_in_the_project_s_bin_is_found_by_no_default_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``bin`` is a directory a project may keep its own scripts under, so it is
    not on the search path every tool is looked for along — a script named after
    a tool there would outrank a real install beside it. The plugin whose tools
    live there names the directory on its detector instead, and a detector that
    names nothing looks along the default path only.
    """
    project = project_with_no_tools(tmp_path, monkeypatch)
    write_stub(project / "bin", "rubocop")

    assert tool_executable("rubocop", project) is None
    assert missing_tools([RUBOCOP], project) == (RUBOCOP,)


def test_a_detector_s_own_search_path_finds_the_bundler_binstub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The search path a detector names is searched ahead of the default one,
    so the project's own binstub wins over whatever the machine carries.
    """
    project = project_with_no_tools(tmp_path, monkeypatch)
    write_stub(machine_bin(tmp_path), "rubocop")
    write_stub(project / "bin", "rubocop")

    found = tool_executable("rubocop", project, ("bin",))

    assert Path(found or "").parent == project / "bin"


def test_a_bundler_binstub_answers_the_setup_and_the_run_in_one_move(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both sides of the tool question across the install that matters to a
    Ruby project: a binstub landing in ``bin`` is the very move that stops the
    setup reporting rubocop missing and gives the run a file to spawn. Both
    ask the detector's own search path, so neither can come to a different
    answer about a directory the default path does not know.
    """
    project = project_with_no_tools(tmp_path, monkeypatch)
    tools = DeclaredTools([BUNDLED_RUBOCOP], project)

    assert missing_tools([BUNDLED_RUBOCOP], project) == (BUNDLED_RUBOCOP,)
    assert tools.file_for("rubocop") is None

    write_stub(project / "bin", "rubocop")

    assert missing_tools([BUNDLED_RUBOCOP], project) == ()
    assert Path(tools.file_for("rubocop") or "").parent == project / "bin"


def test_a_node_found_along_its_detector_s_search_path_answers_for_its_modules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A node-module is asked of node, and node is asked of the search path —
    the one its own detector declared, or the module behind it is reported
    missing on a machine whose node lives in a directory the default path does
    not know.
    """
    project = project_with_no_tools(tmp_path, monkeypatch)

    assert missing_tools([BUNDLED_NODE, TS_MORPH], project) == (BUNDLED_NODE,)

    write_stub(project / "bin", "node")

    assert missing_tools([BUNDLED_NODE, TS_MORPH], project) == ()


def test_a_directory_under_the_project_is_valid(tmp_path: Path) -> None:
    """``bin`` is the case the key exists for: bundler's binstubs, which only
    the tools that live there should be looked for along."""
    accepting_search_paths(tmp_path, '["bin"]')


def test_search_paths_written_as_a_string_is_refused(tmp_path: Path) -> None:
    """A single string is the natural wrong guess at a list of one, and a
    string is not a directory anything can search."""
    assert "list" in refusing_search_paths(tmp_path, '"bin"')


def test_an_empty_search_path_is_refused(tmp_path: Path) -> None:
    """An empty string is the absence it looks like: it names no directory, so
    searching it is a claim about nothing."""
    assert "non-empty" in refusing_search_paths(tmp_path, '[""]')


def test_a_posix_absolute_search_path_is_refused(tmp_path: Path) -> None:
    """A search path names a directory under the project, so an absolute one is
    a directory the project does not keep — and a tool found there would be one
    the project never pinned."""
    assert "under the project" in refusing_search_paths(tmp_path, '["/usr/local/bin"]')


def test_a_windows_drive_search_path_is_refused(tmp_path: Path) -> None:
    """``C:\\tools`` reads as a relative name to the host's own ``isabs`` on a
    Mac, and a config travels: the directory is not under the project there
    either."""
    assert "under the project" in refusing_search_paths(tmp_path, '["C:\\\\tools"]')


def test_a_drive_relative_search_path_is_refused(tmp_path: Path) -> None:
    """``C:tools`` is not a directory under the project even to Windows: it
    names the current directory of another drive, wherever that happens to be."""
    assert "under the project" in refusing_search_paths(tmp_path, '["C:tools"]')


def test_a_rooted_search_path_is_refused(tmp_path: Path) -> None:
    r"""A leading backslash roots the path on Windows as a leading ``/`` does
    on POSIX, so ``\tools`` names a directory the project does not keep."""
    assert "under the project" in refusing_search_paths(tmp_path, '["\\\\tools"]')


def test_a_search_path_climbing_out_of_the_project_is_refused(tmp_path: Path) -> None:
    """A ``..`` component names a directory outside the project whatever else
    the path says, so the neighbour's tools are never searched as the
    project's own."""
    assert "under the project" in refusing_search_paths(tmp_path, '["../bin"]')


def test_a_search_path_that_climbs_and_returns_is_refused(tmp_path: Path) -> None:
    """``bin/..`` is the project root and ``bin/../bin`` is ``bin``, but a
    ``..`` component is refused rather than resolved: the entry is for a
    reader naming a directory, not for a path algebra."""
    assert "under the project" in refusing_search_paths(tmp_path, '["bin/.."]')


@pytest.mark.parametrize("separator", [":", ";"])
def test_a_search_path_carrying_a_path_separator_is_refused(
    tmp_path: Path, separator: str
) -> None:
    """The entries are joined into one search path with exactly these
    characters — ``:`` on POSIX, ``;`` on Windows — so one entry carrying
    either splices every directory after it into each lookup for the tool:
    ``bin:../tools`` searches ``../tools``, a directory the project never
    named. Note the ``..`` is not a component of its own here, so nothing else
    catches it. Both are refused on every host because a plugin config travels
    between POSIX and Windows."""
    assert "under the project" in refusing_search_paths(
        tmp_path, f'["bin{separator}../tools"]'
    )
