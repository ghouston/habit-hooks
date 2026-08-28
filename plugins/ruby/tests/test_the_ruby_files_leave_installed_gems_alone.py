"""What this plugin means when it says which files are its language's.

A project that names no ``files`` of its own scans what its plugins declare, and
``habit-hooks init`` writes exactly such a config, so what is declared here *is*
the first run for anyone init set up. A bare ``**/*.rb`` reaches into
``vendor/``, where Bundler puts every installed gem, and reports on code the
project did not write and cannot change.

Ruby also keeps source in files with no extension between them, so the globs
have to name ``Rakefile``, ``Gemfile`` and ``*.gemspec`` by hand. RuboCop lints
all three, and a project's own cops apply to them. That cuts both ways: an
installed gem ships its own ``Rakefile`` and ``.gemspec``, so every included
shape needs its own negative under ``vendor/`` and ``tmp/`` — excluding only
``*.rb`` left the rest leaking back in.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pathspec

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "habit_hooks_ruby"

PROJECT_SOURCE = (
    "app/models/billing.rb",
    "lib/tasks/import.rake",
    "spec/billing_spec.rb",
    "Rakefile",
    "Gemfile",
    "acme.gemspec",
    "engines/shop/Gemfile",
)
NOT_THIS_PROJECTS_SOURCE = (
    "vendor/bundle/ruby/3.4.0/gems/rails-8.0.0/lib/rails.rb",
    "vendor/cache/rack-3.1.0/lib/rack.rb",
    "vendor/cache/rack-3.1.0/rack.gemspec",
    "vendor/cache/rack-3.1.0/Rakefile",
    "vendor/bundle/ruby/3.4.0/gems/rails-8.0.0/tasks/engine.rake",
    "vendor/Gemfile",
    "tmp/cache/bootsnap/compile-cache-iseq/a.rb",
    "tmp/scratch.gemspec",
    "tmp/Rakefile",
    "tmp/cache/assets/import.rake",
    "tmp/cache/Gemfile",
    "db/schema.rb",
)


def _declared_files() -> pathspec.PathSpec:
    config = tomllib.loads((PACKAGE / "config.toml").read_text(encoding="utf-8"))
    return pathspec.PathSpec.from_lines("gitignore", config["files"])


def test_the_project_s_own_ruby_is_source() -> None:
    spec = _declared_files()

    assert [path for path in PROJECT_SOURCE if spec.match_file(path)] == list(
        PROJECT_SOURCE
    )


def test_an_installed_gem_is_not_this_project_s_source() -> None:
    """One of every included shape, under `vendor/` and under `tmp/`, nested
    and sitting directly on the directory: none of it is Ruby this project
    wrote. `vendor/Gemfile` is the boundary case — zero directories between
    `vendor/` and the file, where `**` has to match nothing.
    """
    spec = _declared_files()

    assert [path for path in NOT_THIS_PROJECTS_SOURCE if spec.match_file(path)] == []


def test_the_exclusions_name_ruby_shapes_so_they_bind_only_ruby() -> None:
    """A plugin's exclusions bind the union of every active plugin's globs, not
    just its own (docs/config.md). A bare `!**/vendor/**` here would stop a
    php+ruby project scanning its own Composer packages' PHP, the mistake the
    java plugin's config records making with `!**/build/**`. Every exclusion
    therefore names a file shape only Ruby claims — an extension Ruby source
    carries, or one of Ruby's extensionless filenames — never a directory.
    """
    config = tomllib.loads((PACKAGE / "config.toml").read_text(encoding="utf-8"))
    exclusions = [glob for glob in config["files"] if glob.startswith("!")]

    assert exclusions, "the plugin declares no exclusions at all"
    ruby_shapes = (".rb", ".rake", ".gemspec", "/Rakefile", "/Gemfile", "/schema.rb")
    for glob in exclusions:
        assert glob.endswith(ruby_shapes), glob
