"""Run RuboCop and print canonical findings, mapped from cop name to smell.

**Which cops run is the project's business, not ours.** The sensor passes no
``--only`` and no ``--config``. RuboCop finds ``.rubocop.yml`` by walking up from
each inspected file, exactly as it does when run by hand, so a project's habit-
hooks run is the run it gets from the tool directly. ``--force-exclusion`` is the
one flag that keeps that true. Without it, naming files on the command line
overrides the project's own ``AllCops: Exclude:``.

Parsing and shaping live next door in ``rubocop_report``, a neighbour imported
as a top-level module because a helper runs as a loose script — the interpreter
puts the helper's own directory first on ``sys.path`` (CLAUDE.md, "A plugin
helper imports its neighbours as top-level modules").

The plugin ships no RuboCop of its own, so the sensor names ``${detector:rubocop}``
and its ``sys.argv[1]`` is the file this project runs for it, and the scoped
files follow. A rubocop nobody installed never reaches here at all. The part
has no file for it, so the run answers with the missing-command notice before
anything is spawned.

**A scope filename is a name, never an option or a pattern.** RuboCop reads its
file arguments both ways, and the argv guards each: ``--`` ends option parsing
before any file is named, and :func:`literal_spelling_of` escapes the glob
metacharacters RuboCop would otherwise expand.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

from rubocop_report import findings, offenses, report

# RuboCop's own contract: 0 is clean, 1 is "offences found". Anything else
# means RuboCop never produced a real report, the same distinction
# `part_output.py`'s TOOL_EXIT_CODES draws for a part run directly.
#
# The exit code alone is not enough here, which is a Ruby problem rather than a
# RuboCop one. `rubocop` is a RubyGems binstub with a `#!/usr/bin/env ruby`
# shebang, so it is only as good as the `ruby` that answers first. Point it at
# an interpreter whose gems it is not installed into, whether a version
# manager left off PATH, the wrong bundle, or macOS's system Ruby 2.6, and it
# dies in `find_spec_for_exe` with a Ruby traceback and **exit 1**, the code
# reserved for "I found offences". Trusting that would report a rubocop that
# never started as a clean file (#88).
#
# So the report is the evidence, not the code. `--format json` prints the
# envelope on every run RuboCop actually completed, down to `"files": []` when
# it inspected nothing. No report means no run.
TOOL_EXIT_CODES = (0, 1)

# The characters `Dir[]` reads as a pattern rather than a name. RuboCop hands
# an argument to `Dir[]` only when it contains a `*` (see
# `literal_spelling_of`), so these matter only inside an argument that does.
_GLOB_METACHARACTERS = re.compile(r"[*?\[\]{}\\]")


def literal_spelling_of(path: str) -> str:
    """A scope filename spelled so RuboCop reads it as the file it names.

    RuboCop globs any argument containing a ``*`` —
    ``TargetFinder#process_explicit_path`` passes it to ``Dir[]`` — so a
    literal star would sweep in every file it matches. A backslash is ``Dir[]``'s
    own escape for "this character, literally", which leaves the escaped
    string still containing a ``*`` for RuboCop to notice and hand to ``Dir[]``
    in the first place.

    The other metacharacters are escaped only inside such an argument. A path
    without a ``*`` RuboCop takes verbatim, backslashes included, so escaping a
    ``?`` there would name a file that does not exist and the run would die on
    ``Error: No such file or directory``.
    """
    if "*" not in path:
        return path
    return _GLOB_METACHARACTERS.sub(r"\\\g<0>", path)


def run_rubocop(rubocop: str, files: list[str]) -> subprocess.CompletedProcess[str]:
    """What RuboCop said, spawned as the file this sensor was handed for it.

    The file rather than the name. A name would be looked up again by the
    spawn, and Windows' own lookup adds ``.exe`` and nothing else, where
    RubyGems installs a ``.bat`` shim.

    ``--force-exclusion`` is not a nicety. RuboCop applies ``AllCops: Exclude:``
    to the files it discovers, but a file named explicitly on the command line
    is taken as a deliberate request and linted anyway. Without it, a
    project's own exclusions stop meaning anything the moment habit-hooks passes
    a scope.

    ``--`` ends option parsing before the files, so a valid filename beginning
    with ``-`` is a file rather than a pile of short options — ``-c`` among them,
    which takes the rest as its ``--config`` value.
    """
    return subprocess.run(
        [
            rubocop,
            "--format",
            "json",
            "--force-exclusion",
            "--",
            *[literal_spelling_of(file) for file in files],
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",  # sensors.spawn's policy
    )


def rubocop_crashed(
    result: subprocess.CompletedProcess[str], parsed: dict | None
) -> bool:
    """Whether this run is one whose answer can be believed.

    Both halves are needed. The exit code catches the failures RuboCop reports
    as failures; the missing report catches the one it cannot: a binstub that
    never reached RuboCop at all, which exits 1 like a run full of offences
    (see :data:`TOOL_EXIT_CODES`).

    The report is passed in rather than parsed here so that this is the only
    place the rule is written. :func:`main` needs the parsed report anyway, and
    a version of this that re-derived it would be a second copy of the decision,
    free to drift from the one the tests exercise.
    """
    return result.returncode not in TOOL_EXIT_CODES or parsed is None


def main() -> int:
    rubocop = sys.argv[1]
    files = sys.argv[2:]
    # A scope that resolved to nothing measured nothing, and RuboCop handed no
    # paths falls back to its own default and scans everything under the
    # current directory. Without this guard a docs-only change reports every
    # legacy smell in the tree and fails the run (#93).
    if not files:
        print("[]")
        return 0
    result = run_rubocop(rubocop, files)
    parsed = report(result)
    if rubocop_crashed(result, parsed):
        # `or result.stdout`: a binstub that could not find its own gem writes
        # its traceback to stderr, but a RuboCop that failed on the config
        # writes `Error: ...` to stdout. Whichever one it is, the tool's own
        # words are the only thing the reader can act on.
        sys.stderr.write(result.stderr or result.stdout)
        return 2
    print(json.dumps(findings(offenses(parsed))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
