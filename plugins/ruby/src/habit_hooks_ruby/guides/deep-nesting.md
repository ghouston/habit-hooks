Deeply nested blocks, like `if` inside `each` inside `begin` inside `if`, force the reader to hold every enclosing condition in their head at once. The smell is not the indentation; it is that the method is doing too much branching in one place.

Read the nesting from the inside out and ask what the innermost block actually needs. Usually most of the enclosing conditions are *guards*: preconditions that should be checked and bailed on early, not wrapped around the real work.

Prefer, in order:

1. **Guard clauses.** Invert a condition and `return` early so the happy path stays at the top indentation level. Inside a block, `next` is the same move: `collection.each { |x| next unless x.valid?; ... }` flattens everything below it.
2. **Extract a private method.** When an inner block is a coherent sub-step, pull it into a named method. The name documents the intent and the nesting moves into a flat, separately-readable unit.
3. **Replace the structure.** A deep `if/elsif` ladder is often a hash lookup or polymorphic dispatch in disguise; a nested loop is often a `filter`/`map` pipeline.

If the nesting is genuinely irreducible (a real algorithm with interacting conditions), extract the inner loops into well-named helpers: keep each method shallow even when the algorithm as a whole is deep.

The goal is a method whose shape you can take in at a glance. Merging conditions with `&&` drops a level by trading vertical nesting for an unreadable horizontal condition. The depth is the message, not the target.

{% include "includes/rubocop_line_level_issues.md" %}
