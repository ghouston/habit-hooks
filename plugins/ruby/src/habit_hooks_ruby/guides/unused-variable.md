An unused local variable is dead weight. It usually signals one of three things:
* a computation whose result is never consumed
* a leftover from a refactor
* a value you meant to use and forgot to wire in (the real bug)

Decide which it is before fixing or deleting. If the right-hand side has side effects you still need, keep the call but drop the binding. If it was meant to be returned or passed on, finish that thread rather than silencing the warning.

{% include "includes/line_level_issues.md" %}
