# habit-hooks-ruby notes

## Architecture

### The project's `.rubocop.yml` decides everything

The sensor passes no `--only` and no `--config`. RuboCop finds the project's
config by its own upward walk, so a project's habit-hooks run is the run it gets
from RuboCop directly. There is no shipped fallback config, and the plugin never
writes one into a project. The README carries a suggested `.rubocop.yml` as
documentation only — unlike jscpd or pmd, RuboCop's config already exists in
almost every real Ruby project, so this plugin has no fallback case to cover.

`--force-exclusion` is the one flag the sensor adds, and it is not optional.
RuboCop applies `AllCops: Exclude:` to the files it *discovers*, but treats a
file named on the command line as a deliberate request and lints it anyway.
Since habit-hooks always names a scope, without that flag a project's own
exclusions would stop meaning anything the moment this tool ran.

### An unmapped cop is forwarded, not dropped

This is the same exception to "a sensor emits vocabulary smells only" that the
root `CLAUDE.md` makes for eslint: a cop that fired is one the project's own
`.rubocop.yml` turned on, so forwarding it forwards the project's own decision.

The smell key is the cop name verbatim, `Style/StringLiterals`. Nothing downstream breaks on one: the
guide lookup misses, the finding renders through `uncoached.md`, and the root
`uncoached` key (default `suggest`) decides whether it fails the run.

Two cops are unmapped **on purpose** rather than by omission, so do not "fix"
them by adding rows. `Metrics/ClassLength` and `Metrics/ModuleLength` measure a
class or module, and the vocabulary has no class-scoped smell for them to back.
They stay **uncoached** — forwarded under their own names, rendered through
`uncoached.md`, `suggest` until a class and module scoped coach exists.

