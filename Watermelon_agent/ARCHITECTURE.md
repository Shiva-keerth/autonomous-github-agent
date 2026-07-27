# ARCHITECTURE.md

## Autonomous Platform Intelligence Agent — GitHub

### What does your memory system store, and why did you structure it that way?

Memory is split into two distinct layers, stored in SQLite.

**Execution Memory** stores every instruction the agent has ever run: the instruction text, the exact plan used, whether it succeeded, how many steps/calls it took, how long it took in real seconds, and any error. This layer answers "have I done something like this before, and how did it go?" Before planning a new instruction, the agent checks this table for an exact successful match. If found, it reuses the saved plan instead of calling the LLM to re-plan from scratch — this is the direct mechanism behind the measured speedup on repeat instructions.

**Capability Memory** stores, per individual action (e.g. `close_issue`), a running total of calls, successes, failures, and the most recent error. This answers "how reliable is this specific tool, based on real use?" It's updated after every real action, whether the action was run through a normal plan or through a synthesized capability.

A third table, **Synthesized Capabilities**, stores any new capability the agent builds at runtime (name, description, filter logic, target action, and how many times it's been reused since). This is separate from the other two because it stores a reusable *pattern*, not a single event or a single action's stats.

I structured memory this way because the two required kinds of knowledge — "what happened" (execution history) and "what works" (capability reliability) — answer genuinely different questions and get updated at different times, so combining them into one table would blur what each row actually means.

### How does capability synthesis work in your implementation?

When an instruction requires finding issues that match a content condition (e.g. a keyword in the title) and then applying a different action only to the matches, the agent's fixed 3 actions can't do this directly — none of them can decide *which* issues to act on based on content. A dedicated LLM check (`check_needs_synthesis`) recognizes this pattern and extracts what's needed: which field to check, how to check it, what value to match, and which existing action to apply to matches.

Synthesis itself works by **composing existing tools**, not generating new code: it calls `list_open_issues` to get real, current issues, filters them in Python against the extracted condition, then calls the existing `close_issue` action on each real match. The first time a given capability is needed, it's saved to the Synthesized Capabilities table; every subsequent time, it's found and reused (tracked via `times_reused`) instead of being reasoned out again.

I chose composition over runtime code generation because it is explicitly listed as a valid form of synthesis in the assignment brief, and because a fully working, fully-understood composition-based approach is stronger than a fragile, harder-to-verify code-generation system built under time pressure. With more time, I would extend this to full runtime code generation — the agent actually writing and testing new Python functions for capabilities that composition alone can't express (e.g. cross-referencing two different data sources).

### What is your learning signal, and what does the agent do differently on run N vs run 1?

The primary learning signal is planning cost avoidance, measured in real elapsed time and LLM calls made. On the first run of any new instruction, the agent has no memory of it, so it calls the LLM to plan from scratch (`planning_llm_call_made: true`) — this took approximately 3.0 seconds in testing. On every subsequent run of the same instruction, the agent finds the successful prior run in Execution Memory and reuses that exact plan, skipping the LLM call entirely (`planning_llm_call_made: false`) — this consistently took approximately 2.4–2.7 seconds across four repeated test runs, a genuine ~15–20% reduction driven specifically by the one skipped LLM call.

A second, independent learning signal applies to synthesized capabilities: the first time a capability like "filter and close by title" is needed, it must be built and saved. Every subsequent time the same *type* of instruction appears, the capability is found and reused directly (confirmed via `times_reused` incrementing), without the agent re-deriving the filter-and-act pattern from the instruction again.

### Known Limitations

Only GitHub is supported (by design, one platform was required). Capability synthesis currently supports one filter type ("contains" on a text field); numeric and date-based filtering are the natural next extension, using the same `filter_field`/`filter_type` structure already in place. Given more time, the next priority would be full runtime code generation for synthesis, and expanding the fixed action set beyond list/get/close.