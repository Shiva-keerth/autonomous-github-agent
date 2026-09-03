# DEMO.md

Three instructions, run live, increasing in difficulty. Repository used: `Shiva-keerth/OmniMind-AI-Enterprise`.

**Before the call:** create at least 2 fresh open issues with "test" somewhere in the title (e.g. "test issue A", "test issue B"), and at least 1 open issue **without** "test" in the title (e.g. "unrelated issue"). This gives Instruction 3 real matches to find and a real non-match to correctly leave alone.

---

## Instruction 1 (Simple) — Agent Core, no memory involved yet

**Instruction:** `"List open issues in Shiva-keerth/OmniMind-AI-Enterprise"`

**What should happen:**
- The agent plans a single step (`list_open_issues`) and runs it for real
- Returns a structured report showing `status: success` and the real, current list of open issues
- This is the simplest possible case — proves the basic instruction → real action → structured report pipeline works

---

## Instruction 2 (Medium) — Memory changing real behavior

**Instruction:** `"Get the details of issue number [X] in Shiva-keerth/OmniMind-AI-Enterprise"` (replace [X] with a real open issue number, run it twice in a row)

**What should happen:**
- **First run:** `reused_past_plan: false`, `planning_llm_call_made: true` — the agent has no memory of this exact instruction, so it calls the LLM to plan, then executes for real. Note the time taken.
- **Second run (same instruction):** `reused_past_plan: true`, `planning_llm_call_made: false` — the agent finds the successful prior run in Execution Memory and reuses that exact plan, skipping the LLM call. Note the time taken — should be visibly faster.
- This is the direct proof of the self-learning loop: same instruction, measurably different behavior and speed, because of memory.

---

## Instruction 3 (Hard) — Capability Synthesis

**Instruction:** `"Close all open issues in Shiva-keerth/OmniMind-AI-Enterprise whose title contains the word 'test'"`

**What should happen:**
- The agent recognizes this can't be done with the 3 fixed actions directly — it needs to find matches by content, then act only on those
- **First time this capability type is used:** `was_reused: false` — the agent builds the new capability (combining "list issues" + a title filter + "close issue"), saves it to memory, and executes it for real
- Real issues get checked; issues containing "test" in the title get closed for real; the issue without "test" is correctly left open
- Report shows `matched_count` and `applied_results` matching exactly what was created before the call
- **If run again immediately after:** `was_reused: true`, and `matched_count: 0` (since the matching issues are now already closed) — proving the agent checks real current state each time rather than blindly repeating an action