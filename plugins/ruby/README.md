# habit-hooks-ruby

The Ruby Habit Hooks plugin: wraps [`rubocop`](https://rubocop.org/) for
code-smell detection. Instead of a bare offence, each finding is
coached by listing the smell, guide for fixing, then a list of file locations.
This causes the agent to focus on fixing the smell rather than the metric.

```text
── high-complexity (1 issue) ──

High cyclomatic complexity means one function makes too many decisions at once. The count is the symptom; tangled responsibilities are the cause.

**Untangle the decisions:**
1. Lift guards out first — turn precondition checks into early returns so the happy path stays flat. Much of the count is preconditions wrapped around the real work.
2. Change the shape of what remains: an `if`/`else` chain switching on one value is often a lookup table or polymorphism in disguise; a nested loop is often a filter/map pipeline.
3. If the branches are genuinely separate jobs, extract one function per branch, each named for the responsibility it handles.

Useful tip: describe each branch in one sentence. Two branches with the same sentence belong together; a branch you cannot name cleanly wants its own function.

**AVOID**: merging conditions with and/or, or rewriting branches as ternaries, just to lower the score — the decisions remain, only the counter moves. You are done when a first-time reader can hold the whole function in their head.

app/services/billing.rb:6
```

# Setup

The steps are:

1. Install the plugin.
2. Enable it in your `.habit-hooks/config.toml`.
3. Make sure you have rubocop installed.
4. Make sure your `.rubocop.yml` enables the cops you want to see.

## Install the plugin

```sh
uv tool install "habit-hooks[ruby]"   # pip and pipx work too
```

Or let setup do it: with habit-hooks already installed, `habit-hooks init` in your
project detects ruby, names this plugin in `.habit-hooks/config.toml`, and offers to
run the install for you — see the [Habit-Hooks README #install](https://github.com/habit-hooks/habit-hooks#install).

## Enable the plugin

Installing a plugin does not switch it on — it has to be named in
`plugins` before habit-hooks runs it.

```toml
# .habit-hooks/config.toml
plugins = ["ruby", "generic"]
```

Keep `generic` in the list. Most of the smells this plugin reports are coached
by guides `generic` ships; without it they fall back to a short generic prompt.

## Sensors: install rubocop

The ruby plugin supports the rubocop sensor. It can use any rubocop on your `PATH`, but it is best to point it at the one your project uses. 

Point it at your project's own rubocop:

**If your `Gemfile` pins rubocop, or your `.rubocop.yml` names an extension gem
(`rubocop-rails`, `rubocop-rspec`, `rubocop-performance`), generate binstubs:**

```sh
bundle binstubs rubocop
```

Otherwise, if you have no rubocop yet, install one:

- `rubocop` — `gem install rubocop`

### How it finds rubocop

habit-hooks' rubocop detector searches your project's `bin/` ahead of the
machine's `PATH`, so `bin/rubocop` is what it will run — under your bundle,
with your extension gems loaded.

Without this, habit-hooks runs whatever `rubocop` your `PATH` answers with, and
a config naming cops that rubocop cannot load is a hard error rather than a
lint result:

```
Error: `Rails/*` has been extracted to the `rubocop-rails` gem.
```

habit-hooks reports that as a failed run.

### Configure your `.rubocop.yml`

The sensor runs `rubocop` and reads what comes back.  RuboCop discovers your `.rubocop.yml`
exactly as it does when you run rubocop by hand.  The `--force-exclusion` is the one flag
habit-hooks adds, so your `AllCops: Exclude:` keeps applying even though habit-hooks names files
explicitly.

Cops are mapped to canonical smells and are reported under it:

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

All other cops are **forwarded under their own name** by default.
Recommended: add coaches for cops as needed (see [Customization](#customization)).
Set the root `uncoached` key to `ignore` to drop these cops,
or `enforce` to fail the run on them 
([config.md](https://github.com/habit-hooks/habit-hooks/blob/main/docs/config.md)).

#### A starting `.rubocop.yml`

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

# Customization

Ruby Habit Hooks is customizable without modifying the installed package. Project
files under `.habit-hooks/ruby/` override the corresponding files shipped by the
Ruby plugin. Commit these overrides if they are intended to apply to the whole
project.

## Add project-specific coaching

Replace any Ruby guide by creating a file with the same name under
`.habit-hooks/ruby/guides/`. For example,
`.habit-hooks/ruby/guides/high-complexity.md` replaces the default coaching for
the `high-complexity` smell while leaving all other guides unchanged.


An unmapped cop forwarded under its own name can use a custom filename through the project
config:

```toml
[smells."Style/StringLiterals"]
guide = "style-string-literals.md"
```

Then add a guide at `.habit-hooks/ruby/guides/style-string-literals.md`. For example:

```markdown
Use the quote style established by this project. preserve interpolation and readability.

{% for issue in issues -%}
{{ issue.details.file }}:{{ issue.details.line }}
{% endfor %}
```

Guides are Markdown Jinja templates. They can use `smell` and `language`, read
smell-level `details`, and loop over `issues` to show each offense.  The loop in
the example above writes the file and line of each issue (required, otherwise the
agent will not know where the offense occurred).

## Add a cop-to-smell mapping

Prefer mapping a cop to an existing general smell when the guidance fits. This
lets the project benefit from shared coaching and keeps the smell vocabulary
small. If the cop represents a smell that should be useful beyond your project,
consider contributing the mapping, guide, and any needed vocabulary changes in
a pull request to the [Habit Hooks project](https://github.com/habit-hooks/habit-hooks).

The built-in cop mappings live in `sensors/rubocop_report.py`, in the
`COP_SMELLS` table.

To add a mapping for a project, copy that file to
`.habit-hooks/ruby/sensors/rubocop_report.py` and add an entry, for example:

```python
COP_SMELLS = {
    # existing mappings ...
    "Style/StringLiterals": "project-style",
}
```

Because the sensor helper imports this file from its own directory, also copy
`rubocop_sensor.py` and `rubocop.toml` to the same override directory (.habit-hooks/ruby/sensors).
Keep the recipe in the TOML file the same; its `${dir}` then points at the override and
loads your customized report module.

If the new mapping uses an existing smell, its existing guide and severity are
used. For a new smell, add a guide and configure its severity as needed:

```toml
[smells.project-style]
severity = "suggested"
```

Then add `.habit-hooks/ruby/guides/project-style.md`.

## Add or replace a sensor

A sensor is a TOML recipe under `sensors/`. To replace the RuboCop sensor,
override `.habit-hooks/ruby/sensors/rubocop.toml`; to add a separate sensor,
create a new recipe such as `.habit-hooks/ruby/sensors/custom-check.toml` and
add its name to the Ruby plugin's `sensors` list in
`.habit-hooks/ruby/config.toml`:

```toml
sensors = ["rubocop", "custom-check"]
```

The plugin config override is a complete replacement, so copy the shipped
Ruby `config.toml` and preserve its `language`, `files`, `transformers`, and
`detectors` entries when adding a sensor. Declare every external command the
sensor uses in `detectors`, and use `${detector:<name>}` in its recipe when the
sensor invokes that command.

The sensor must print a JSON array of Habit Hooks findings. See the
[sensor interface](https://github.com/habit-hooks/habit-hooks/blob/main/docs/sensor-interface.spec.md)
for the finding shape and available recipe placeholders.

For example, a simple custom sensor returning a canned finding to demonstrate the customization.

- Create
`.habit-hooks/ruby/sensors/custom-check.toml`:

```toml
command = "${dir}/custom-check.sh"
```

- Then create the executable `.habit-hooks/ruby/sensors/custom-check.sh`:

```sh
#!/bin/sh
printf '%s\n' '[{"smell":"custom-check","details":{},"issues":[{"key":"app/models/example.rb","details":{"file":"app/models/example.rb","line":1,"message":"Canned custom-check result","source":"custom-check"}}]}]'
```

The sensor's issue paths should be relative to the project, and its
output must always be a JSON array of findings.

- Enable it by copying the entire `plugins/ruby/src/habit_hooks_ruby/config.toml` to `.habit-hooks/ruby/config.toml` and adding `"custom-check"` to the `sensors` list in the plugin config
override. for example:
```
sensors = ["rubocop", "custom-check"]  
```