The three complexity cops all map to `high-complexity` (human decision). They
are correlated but independent — `PerceivedComplexity` weights nesting and
`AbcSize` counts assignments and calls, so either fires without
`CyclomaticComplexity` — and an unmapped complexity cop coached a genuinely
tangled method through `uncoached.md` when the real guide applied verbatim. The
old objection, one method reported three times over, is dissolved by the
mapper: this sensor groups every cop that fired on a smell into one finding's
issue list, which is never deduped (issue #140), so a method tripping two cops
keeps both measurements inside a single coaching block.

## Gotchas

### RuboCop reads a file argument as options, then as a glob

A scope filename is exact, and RuboCop reads its file arguments two other ways
before it reads them as names. A filename beginning with `-` is parsed as short
options — `-c` among them, which takes the rest as its `--config` value — and an
argument containing a `*` is handed to `Dir[]`
(`TargetFinder#process_explicit_path`), so a literal star sweeps in every file
it matches. `run_rubocop` therefore puts `--` between its flags and the files,
and `literal_spelling_of` escapes the glob metacharacters.

The escaping is narrower than it looks, and has to be. RuboCop globs only an
argument containing a `*`; every other one it takes verbatim, backslashes
included, so escaping a `?` in a starless path would name a file that does not
exist and the run would die on `Error: No such file or directory`. The other
metacharacters are escaped only inside a starred argument, where `Dir[]` is
reading the whole thing as a pattern. The literal-star behavioural test runs
only where a filesystem allows a `*` in a name — Windows forbids it — so it
skips there through
`tests/platform_probe.A_FILESYSTEM_THAT_ALLOWS_A_STAR_IN_A_FILENAME`.

### RuboCop's exit code lies when the binstub never reached RuboCop

`ruff_sensor` can trust ruff's exit code. `rubocop` is a RubyGems
binstub beginning `#!/usr/bin/env ruby`, so it is only as good as the `ruby`
that answers first. Point it at an interpreter it is not installed into (a
version manager left off `PATH`, the wrong bundle, macOS's system Ruby 2.6) and
it dies in `find_spec_for_exe` with a Ruby traceback and **exit 1** — the code
reserved for "I found offences". Judged on the code alone, that is a clean file
from a tool that never started, which is the false-clean class issue #88 exists
for.

So the report is the evidence, not the code. `--format json` prints its envelope
on every run RuboCop completed, down to `"files": []` when it inspected nothing,
so no envelope means no run whatever it exited with. `report()` answers `None`
for anything that is not a report, and it requires the `files` key rather than
merely valid JSON. `rubocop_crashed()` takes the parsed report as an argument
instead of re-deriving it, so the rule lives in one place and `main` cannot
drift from what the tests exercise.

Ask this of any wrapped tool reached through an interpreter shim rather than a
binary. The cost of getting it wrong is silence, and silence reads as success.

`tests/test_the_sensor_runs_the_rubocop_it_is_handed.py` has to hand `ruby` back
on a directory of its own for the same reason. The binstub and its interpreter
live in one directory, so taking `rubocop` off `PATH` takes `ruby` with it, and
the test would then be proving the crash rather than the lookup.

### RuboCop globs every ancestor directory looking for a gemspec

`TargetRuby` settles which Ruby to parse as by trying, in order,
`TargetRubyVersion` in the config, then any `*.gemspec`, then `.ruby-version`.
The gemspec step is a `Dir.glob` up every ancestor directory to the filesystem
root, and **`.ruby-version` does not prevent it**, because RuboCop looks for the
gemspec first. A Rails app, which has no gemspec, therefore sends RuboCop
climbing out of the project on every run. A gem stops the climb by having a
gemspec; everything else stops it by pinning `TargetRubyVersion`.

That is RuboCop's own behaviour and the sensor reproduces it rather than
papering over it, per the precedence rule in the root `CLAUDE.md`. It matters
for the tests because the spec harness runs each case in
`<repo>/.spec-runs/tmpXXXX/`: a case pinning neither climbs through this
checkout and out into the home directory, where a sandboxed dev machine denies
the glob outright and the sensor fails for a reason that has nothing to do with
the case. Every case in `docs/ruby-plugin.spec.md` and
`tests/installed_projects.ruby_project` pins `TargetRubyVersion`.

It is the RuboCop counterpart of the root `CLAUDE.md`'s `GIT_CEILING_DIRECTORIES`
rule and of jscpd's `.gitignore` walk: a wrapped tool that searches upward has
to be given a floor, or it finds ours.

### A Rails project's rubocop is the only one that can read its config

A `.rubocop.yml` naming cops from an extension gem is a hard RuboCop error when
that gem is not loadable:

```
Error: `Rails/*` has been extracted to the `rubocop-rails` gem.
```

Nearly every Rails repo pins rubocop plus `rubocop-rails` / `rubocop-rspec` /
`rubocop-performance` in its `Gemfile`, and those gems load only under the
project's own bundle. This is the likeliest way the sensor fails in practice,
and it is why `<project>/bin` was added to `project_paths.tool_search_path`:
`bundle binstubs rubocop` writes `bin/rubocop`, and habit-hooks looks there
before the machine's `PATH`.

The lookup belongs in `project_paths` and not in this sensor. `missing_tools`
clears a tool by asking `tool_executable`, and `sensors/spawn.py` spawns the
file it answered with, so a second answer here would let setup clear a rubocop
the run then does not use. `bin` ranks *after* `node_modules/.bin` and
`.venv/bin` because it is the least specific of the three: those two can hold
nothing else, where a `bin` may hold a project's own scripts.

## Testing

`tests/conftest.py` puts `src/habit_hooks_ruby/sensors` on `sys.path` so the
helper loads as a loose top-level module, which is how
`${python} ${dir}/rubocop_sensor.py` loads it. Reaching it as
`habit_hooks_ruby.sensors.rubocop_sensor` is a path no run ever takes.

A missing rubocop is a `pytest.fail`, not a skip, matching every other plugin: a
machine without it is a suite that has quietly stopped gating, not a machine
this plugin does not apply to.

The split between `test_the_rubocop_pipeline_maps_cops_to_smells.py` and
`test_the_rubocop_sensor_runs_the_real_tool.py` is worth keeping. The first says
what RuboCop's output *becomes* and runs no subprocess; the second proves
RuboCop still produces output of the shape the first assumes. A RuboCop upgrade
that renames `cop_name` or restructures `location` fails the second alone, which
is the signal you want.
