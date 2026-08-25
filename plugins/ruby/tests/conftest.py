"""What every test here needs of the run it stands in for.

**A helper loads as a loose script.** ``sensors/rubocop.toml`` spells
``${python} ${dir}/rubocop_sensor.py``, so the interpreter puts the helper's own
directory first on ``sys.path``, and a unit test does the same rather than
reaching the code as ``habit_hooks_ruby.sensors.rubocop_sensor`` — a load path
no run ever takes (see "A plugin helper imports its neighbours as top-level
modules" in CLAUDE.md).

**A helper is handed its tool as a file.** The spec names it with
``${detector:rubocop}``, which the run resolves against the project's own bins
before the helper is spawned (``project_paths.tool_executable``). A test
spawning the helper directly stands in for the run, so it asks that same
question and hands over a real file rather than a name. Absent is a failure
rather than a skip: a machine without rubocop is a suite that has quietly
stopped gating, not a machine this plugin does not apply to.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

SENSORS = Path(__file__).resolve().parents[1] / "src" / "habit_hooks_ruby" / "sensors"

sys.path.insert(0, str(SENSORS))


@pytest.fixture(scope="session")
def rubocop() -> str:
    """The file this machine runs rubocop by, as the sensor's first argument.

    ``shutil.which`` rather than the name on disk: RubyGems installs a ``.bat``
    shim on Windows, which a lookup finds and a spawn handed the bare name
    cannot reach.
    """
    found = shutil.which("rubocop")
    if found is None:
        pytest.fail("rubocop is not on PATH — 'gem install rubocop'")
    return found
