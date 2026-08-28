"""The uncoached guide fallback is filtered by the finding's language.

``rendering.resolve_guide`` picks the primary guide from
``plugins_for_language`` — the language-matching plugin first, the languageless
plugin (``generic``) last — but the ``uncoached.md`` fallback used to walk the
raw ``config.plugins`` order. A plugin of a *different* language that happened
to be listed first therefore coached the finding: with Ruby first, Ruby's
newly shipped ``uncoached.md`` coached an uncatalogued TypeScript/ESLint
finding (#150). The fallback must walk the same language-filtered order, then
the core's own guide.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from habit_hooks import mapper
from plugin_fixture import write_plugin, write_project_config

_TYPESCRIPT_FINDING = {
    "smell": "unmapped-eslint-rule",
    "language": "typescript",
    "details": {},
    "issues": [{"key": "src/a.ts", "details": {"file": "src/a.ts"}}],
}


def test_the_uncoached_fallback_respects_the_findings_language(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With Ruby listed first and only Ruby and generic shipping an
    ``uncoached.md``, an uncatalogued TypeScript finding is coached by
    generic's — never by Ruby's (#150)."""
    write_plugin(
        tmp_path,
        "ruby",
        {
            "config.toml": 'language = "ruby"\nsensors = []',
            "guides/uncoached.md": "Ruby-shaped uncoached guidance.",
        },
    )
    write_plugin(
        tmp_path,
        "typescript",
        {"config.toml": 'language = "typescript"\nsensors = []'},
    )
    write_plugin(
        tmp_path,
        "generic",
        {
            "config.toml": "sensors = []",
            "guides/uncoached.md": "Generic uncoached guidance.",
        },
    )
    write_project_config(tmp_path, 'plugins = ["ruby", "typescript", "generic"]')

    mapper.run([_TYPESCRIPT_FINDING], tmp_path)

    out = capsys.readouterr().out
    assert "Generic uncoached guidance." in out
    assert "Ruby-shaped uncoached guidance." not in out


def test_the_uncoached_fallback_reaches_the_core_without_a_languageless_plugin(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No languageless plugin configured: the fallback reaches the core's own
    ``uncoached.md`` rather than a differently-language plugin's (#150)."""
    write_plugin(
        tmp_path,
        "ruby",
        {
            "config.toml": 'language = "ruby"\nsensors = []',
            "guides/uncoached.md": "Ruby-shaped uncoached guidance.",
        },
    )
    write_project_config(tmp_path, 'plugins = ["ruby"]')

    mapper.run([_TYPESCRIPT_FINDING], tmp_path)

    out = capsys.readouterr().out
    assert "General guidance" in out
    assert "Ruby-shaped uncoached guidance." not in out
