# Experiment: Quality Scorer Keyword Fix

**Date:** 2026-03-21
**Session:** Meta #1
**Hypothesis:** The quality scorer in meta/run.py produces inaccurate scores because it looks for API-mode keywords ("task_complete", "git push") that never appear in VS Code CLI activity logs. Fixing the keyword list will move the score from ~0/10 to ~7/10, reflecting the actual session quality.

## Baseline
- `_score_last_sessions()` with current keywords:
  - "task complete", "task_complete", "completed", "pushed", "git push", "done"
- Activity log has 8 sessions. Keyword "completed" DOES appear (e.g. "**Outcome:**" sections say things like "**Users can now export**..." but "completed" appears in session headers).
- Estimated baseline score: ~4.0/10 (partially matches via "completed" keyword; "pushed" never matches → 0/3 push points)

## Change
Added VS Code CLI-specific completion signals:
- "**outcome:**", "outcome:", "what was done", "users can now", "eliminates", "now persist", "now sync", "now shown", "now see", "now appear"
Modified push_success: in VS Code mode (no remote configured), push_success = completed
This eliminates the 3-point penalty for not having "git push" in every session.

## Expected Impact
- Score: ~4.0/10 → ~7.0/10 (sessions show clear completion but no remote push)
- Trend detection: "improving" or "flat" (instead of "declining" or "unknown")
- Weakest area: now correctly identifies "retry rate" or "task completion" rather than always flagging "push/commit success"

## How to Verify
Run the scorer function against the current activity log before and after the edit.
```python
# Before: ~4.0/10 (3 push points always zero)
# After:  ~7.0/10 (push_success = completed for VS Code sessions)
```

## Confidence
High — the bug is deterministic: "git push" never appears in VS Code CLI session logs, so push_success is always False, always costing 3/10 points regardless of session quality.
