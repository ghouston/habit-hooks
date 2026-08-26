This cop is not one habit-hooks coaches specifically. RuboCop's own message below says what fired and where.

1. **Let RuboCop fix what it can.** An issue tagged `[Correctable]` has an autocorrect: `rubocop -a <file>` applies safe corrections, `rubocop -A <file>` includes unsafe ones. review the diff it makes.
2. **For what remains:** ask why the cop exists and what it says about this code, then find a fix that improves: maintainability, cuts cruft, lowers cognitive load, and **importantly** improves security, scalability, and resilience. Fix the shape, not the score: a change that only quiets the cop while the code stays as tangled is worse than the offence.

{% include "includes/rubocop_line_level_issues.md" %}
