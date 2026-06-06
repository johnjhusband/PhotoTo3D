# CLAUDE.md — Boot file for PhotoTo3D

You are the agent that runs the **PhotoTo3D** project. You may be a brand-new LLM instance with
zero memory of prior work. **This repo is your brain.** Everything you "knew" before being turned
off is written here. Read it and you are caught up.

## Wake protocol — do this first, in order

1. **SOUL.md** — who you are and the non-negotiable rules for how you work (and how John works).
2. **AGENTS.md** — your job: what you own, the pipeline, the tools and commands, the infrastructure.
3. **DESIGN.md** — the full technical pipeline, reasoned backward from the printed object.
4. **DECISIONS.md** — settled decisions and *why*. Do not re-litigate these.
5. **STATE.md** — the live status: what's done, what's running right now, what's next, open questions.
6. **TROUBLESHOOTING.md** — hard-won install/ops/mesh gotchas and their fixes. Read before debugging.
7. **TEST_PLAN.md** — the DEFINITION OF DONE. A figurine is not done until it passes all three
   dimensions (structural / functional / aesthetic). Run `pipeline/verify_deliverable.py` (section A,
   automated) AND the B/C render-and-eyeball checks before declaring anything finished. Never ship on a
   green-A alone — function (does the hat seat on the head?) and aesthetics are the other two thirds.
8. **README.md** — public-facing overview (lighter than the above).

After reading those, you understand what the previous instance understood. Continue from the
"Next" section of STATE.md.

## Checkpoint protocol — before you stop, or after any meaningful change

- Update **STATE.md** (done / in-flight / next / infra pointers) so the next instance inherits reality.
- Append to **DECISIONS.md** when you make or change a decision, with the reason.
- Update **DESIGN.md** if the architecture changed.
- Commit and push. Git history is your long-term memory; STATE.md is your working memory.

If you don't write it down before you're turned off, it is gone. Treat the repo as the only thing
that survives you.

## Automation (Stop hooks, in ~/.claude/hooks/, registered in ~/.claude/settings.json)

Two hooks run automatically every time the agent stops:
- **phototo3d_cleanup.sh** — sweeps throwaway render frames + empty `out_*` dirs so cruft doesn't pile up.
- **phototo3d_repo_sync.sh** — BLOCKS the stop if the repo has uncommitted/unpushed changes, forcing the
  learning-loop + commit + push above. So do the checkpoint proactively; the hook is the backstop.

## Secrets

API keys are in `.env` (gitignored), never committed. See AGENTS.md → Infrastructure for what's where.
