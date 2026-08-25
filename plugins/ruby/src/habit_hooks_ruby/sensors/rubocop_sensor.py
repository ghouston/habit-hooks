"""Run RuboCop and print canonical findings, mapped from cop name to smell.

RuboCop's own JSON nests offences under each file; this flattens them, groups by
smell and shapes each into the canonical finding.

**Which cops run is the project's business, not ours.** The sensor passes no
``--only`` and no ``--config``. RuboCop finds ``.rubocop.yml`` by walking up from
each inspected file, exactly as it does when run by hand, so a project's habit-
hooks run is the run it gets from the tool directly. ``--force-exclusion`` is the
one flag that keeps that true. Without it, naming files on the command line
overrides the project's own ``AllCops: Exclude:``.

**An unmapped cop is forwarded, not dropped**, which is the opposite of the knip
sensor and the same as the eslint one. CLAUDE.md's test for a wrapped tool is
"whose vocabulary is it?" Knip's key set is knip's own, but a cop that fired is
one the project's ``.rubocop.yml`` turned on, so forwarding it saves running
RuboCop separately. Its smell key is the cop name verbatim
(``Style/StringLiterals``). A ``/`` in a smell key is already precedented by
eslint forwarding ``@typescript-eslint/no-explicit-any``. Nothing downstream
breaks on one. An uncatalogued smell renders through ``uncoached.md``, and the
root ``uncoached`` key (default ``suggest``) decides whether it fails the run.

``Metrics/ClassLength`` and ``Metrics/ModuleLength`` are the two cops
deliberately unmapped and forwarded like anything else. They are the wrong
shape, not a duplicate: they measure a class or module, never a file, so
neither can back a file-scoped smell, and ``oversized-file`` comes from the
generic ``line-count`` sensor instead, as it does for python and php.

The three complexity cops share one smell on purpose. They are correlated but
independent. A method tripping two cops keeps both measurements inside a single coaching
block.

``Metrics/BlockLength`` maps to its own smell rather than to
``oversized-function``: a block is an anonymous function the project never
named, and its coaching (name the work as a method, let the declaration point
at it) differs enough from a method's to warrant the ruby plugin's own guide.

The plugin ships no RuboCop of its own, so the sensor names ``${detector:rubocop}``
and its ``sys.argv[1]`` is the file this project runs for it, and the scoped
files follow. A rubocop nobody installed never reaches here at all. The part
has no file for it, so the run answers with the missing-command notice before
anything is spawned.
"""

from __future__ import annotations

import json
import subprocess
import sys

COP_SMELLS = {
    "Metrics/ParameterLists": "too-many-parameters",
    "Metrics/MethodLength": "oversized-function",
    "Metrics/BlockLength": "oversized-block",
    "Metrics/CyclomaticComplexity": "high-complexity",
    "Metrics/PerceivedComplexity": "high-complexity",
    "Metrics/AbcSize": "high-complexity",
    "Metrics/BlockNesting": "deep-nesting",
    "Lint/UselessAssignment": "unused-variable",
    "Lint/SuppressedException": "swallowed-exception",
    "Lint/Syntax": "parse-error",
}

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
    """
    return subprocess.run(
        [rubocop, "--format", "json", "--force-exclusion", *files],
        capture_output=True,
        encoding="utf-8",
        errors="replace",  # sensors.spawn's policy
    )


def report(result: subprocess.CompletedProcess[str]) -> dict | None:
    """RuboCop's JSON report, or ``None`` where it produced none.

    ``files`` has to be there, not merely valid JSON. That key is what makes it
    a report rather than something else that happens to parse.
    """
    text = result.stdout.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) and "files" in parsed else None


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


def offenses(parsed: dict) -> list[dict]:
    """RuboCop's per-file nesting flattened, each offence carrying its path."""
    return [
        {"file": entry["path"], "offense": offense}
        for entry in parsed.get("files", [])
        for offense in entry["offenses"]
    ]


def smell_of(cop_name: str) -> str:
    """This plugin's smell for a cop, or the cop itself where it has none.

    ``.get`` with the cop as its own default, never a bare lookup. The string
    comes from RuboCop and nothing constrains it to the table above (issue #83).
    """
    return COP_SMELLS.get(cop_name, cop_name)


def issue(entry: dict) -> dict:
    offense = entry["offense"]
    return {
        "key": entry["file"],
        "details": {
            "file": entry["file"],
            "line": offense["location"]["line"],
            "column": offense["location"]["column"],
            "message": offense["message"],
            "source": "rubocop:" + offense["cop_name"],
        },
    }


def findings(entries: list[dict]) -> list[dict]:
    by_smell: dict[str, list[dict]] = {}
    for entry in entries:
        by_smell.setdefault(smell_of(entry["offense"]["cop_name"]), []).append(entry)
    return [
        {
            "smell": smell,
            "details": {},
            "issues": [issue(entry) for entry in by_smell[smell]],
        }
        for smell in sorted(by_smell)
    ]


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
