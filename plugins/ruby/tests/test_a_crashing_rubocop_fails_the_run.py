"""A broken ``rubocop`` must not read as clean — it must fail the sensor.

``rubocop_crashed`` trusts exactly RuboCop's own contract (0 clean, 1 offences
found); the boundary is exercised directly here, and the real-tool case below
proves the whole helper honours it.

The real-tool case is a ``.rubocop.yml`` naming cops from an extension gem the
project has not got. That is not a contrived break: it is the single most likely
way this sensor fails in the wild, because every Rails project's config names
``rubocop-rails`` and the gem only loads under the project's own bundle. RuboCop
answers it with an ``Error:`` and a non-zero exit, and the sensor has to carry
that through rather than print an empty findings array — a false-clean run on a
config problem is exactly what #88 exists to prevent.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from rubocop_sensor import report, rubocop_crashed


def _crashed(result: subprocess.CompletedProcess[str]) -> bool:
    """The question `main` asks, composed the way `main` composes it."""
    return rubocop_crashed(result, report(result))

SENSOR = (
    Path(__file__).resolve().parents[1]
    / "src/habit_hooks_ruby/sensors/rubocop_sensor.py"
)

EMPTY_REPORT = '{"files":[],"summary":{"offense_count":0}}'

# What a binstub prints when the `ruby` its shebang found has no rubocop gem.
# It goes to stderr, stdout stays empty, and the exit code is 1.
BINSTUB_TRACEBACK = (
    "rubygems.rb:283:in `find_spec_for_exe': can't find gem rubocop (>= 0.a) "
    "with executable rubocop (Gem::GemNotFoundException)"
)


def _result(
    returncode: int, stdout: str = EMPTY_REPORT, stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=stderr
    )


@pytest.mark.parametrize("returncode", [0, 1])
def test_rubocop_s_own_exit_codes_are_trusted_when_it_reported(
    returncode: int,
) -> None:
    """0 is clean and 1 is "offences found" — a linter's way of saying it
    worked, *provided* it produced the report that says so."""
    assert _crashed(_result(returncode)) is False


@pytest.mark.parametrize("returncode", [2, 127, -9])
def test_any_other_exit_code_is_a_crash(returncode: int) -> None:
    assert _crashed(_result(returncode)) is True


def test_a_binstub_that_never_reached_rubocop_is_a_crash_not_a_clean_run() -> None:
    """The regression this file is really about.

    `rubocop` is a RubyGems binstub with a `#!/usr/bin/env ruby` shebang. Point
    it at an interpreter it is not installed into — a version manager off PATH,
    the wrong bundle, macOS's system Ruby — and it dies in `find_spec_for_exe`
    and exits **1**, the code that otherwise means "I found offences". Judged on
    the exit code alone that is a clean file from a tool that never started.
    """
    crashed = _result(1, stdout="", stderr=BINSTUB_TRACEBACK)

    assert report(crashed) is None
    assert _crashed(crashed) is True


@pytest.mark.parametrize(
    "stdout",
    ["", "   \n", "Error: could not read .rubocop.yml", '{"summary":{}}', "[]"],
    ids=["empty", "blank", "prose", "no-files-key", "not-an-object"],
)
def test_output_that_is_not_a_report_is_a_crash(stdout: str) -> None:
    """RuboCop prints its JSON envelope on every run it completed, down to
    `"files": []` when it inspected nothing — so anything else is a run that did
    not happen, whatever it exited with. `files` is the key that makes it a
    report; valid JSON alone is not enough."""
    assert _crashed(_result(1, stdout=stdout)) is True


def test_a_report_inspecting_nothing_is_still_a_report() -> None:
    """The other side of that rule: every file excluded is a real, believable
    clean run, and must not be mistaken for a tool that failed to start."""
    assert _crashed(_result(0, stdout=EMPTY_REPORT)) is False


def test_a_config_naming_an_unloadable_gem_s_cops_fails_the_run(
    tmp_path: Path, rubocop: str
) -> None:
    """The Rails case. A `.rubocop.yml` naming `Rails/*` cops without the
    `rubocop-rails` gem loaded is a hard RuboCop error, and the sensor must
    surface it rather than report the file clean."""
    (tmp_path / ".rubocop.yml").write_text(
        "Rails/Blank:\n  Enabled: true\n", encoding="utf-8"
    )
    (tmp_path / "app.rb").write_text("puts 'hi'\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SENSOR), rubocop, "app.rb"],
        cwd=tmp_path,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 2
    assert result.stdout.strip() == ""
    assert "rubocop-rails" in result.stderr


def test_an_unreadable_config_fails_the_run(tmp_path: Path, rubocop: str) -> None:
    """A `.rubocop.yml` that is not YAML at all — the typo case, which must be a
    named failure rather than a run that quietly measured nothing."""
    (tmp_path / ".rubocop.yml").write_text("\tnot: [valid\n", encoding="utf-8")
    (tmp_path / "app.rb").write_text("puts 'hi'\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SENSOR), rubocop, "app.rb"],
        cwd=tmp_path,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )

    assert result.returncode == 2
    assert result.stdout.strip() == ""
    assert result.stderr.strip() != ""
