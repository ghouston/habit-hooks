# habit-hooks-ruby

The Ruby Habit Hooks plugin: wraps [`rubocop`](https://rubocop.org/) for
structural code-smell detection. Instead of a bare offence, each finding is
coached by listing the smell, guide for fixing, then a list of matching offenses:

```text
── high-complexity (3 issues) ──

High complexity means one method makes too many decisions at once. RuboCop measures it three ways: cyclomatic counts branches, perceived weights nesting, AbcSize counts assignments and calls. One method can therefore be listed more than once below. The count is the symptom; tangled responsibilities are the cause.

**Untangle the decisions:**
1. Lift guards out first: turn precondition checks into early returns (`return unless ...`) so the happy path stays flat. Much of the count is preconditions wrapped around the real work.
2. Change the shape of what remains: an `if`/`elsif` chain switching on one value is often a hash lookup or polymorphism in disguise; a nested loop is often a `filter`/`map` pipeline.
3. If the branches are genuinely separate jobs, extract one method per branch, each named for the responsibility it handles.

Useful tip: describe each branch in one sentence. Two branches with the same sentence belong together; a branch you cannot name cleanly wants its own method.

Lower the decision count, not the metric: merged conditions and ternaries move the number while the decisions remain. You are done when a first-time reader can hold the whole method in their head.

app/services/billing.rb:14 rubocop:Metrics/CyclomaticComplexity
  Cyclomatic complexity for charge is too high. [12/7]
app/services/billing.rb:14 rubocop:Metrics/PerceivedComplexity
  Perceived complexity for charge is too high. [13/8]
app/services/billing.rb:14 rubocop:Metrics/AbcSize
  Assignment Branch Condition size for charge is too high. [38.4/20]
```

## Install

```sh
pip install "habit-hooks[ruby]"
```

## Enable

```toml
# .habit-hooks/config.toml
plugins = ["ruby"]
```

Installing a plugin does not switch it on — it has to be named in
`plugins` before habit-hooks runs it.

## Detectors

- `rubocop` — `gem install rubocop`

## Point it at your project's own rubocop

**If your `Gemfile` pins rubocop, or your `.rubocop.yml` names an extension gem
(`rubocop-rails`, `rubocop-rspec`, `rubocop-performance`), generate binstubs:**

```sh
bundle binstubs rubocop
```

habit-hooks looks along `bin/` before the machine's `PATH`, so `bin/rubocop` is
what it will run — under your bundle, with your extension gems loaded.

Without this, habit-hooks runs whatever `rubocop` your `PATH` answers with, and
a config naming cops that rubocop cannot load is a hard error rather than a
lint result:

```
Error: `Rails/*` has been extracted to the `rubocop-rails` gem.
```

habit-hooks reports that as a failed run rather than a clean one — a crashed
tool is never "no problems found" — but the fix is to give it the right rubocop.

## Your `.rubocop.yml` decides everything

The sensor runs `rubocop` and reads what comes back. It passes no `--only` and
no `--config`, so rubocop discovers your `.rubocop.yml` exactly as it does when
you run it by hand, and **your habit-hooks run is the run you get from rubocop
directly**. `--force-exclusion` is the one flag it adds, so your
`AllCops: Exclude:` keeps applying even though habit-hooks names files
explicitly.

Cops this plugin has a canonical smell for are reported under it:

| Cop | Smell |
|-----|-------|
| `Metrics/ParameterLists` | `too-many-parameters` |
| `Metrics/MethodLength` | `oversized-function` |
| `Metrics/BlockLength` | `oversized-block` |
| `Metrics/CyclomaticComplexity` | `high-complexity` |
| `Metrics/PerceivedComplexity` | `high-complexity` |
| `Metrics/AbcSize` | `high-complexity` |
| `Metrics/BlockNesting` | `deep-nesting` |
| `Lint/UselessAssignment` | `unused-variable` |
| `Lint/SuppressedException` | `swallowed-exception` |
| `Lint/Syntax` | `parse-error` |

Every other cop is **forwarded under its own name** — you turned it on, so you
get to see it. It coaches without failing the run; set the root `uncoached` key
to `ignore` to drop them, or `enforce` to fail on them
([config.md](https://github.com/habit-hooks/habit-hooks/blob/main/docs/config.md)).

## Findings the `generic` plugin adds

`habit-hooks init` writes `generic` into your `plugins` list alongside `ruby`,
so a generated setup also coaches two smells this plugin has no part in:

Drop `generic` from `plugins` if you would rather not see either.

- **`oversized-file`** — from generic's built-in line counter. Nothing to
  install or configure.
- **`duplicated-code`** — from generic's jscpd sensor. This one needs setup:
  jscpd itself (`npm install --save-dev jscpd`) and a `.jscpd.json` of your
  own, because its bundled config scans `src/` — a directory a Ruby project
  usually doesn't have.

### A starting `.rubocop.yml`

If you have no config yet, this turns on the structural cops this plugin maps
and nothing else. It is a suggestion, not a default. Habit-hooks never writes
it for you and never passes it to rubocop.

```yaml
AllCops:
  NewCops: enable
  Exclude:
    - 'db/schema.rb'
    - 'vendor/**/*'
    - 'tmp/**/*'

Metrics/ParameterLists:
  Max: 4
Metrics/MethodLength:
  Max: 20
Metrics/CyclomaticComplexity:
  Max: 10
Metrics/BlockNesting:
  Max: 3
Lint/UselessAssignment:
  Enabled: true
Lint/SuppressedException:
  Enabled: true
```

Part of [habit-hooks](https://github.com/habit-hooks/habit-hooks).
