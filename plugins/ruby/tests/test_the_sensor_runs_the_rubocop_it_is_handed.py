"""The sensor spawns the rubocop it was handed, never a name it looks up again.

``sensors/rubocop.toml`` names its tool with ``${detector:rubocop}``, so the run
resolves it to a file and passes that file as the helper's first argument.
Handing over the file is the whole point: a bare name is looked up again by
whatever spawns it, and Windows' ``CreateProcess`` adds ``.exe`` and nothing
else, where RubyGems installs rubocop as a ``.bat`` shim, and
``bundle binstubs`` writes a ``.cmd``.

A ``PATH`` that cannot answer ``rubocop`` is what proves the helper takes it: a
helper still spelling that name would find nothing to spawn, while one handed
the file runs a tool no search path leads to.

**The interpreter has to be put back, which the other plugins do not have to
do.** ``rubocop`` is not a program; it is a RubyGems binstub that begins
``#!/usr/bin/env ruby``, and it is installed into the very directory its
interpreter lives in. Taking ``rubocop`` off ``PATH`` therefore takes ``ruby``
with it, and the binstub then falls through to whatever ``ruby`` answers next,
on a Mac the system 2.6, which has no rubocop gem and dies in
``find_spec_for_exe``. That is a real failure and the sensor is right to fail on
it (``test_a_crashing_rubocop_fails_the_run``), but it is not the question here,
so ``ruby`` alone is handed back on a directory of its own. What is left cannot
answer ``rubocop`` and can answer ``ruby``, which isolates the one variable.

A rubocop nobody installed is not this plugin's to answer for. The run resolves
the name before the helper is spawned and answers for an absent one itself, as
the ordinary missing command it is (``tests/test_a_tool_a_part_cannot_run.py``).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from tool_lookup import where_the_bare_name_reaches_nothing

SENSORS = Path(__file__).resolve().parents[1] / "src" / "habit_hooks_ruby" / "sensors"


def _where_only_the_interpreter_is_left(bin_dir: Path) -> dict[str, str]:
    """This machine's environment with ``rubocop`` unreachable and ``ruby`` not.

    The link is to the interpreter this machine really uses, so the binstub
    handed to the sensor loads from the gems it was installed into.
    """
    interpreter = shutil.which("ruby")
    if interpreter is None:
        pytest.fail("ruby is not on PATH, rubocop cannot run without it")
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / "ruby").symlink_to(interpreter)

    environment = where_the_bare_name_reaches_nothing("rubocop")
    environment["PATH"] = os.pathsep.join([str(bin_dir), environment["PATH"]])
    assert shutil.which("rubocop", path=environment["PATH"]) is None
    assert shutil.which("ruby", path=environment["PATH"]) is not None
    return environment


@pytest.mark.skipif(
    os.name == "nt", reason="a POSIX shebang is what makes the interpreter reachable"
)
def test_the_rubocop_sensor_spawns_the_rubocop_it_was_handed(
    tmp_path: Path, rubocop: str
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".rubocop.yml").write_text(
        "AllCops:\n  DisabledByDefault: true\nMetrics/ParameterLists:\n  Enabled: true\n",
        encoding="utf-8",
    )
    (project / "billing.rb").write_text(
        "def charge(a, b, c, d, e, f, g)\n  a\nend\n", encoding="utf-8"
    )

    result = subprocess.run(
        [sys.executable, str(SENSORS / "rubocop_sensor.py"), rubocop, "billing.rb"],
        cwd=project,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=_where_only_the_interpreter_is_left(tmp_path / "interpreter-only"),
    )

    assert result.returncode == 0, result.stderr
    assert [finding["smell"] for finding in json.loads(result.stdout)] == [
        "too-many-parameters"
    ]
