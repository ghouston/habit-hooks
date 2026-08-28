"""A bare ``argv[0]`` that names a declared tool, and the file it then runs.

``${detector:<name>}`` is one way a recipe names a tool; a bare program name is
the other, and the authoring guide promises both
(``docs/authoring-plugins.spec.md``). The bare spelling used to be looked up
along the default path alone, whatever the tool's detector declared — so a
binstub installed only under the project's ``bin`` was cleared by the setup
(``missing_tools`` asks the detector's own search paths) and then not found by
the run, the very disagreement ``project_paths.tool_executable`` exists to
prevent. A bare name this run's plugins declared is resolved to the same file
the placeholder spelling stands for; a name nobody declared keeps the lookup
the spawn always made.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from bare_machine import project_with_no_tools
from detector_declarations import declaring
from executable_stub import write_stub
from plugin_fixture import one_sensor

from habit_hooks.project_paths import tool_executable
from habit_hooks.scope import Scope
from habit_hooks.sensors.execution import Execution
from habit_hooks.sensors.model import Part

BUNDLER = (
    '{ name = "rubocop", kind = "command", install = "gem install rubocop", '
    'search_paths = ["bin"] }'
)


def _argv(project: Path, part: Part) -> list[str]:
    """The argv spawning ``part`` in ``project`` would carry."""
    return Execution(project_dir=project, scope=Scope(files=[]))._expand(part)


def _run(project: Path, part: Part) -> object:
    """What running ``part`` over one file comes to."""
    scope = Scope(files=["a.rb"])
    return Execution(project_dir=project, scope=scope).run_sensors([part])


def test_a_bare_program_is_looked_for_along_the_search_path_its_detector_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bare spelling of a name is resolved exactly as ``${detector:<name>}``
    is: the same detector, the same search paths, the same file."""
    project = project_with_no_tools(tmp_path, monkeypatch)
    write_stub(project / "bin", "rubocop")
    part = one_sensor(project, 'argv = ["rubocop", "--json"]', declaring(BUNDLER))

    argv = _argv(project, part)

    assert Path(argv[0]).parent == project / "bin"
    assert Path(argv[0]).stem == "rubocop"
    assert argv[1:] == ["--json"]


def test_a_bare_program_only_the_detector_could_find_is_the_file_that_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole gap: the default lookup cannot find the program, and the run
    still executes the detector's file — a clean run, where the bare name alone
    was the missing command the notice would have named."""
    project = project_with_no_tools(tmp_path, monkeypatch)
    write_stub(project / "bin", "rubocop")
    part = one_sensor(project, 'argv = ["rubocop", "--json"]', declaring(BUNDLER))

    assert tool_executable("rubocop", project) is None

    run = _run(project, part)

    assert run.notices == []
    assert run.findings == []


def test_a_bare_program_declared_and_absent_fails_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A declared tool the project has not got is the everyday missing tool,
    whichever spelling named it — answered before the spawn, naming what to
    install."""
    project = project_with_no_tools(tmp_path, monkeypatch)
    part = one_sensor(project, 'argv = ["rubocop", "--json"]', declaring(BUNDLER))

    run = _run(project, part)

    assert run.notices == [
        "habit-sensors: sensor 's' needs the 'rubocop' command, which is not "
        "installed — install it, or disable the sensor with [sensors.s] "
        "disabled = true"
    ]


def test_a_bare_program_nobody_declared_keeps_the_name_it_spelled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only a declared name is resolved through its detector: ``node`` here is
    nobody's, and the recipe keeps the name it spelled for the spawn to look
    up as it always did."""
    project = project_with_no_tools(tmp_path, monkeypatch)
    part = one_sensor(project, 'argv = ["node", "h.cjs"]', declaring(BUNDLER))

    assert _argv(project, part)[0] == "node"
