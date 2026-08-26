High complexity means one method makes too many decisions at once. RuboCop measures it three ways: cyclomatic counts branches, perceived weights nesting, AbcSize counts assignments and calls. One method can therefore be listed more than once below. The count is the symptom; tangled responsibilities are the cause.

**Untangle the decisions:**
1. Lift guards out first: turn precondition checks into early returns (`return unless ...`) so the happy path stays flat. Much of the count is preconditions wrapped around the real work.
2. Change the shape of what remains: an `if`/`elsif` chain switching on one value is often a hash lookup or polymorphism in disguise; a nested loop is often a `filter`/`map` pipeline.
3. If the branches are genuinely separate jobs, extract one method per branch, each named for the responsibility it handles.

Useful tip: describe each branch in one sentence. Two branches with the same sentence belong together; a branch you cannot name cleanly wants its own method.

Lower the decision count, not the metric: merged conditions and ternaries move the number while the decisions remain. You are done when a first-time reader can hold the whole method in their head.

{% include "includes/rubocop_line_level_issues.md" %}
