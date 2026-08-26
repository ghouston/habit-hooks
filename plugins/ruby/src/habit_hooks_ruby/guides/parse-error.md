A fatal parse error means RuboCop could not analyse the file at all, so every other cop went unchecked there too. Real issues in this file are currently invisible.

Check, in order: a syntax error (`ruby -c <file>` names the line); a `TargetRubyVersion` in `.rubocop.yml` older than the syntax the file uses (pattern matching or endless methods under a 2.x target); a generated file that is not valid Ruby.

You've fixed it when a deliberate change to the file produces the ordinary offence you'd expect, since that proves analysis is running again. Keep the file in the lint set: it is exactly the file most in need of the other cops.

{% include "includes/file_level_issues.md" %}
