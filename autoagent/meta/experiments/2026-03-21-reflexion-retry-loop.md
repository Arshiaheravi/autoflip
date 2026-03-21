# Experiment: Reflexion Self-Reflection in Engineer Retry Loop

**Date:** 2026-03-21
**Session:** Meta #1
**Source:** Shinn et al. "Reflexion: Language Agents with Verbal Reinforcement Learning" (arXiv:2303.11366)

## Hypothesis
Adding a mandatory 3-sentence verbal self-reflection step before each health check retry will improve retry success rate by ~10–15%.

**Evidence from research:**
- Reflexion achieved +11% on HumanEval Python coding tasks over 12 iterative steps
- Key mechanism: converting binary pass/fail into natural-language self-critique stored as context for the next attempt
- SaMuLe (multi-level reflection) shows step-level reflection catches the most common failure mode: wrong function/method call

## Baseline
Current behavior: health check fails → `update_current_task(qa_attempt=N, qa_feedback="...")` → retry
Problem: qa_feedback is often a copy-paste of the error message, not a diagnosed root cause.
Without explicit self-reflection instruction, the agent tends to make the same mistake on retry attempt 2.

## Change Applied
`autoagent/agents/engineer.py` — Added PHASE 5.5 between Test and Validate phases.
Requirements:
1. Self-reflection is 3 sentences: what failed, root cause (not symptom), what will change
2. Reflection must precede the fix (think before acting)
3. After 3 failures: write_post_mortem + escalate to backlog (prevents infinite spiraling)

## Expected Impact
- Retry success rate: ~50% → ~60-65% on attempt 2 (agent diagnoses root cause vs. re-applying same fix)
- Sessions with 3+ retries: reduced (better diagnosis = less brute-force)
- Post-mortems: will increase (good — we want failed approaches documented)

## How to Verify
Count sessions where qa_attempt > 1 in activity log. Compare "retry eventually succeeded" rate before and after this change becomes active in the next 10 agent sessions.

## Risk
Low — this is an additive instruction, not a structural change. Worst case: agent ignores it (current behavior preserved).
