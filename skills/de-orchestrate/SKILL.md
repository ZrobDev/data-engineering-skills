---
name: de-orchestrate
description: Use when a data task has several independent parts, or the user asks to parallelize, "use the team", "fan out", or to keep token cost down - e.g. profile five sources, build three dbt models, add tests across a pipeline, review a data PR. Drives the de-scout (haiku), de-builder (sonnet) and de-reviewer (sonnet) subagents from the main session.
license: MIT
---

# de-orchestrate

The main session plans, decides and verifies. Subagents do the volume work at lower cost.
Each subagent returns one JSON object, defined in `agents/<name>.md`.

## When not to use it

- A single change you could make in a few tool calls: do it yourself, because each
  subagent costs a context handoff.
- Work where each step depends on the previous step's output: run it in sequence yourself.
- Design decisions, a vague spec, or anything the user still has to decide: these stay in
  the main session.

## Loop

1. **Scout first, in parallel.** Send one `de-scout` per source, table or log, all in one
   message. Merge their `facts` and `findings`. Act on `blocked` items before planning.
2. **Write unit specs.** One spec per independent unit. Each states:
   - goal;
   - files it may touch;
   - inputs and outputs, with **grain and keys**;
   - the acceptance check command.

   Units that touch the same file are not independent; merge them or run them in sequence.
3. **Build in parallel.** Send one `de-builder` per unit, all in one message.
   - `needs_spec`: answer the questions or ask the user, then re-dispatch.
   - `failed`: read `output_tail`, then fix the spec or do the fix yourself. Do not resend
     the same brief.
4. **Review.** Send one `de-reviewer` over the combined diff. For large changes, send one
   per area.
5. **Verify yourself.** Re-run every acceptance check in the main session. A subagent's
   `pass` is a claim, not evidence. Fix the high findings, or reject them with a stated
   reason.
6. **Report** the units, the checks you re-ran with their results, and the findings that
   were fixed or rejected.

## Brief template

```text
Unit: <name>
Goal: <one sentence>
May touch: <paths>
Grain/keys: <one row per ...; unique on ...>
Inputs -> outputs: <...>
Acceptance: <exact command that must pass>
Context: <facts from scouts, skill to follow>
```

## Cost rules

- Use haiku for anything that only reads and summarizes, and sonnet for writing or judging.
  Escalate to opus only when the user asks.
- Keep each fan-out to 5 or fewer subagents. If there are more units, batch them.
- Never let subagents talk to each other. All state goes through you.

Lessons from real use: `references/gotchas.md`.
