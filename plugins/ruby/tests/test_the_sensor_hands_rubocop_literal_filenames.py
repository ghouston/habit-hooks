"""How the sensor spells the filenames it hands RuboCop.

RuboCop reads a file argument twice over, and both readings are wrong for an
exact scope filename. As *options*: a filename beginning with ``-`` is parsed as
short flags, ``-c`` among them, which takes the rest as its ``--config`` value.
As a *pattern*: an argument containing a ``*`` is handed to ``Dir[]``
(``TargetFinder#process_explicit_path``), so a literal star sweeps in every file
it matches. The argv fixes both: ``--`` ends option parsing before any file is
named, and a star is escaped with the backslash ``Dir[]`` reads as "this
character, literally".

These are the argv and spelling halves, answered without a subprocess so they
run on every platform. What RuboCop makes of the spelled argv is proven against
the real tool in ``test_the_rubocop_sensor_runs_the_real_tool``, whose
literal-star case runs only where the filesystem can hold such a name at all.
"""

from __future__ import annotations

import subprocess

import pytest

import rubocop_sensor
from rubocop_sensor import literal_spelling_of


@pytest.fixture
def argv_handed_to_rubocop(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Every argv ``run_rubocop`` would spawn, standing in for the spawn.

    The completed process it answers with is a report RuboCop never wrote but
    one of the shape it writes, so a caller that goes on to parse it is not
    interrupted for the stand-in's sake.
    """
    spawns: list[list[str]] = []

    def record(argv: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        spawns.append(argv)
        return subprocess.CompletedProcess(argv, 0, '{"files": []}', "")

    monkeypatch.setattr(rubocop_sensor.subprocess, "run", record)
    return spawns


def test_option_parsing_ends_before_the_files_are_named(
    argv_handed_to_rubocop: list[list[str]],
) -> None:
    """`--` sits between RuboCop's flags and the files, so `-charge.rb` is never
    read as one. A filename beginning with a dash is a valid name on every
    platform this tool runs on; only the argument list has to say which it is."""
    rubocop_sensor.run_rubocop("rubocop-file", ["-charge.rb", "plain.rb"])

    assert argv_handed_to_rubocop == [
        [
            "rubocop-file",
            "--format",
            "json",
            "--force-exclusion",
            "--",
            "-charge.rb",
            "plain.rb",
        ]
    ]


def test_a_filename_without_a_star_is_spelled_as_it_is() -> None:
    """The common case passes through untouched, byte for byte."""
    assert literal_spelling_of("app/billing.rb") == "app/billing.rb"


def test_a_star_is_escaped_so_the_name_stays_a_name() -> None:
    """`star\\*.rb` is glob syntax for the literal `star*.rb`, which `Dir[]`
    honours — and RuboCop still globs the argument, because the escaped string
    contains a `*` too."""
    assert literal_spelling_of("star*.rb") == "star\\*.rb"


def test_a_backslash_inside_a_starred_argument_is_doubled() -> None:
    """`Dir[]` reads a backslash as its own escape, so a starred name holding
    one must double it: `a\\\\\\*b.rb` is the pattern for the literal
    `a\\*b.rb`. Left single, the backslash would escape the `*` instead of
    standing for itself, so the pattern would name the literal `a*b.rb` — a
    different file — and the one in the scope would never be scanned.
    Without a star the same backslash stays as it is, byte for byte."""
    assert literal_spelling_of("a\\*b.rb") == "a\\\\\\*b.rb"
    assert literal_spelling_of("a\\b.rb") == "a\\b.rb"


def test_the_other_metacharacters_are_escaped_only_inside_a_starred_argument() -> None:
    """A `?` on its own must not be escaped. RuboCop globs only an argument
    containing a `*`; every other one it takes verbatim, backslashes included,
    so `a\\?b.rb` names a file that does not exist and the run dies on
    `Error: No such file or directory`. Inside a starred argument the escape is
    needed — there the `?` would otherwise match any character — and safe,
    because `Dir[]` is reading the whole thing as a pattern."""
    assert literal_spelling_of("a?b.rb") == "a?b.rb"
    assert literal_spelling_of("a*b?c[d.rb") == "a\\*b\\?c\\[d.rb"
