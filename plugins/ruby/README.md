# habit-hooks-ruby

The Ruby Habit Hooks plugin: wraps [`rubocop`](https://rubocop.org/) for
structural code-smell detection.

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
and nothing else. It is a suggestion, not a default — habit-hooks never writes
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
