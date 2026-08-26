A fatal parse error means RuboCop could not analyse the file at all, so every other cop went unchecked there too — real issues in this file are currently invisible.

Typical causes worth checking: a syntax error (`ruby -c <file>` will name the line), a `TargetRubyVersion` in `.rubocop.yml` older than the syntax the file uses (e.g. pattern matching or endless methods under a 2.x target), or a generated file that is not valid Ruby.

You've fixed it when a deliberate change to the file produces the ordinary offence you'd expect — that proves analysis is running again. Do not silence it by adding the file to `AllCops: Exclude` or with a `# rubocop:disable` comment.

{% include "includes/file_level_issues.md" %}
