"""The helper wired to the real ``rubocop``.

The pure mapping is covered by ``test_the_rubocop_pipeline_maps_cops_to_smells``;
this proves RuboCop's own output still has the shape that mapping expects: its
per-file nesting, its ``cop_name``/``location`` field names, and its exit codes.
A RuboCop upgrade that renames any of them fails here rather than silently
producing an empty run.

Every case writes its own ``.rubocop.yml`` with ``DisabledByDefault: true`` and
names the cops it is about. That is not the sensor being narrowed. The sensor
passes no ``--only`` and forwards whatever fires. It is the *project* deciding,
which is the arrangement under test, and it keeps the assertions about one cop
instead of about RuboCop's several-hundred-cop default set.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from platform_probe import A_FILESYSTEM_THAT_ALLOWS_A_STAR_IN_A_FILENAME

SENSOR = (
    Path(__file__).resolve().parents[1]
    / "src/habit_hooks_ruby/sensors/rubocop_sensor.py"
)


def _run(project: Path, rubocop: str, *files: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SENSOR), rubocop, *files],
        cwd=project,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )


def _configure(project: Path, *cops: str) -> None:
    """A project config enabling exactly ``cops`` and nothing else."""
    enabled = "".join(f"{cop}:\n  Enabled: true\n" for cop in cops)
    (project / ".rubocop.yml").write_text(
        f"AllCops:\n  DisabledByDefault: true\n{enabled}", encoding="utf-8"
    )


def test_a_clean_file_is_a_clean_run(tmp_path: Path, rubocop: str) -> None:
    _configure(tmp_path, "Metrics/ParameterLists")
    (tmp_path / "clean.rb").write_text("def add(a, b)\n  a + b\nend\n", encoding="utf-8")

    result = _run(tmp_path, rubocop, "clean.rb")

    assert result.returncode == 0
    assert json.loads(result.stdout) == []


def test_real_offenses_reach_their_canonical_smells(tmp_path: Path, rubocop: str) -> None:
    """Two cops the plugin maps, fired by one fixture, through the real tool."""
    _configure(tmp_path, "Metrics/ParameterLists", "Lint/UselessAssignment")
    (tmp_path / "billing.rb").write_text(
        "def charge(a, b, c, d, e, f, g)\n  unused = 1\n  a + b\nend\n", encoding="utf-8"
    )

    result = _run(tmp_path, rubocop, "billing.rb")

    assert result.returncode == 0
    found = json.loads(result.stdout)
    assert {finding["smell"] for finding in found} == {
        "too-many-parameters",
        "unused-variable",
    }
    assert {finding["issues"][0]["details"]["source"] for finding in found} == {
        "rubocop:Metrics/ParameterLists",
        "rubocop:Lint/UselessAssignment",
    }


def test_a_syntax_error_is_a_parse_error(tmp_path: Path, rubocop: str) -> None:
    """`Lint/Syntax` is reported whatever the config enables. RuboCop cannot
    run a cop over source it could not parse, so it says so instead. That makes
    unparseable Ruby a *finding*, not a crashed sensor."""
    _configure(tmp_path, "Metrics/ParameterLists")
    (tmp_path / "broken.rb").write_text("def broken(\n", encoding="utf-8")

    result = _run(tmp_path, rubocop, "broken.rb")

    assert result.returncode == 0
    [finding] = json.loads(result.stdout)
    assert finding["smell"] == "parse-error"
    assert finding["issues"][0]["details"]["source"] == "rubocop:Lint/Syntax"


def test_an_unmapped_cop_arrives_under_its_own_name(tmp_path: Path, rubocop: str) -> None:
    """The forwarding half, proven against the real tool: a cop this plugin has
    no smell for still reaches the run, because the project enabled it."""
    _configure(tmp_path, "Style/FrozenStringLiteralComment")
    (tmp_path / "app.rb").write_text("puts 'hi'\n", encoding="utf-8")

    result = _run(tmp_path, rubocop, "app.rb")

    assert result.returncode == 0
    [finding] = json.loads(result.stdout)
    assert finding["smell"] == "Style/FrozenStringLiteralComment"


def test_no_files_never_lets_rubocop_scan_the_tree(tmp_path: Path, rubocop: str) -> None:
    """An empty scope measured nothing. A bare `rubocop` scans the whole current
    directory, so without the guard a docs-only change reports every legacy
    smell in the repository and fails the run (#93)."""
    _configure(tmp_path, "Metrics/ParameterLists")
    (tmp_path / "legacy.rb").write_text(
        "def charge(a, b, c, d, e, f, g)\n  a\nend\n", encoding="utf-8"
    )

    result = _run(tmp_path, rubocop)

    assert result.returncode == 0
    assert json.loads(result.stdout) == []


def test_the_projects_own_exclusions_are_honoured(tmp_path: Path, rubocop: str) -> None:
    """`--force-exclusion` is what keeps a project's `AllCops: Exclude:` meaning
    something once habit-hooks names files explicitly. Without it RuboCop treats
    a named file as a deliberate request and lints it anyway, so a project's
    config would quietly stop applying the moment this tool ran it."""
    (tmp_path / ".rubocop.yml").write_text(
        "AllCops:\n"
        "  DisabledByDefault: true\n"
        "  Exclude:\n"
        "    - 'generated/**/*'\n"
        "Metrics/ParameterLists:\n"
        "  Enabled: true\n",
        encoding="utf-8",
    )
    (tmp_path / "generated").mkdir()
    (tmp_path / "generated" / "schema.rb").write_text(
        "def charge(a, b, c, d, e, f, g)\n  a\nend\n", encoding="utf-8"
    )

    result = _run(tmp_path, rubocop, "generated/schema.rb")

    assert result.returncode == 0
    assert json.loads(result.stdout) == []


def test_a_filename_beginning_with_a_dash_is_a_file_not_an_option(
    tmp_path: Path, rubocop: str
) -> None:
    """`--` ends RuboCop's option parsing before the files are named, so a
    valid filename beginning with `-` is inspected rather than read as flags.
    Without it `-charge.rb` is short options — `-c` among them, which takes the
    rest as its `--config` value — and the file is never inspected at all.

    `plain.rb` is the file that proves the discrimination: it is never named,
    so any spelling that left RuboCop scanning the directory would report it
    too.
    """
    _configure(tmp_path, "Metrics/ParameterLists")
    offence = "def charge(a, b, c, d, e, f, g)\n  a\nend\n"
    (tmp_path / "-charge.rb").write_text(offence, encoding="utf-8")
    (tmp_path / "plain.rb").write_text(offence, encoding="utf-8")

    result = _run(tmp_path, rubocop, "-charge.rb")

    assert result.returncode == 0, result.stderr
    [finding] = json.loads(result.stdout)
    assert [issue["key"] for issue in finding["issues"]] == ["-charge.rb"]


@A_FILESYSTEM_THAT_ALLOWS_A_STAR_IN_A_FILENAME
def test_a_literal_star_in_a_filename_is_not_a_glob(
    tmp_path: Path, rubocop: str
) -> None:
    """A `*` in a scope filename is a character in a name, never a pattern.
    RuboCop hands any argument containing a `*` to `Dir[]`, so unescaped,
    `star*.rb` sweeps in `star2.rb` as well — a file the scope never named,
    reported as though it had. Escaped, RuboCop inspects the file it was given
    and only it.
    """
    _configure(tmp_path, "Metrics/ParameterLists")
    offence = "def charge(a, b, c, d, e, f, g)\n  a\nend\n"
    (tmp_path / "star*.rb").write_text(offence, encoding="utf-8")
    (tmp_path / "star2.rb").write_text(offence, encoding="utf-8")

    result = _run(tmp_path, rubocop, "star*.rb")

    assert result.returncode == 0, result.stderr
    [finding] = json.loads(result.stdout)
    assert [issue["key"] for issue in finding["issues"]] == ["star*.rb"]
