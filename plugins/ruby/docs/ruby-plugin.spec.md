# The ruby plugin: acceptance

The ruby plugin runs its sensor through the real `habit-sensors` pipeline. These
cases run the actual tool, RuboCop, against a fixture with a known smell, and
assert the canonical finding comes out mapped to the smell keys in
[smell-vocabulary.md](smell-vocabulary.md).

`habit-sensors` is the installed CLI and `rubocop` is on the system `PATH`. The
plugin declares `rubocop` as the one tool it needs, and the run resolves it to a
file before the sensor starts.

**The project decides which cops run.** The sensor passes no `--only` and no
`--config`, so RuboCop finds `.rubocop.yml` by its own upward walk, and a
project's habit-hooks run is the run it gets from RuboCop directly. Every case
below writes its own config, the way a real project has one. They set
`DisabledByDefault` so each case is about the cops it names rather than about
RuboCop's several hundred defaults.

They also set `TargetRubyVersion`, which is worth knowing about for reasons that
outlast these tests. RuboCop works out which Ruby to parse as by trying, in
order, `TargetRubyVersion` in the config, then any `*.gemspec`, then
`.ruby-version`. The gemspec step globs every ancestor directory, so a project
with no gemspec sends RuboCop climbing to the filesystem root on every run.
`.ruby-version` does not prevent that, because RuboCop looks for the gemspec
first. A gem stops the climb by having a gemspec; everything else, a Rails app
included, stops it by pinning `TargetRubyVersion`. Here it also keeps each case
inside its own directory instead of reading whatever sits above the checkout.

📄.habit-hooks/config.toml
```toml
plugins = ["ruby"]
```

## rubocop sensor maps cop names to canonical smells

The sensor shapes each offence into one finding per smell and stamps
`source: "rubocop:<cop>"` on every issue. A seven-parameter method trips
`Metrics/ParameterLists`, which maps to `too-many-parameters`. Its dead local
trips `Lint/UselessAssignment`, which maps to `unused-variable`.

📄.rubocop.yml
```yaml
AllCops:
  DisabledByDefault: true
  TargetRubyVersion: 3.1
Metrics/ParameterLists:
  Enabled: true
Lint/UselessAssignment:
  Enabled: true
```

📄billing.rb
```ruby
def charge(a, b, c, d, e, f, g)
  unused = 1
  a + b + c
end
```

```bash
habit-sensors --all | jq 'sort_by(.smell)[] | {smell, language, key: .issues[0].key, line: .issues[0].details.line, source: .issues[0].details.source}'
```

🖥️ ✅
```json
{
  "smell": "too-many-parameters",
  "language": "ruby",
  "key": "billing.rb",
  "line": 1,
  "source": "rubocop:Metrics/ParameterLists"
}
{
  "smell": "unused-variable",
  "language": "ruby",
  "key": "billing.rb",
  "line": 2,
  "source": "rubocop:Lint/UselessAssignment"
}
```

## A cop the plugin has no smell for is forwarded, not dropped

This is the deliberate exception to "a sensor emits vocabulary smells only". The
knip sensor drops a key it cannot map, because knip's key set belongs to knip. A
RuboCop cop that fired is one the project's own `.rubocop.yml` switched on, so
it belongs to the project, and forwarding it saves running RuboCop separately.
The smell key is the cop name verbatim.

An uncatalogued smell coaches without failing the run, so the second command
exits 0. The root `uncoached` key decides that, and it defaults to `suggest`.

📄.rubocop.yml
```yaml
AllCops:
  DisabledByDefault: true
  TargetRubyVersion: 3.1
Style/FrozenStringLiteralComment:
  Enabled: true
```

📄app.rb
```ruby
puts 'hello'
```

```bash
habit-sensors --all | jq -c '[.[] | {smell, source: .issues[0].details.source}]'
```

🖥️ ✅
```json
[{"smell":"Style/FrozenStringLiteralComment","source":"rubocop:Style/FrozenStringLiteralComment"}]
```

```bash
habit-sensors --all | habit-mapper >/dev/null
```

🖥️ ✅

## rubocop maps a syntax error to parse-error

RuboCop cannot run a cop over source it failed to parse, so it reports
`Lint/Syntax` instead, whatever the config enables. Unparseable Ruby is a
finding rather than a crashed sensor.

📄.rubocop.yml
```yaml
AllCops:
  DisabledByDefault: true
  TargetRubyVersion: 3.1
Metrics/ParameterLists:
  Enabled: true
```

📄broken.rb
```ruby
def broken(
```

```bash
habit-sensors --all | jq -c '[.[] | {smell, source: .issues[0].details.source}]'
```

🖥️ ✅
```json
[{"smell":"parse-error","source":"rubocop:Lint/Syntax"}]
```

## The project's own exclusions still apply

`--force-exclusion` is the one flag the sensor adds that changes what RuboCop
*lints*: it keeps a project's `AllCops: Exclude:` meaning something once
habit-hooks names files on the command line. Without it RuboCop reads a named
file as a deliberate request and lints it anyway, so the project's config
would stop applying the moment this tool ran it. (The sensor also passes
`--raise-cop-error`, which makes a crashing cop *fail* with
`Error:` and exit 2 which habit-hooks interprets as a failed run.)

📄.rubocop.yml
```yaml
AllCops:
  DisabledByDefault: true
  TargetRubyVersion: 3.1
  Exclude:
    - 'generated/**/*'
Metrics/ParameterLists:
  Enabled: true
```

📄generated/wire.rb
```ruby
def charge(a, b, c, d, e, f, g)
  a
end
```

```bash
habit-sensors --all | jq -c '[.[].smell]'
```

🖥️ ✅
```json
[]
```

## A crashing rubocop fails the run, never reports clean

A `.rubocop.yml` naming cops from an extension gem that is not loaded is a hard
RuboCop error. It is also the likeliest way this sensor fails in practice, since
every Rails project's config names `rubocop-rails` and that gem loads only under
the project's own bundle.

The sensor surfaces the error as a failure, because a crashed tool is never a
clean run. It exits with a code outside the findings range, so `habit-sensors`
raises, names the sensor on stderr, and exits 1 instead of printing an empty
result that would read as clean. The failed run carries only the reserved
`incomplete-run` marker on stdout
([habit-sensors.spec.md](../../../docs/habit-sensors.spec.md)).

📄.rubocop.yml
```yaml
Rails/Blank:
  Enabled: true
```

📄app.rb
```ruby
puts 'hello'
```

```bash
habit-sensors --all | jq -c '[.[].smell]'
```

🖥️ ❌ 1
```json
["incomplete-run"]
```

```bash
habit-sensors --all 2>&1 >/dev/null | sed -n 1p
```

🖥️ ❌ 1
```text
habit-sensors: sensor 'rubocop' failed: '${python}' '${dir}/rubocop_sensor.py' '${detector:rubocop}' '${files}'
```

## An empty scope runs no sensor, so rubocop never scans the whole tree

A scoped run that resolves to zero files measured nothing, and no sensor may run
over it. A `rubocop` handed no paths falls back to its own default and scans the
current directory, so without this guard a docs-only change reports every legacy
smell in the tree and fails the run (#93). Here the plugin's `files` counts only
Ruby as source and `--file README.md` names a doc, so the scope is empty even
though `legacy.rb` carries a real smell.

📄.rubocop.yml
```yaml
AllCops:
  DisabledByDefault: true
  TargetRubyVersion: 3.1
Metrics/ParameterLists:
  Enabled: true
```

📄README.md
```markdown
# Docs only
```

📄legacy.rb
```ruby
def charge(a, b, c, d, e, f, g)
  a
end
```

```bash
habit-sensors --file README.md | jq -c '[.[].smell]'
```

🖥️ ✅
```json
[]
```
