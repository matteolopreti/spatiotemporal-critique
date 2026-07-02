# Feature-Flag Progressive Rollout

## Overview

This specification defines how a feature flag moves from dark launch to full availability: cohort assignment, stage percentages, promotion criteria, rollback triggers, and kill-switch semantics. It applies to every user-facing flag served by the flag service; internal operational toggles are out of scope.

A rollout is a sequence of stages, each enabling the flag for a fixed share of eligible users. Stage percentages are the total enabled share at that stage, not an increment over the previous stage.

## Cohort Assignment

Each user is mapped to a bucket in [0, 9999] by computing SHA-256 over the string `<flag_key>:<user_id>` and taking the result modulo 10,000. The mapping is deterministic — a user keeps the same bucket for a given flag across sessions and devices — and independent across flags, since the flag key is part of the hash input. For anonymous traffic, the stable device identifier substitutes for the user identifier; requests with neither identifier are served the default (control) code path and are not counted as exposed.

A stage with threshold T enables buckets [0, T). Buckets [9900, 10000) are reserved as the control cohort (1% of users) for metric comparison and are never enabled before Stage 5.

## Stages

| Stage | Share enabled | Bucket threshold | Minimum soak time |
|-------|---------------|------------------|-------------------|
| 1     | 1%            | 100              | 24 hours          |
| 2     | 5%            | 500              | 24 hours          |
| 3     | 25%           | 2,500            | 48 hours          |
| 4     | 50%           | 5,000            | 48 hours          |
| 5     | 100%          | 10,000           | — (launch)        |

Thresholds only increase during a rollout, so each stage's enabled set is a strict superset of the previous stage's: no user ever flips from enabled to disabled by a promotion. This monotonicity is the property that makes mid-rollout metrics attributable — treatment users accumulate exposure, they never churn out.

The treatment range never overlaps the control cohort through Stage 4: the largest pre-launch threshold is 5,000, and control occupies [9900, 10000). At Stage 4, the population splits 50% treatment, 1% control, 49% untreated remainder — totaling 100%. Stage 5 enables all buckets, including former control; comparison metrics are therefore defined only for Stages 1–4, and Stage 5 is monitored through the service's global error budget instead.

Minimum soak times sum to 144 hours, so a flag reaches 100% no sooner than 6 days after entering Stage 1.

## Promotion Criteria

Promotion from one stage to the next requires all of the following, evaluated over the current stage's soak window:

- Minimum soak time met (table above).
- Sample floor met: at least 500 exposed users — users who evaluated the flag and received treatment. If the floor is not met when the minimum soak elapses, the stage simply continues until it is; soak times are minimums, never deadlines.
- Error-rate delta below 0.5 percentage points: the treatment cohort's request error rate minus the control cohort's, as an absolute percentage-point difference.
- Latency: treatment p95 within 5% of control p95.
- No Sev-2 or higher incident attributed to the flag during the stage.

The error-rate delta governs a three-band policy with no gaps or overlaps: below 0.5 points, the flag is promotion-eligible; from 0.5 up to but not including 2.0 points, the flag holds at its current stage pending a human decision (promote is blocked, rollback is not forced); at 2.0 points or above, automatic rollback fires (next section). A hold is not a failure state — operators may investigate, fix forward behind the same stage, or roll back manually.

Promotion is a manual action by the flag owner once all criteria show green; the service enforces the criteria and refuses promotion while any is unmet.

## Rollback

Automatic rollback sets the threshold to 0 immediately when any trigger fires:

- Error-rate delta of 2.0 percentage points or more.
- Crash-rate increase of 1.0 percentage point or more in treatment versus control.
- A Sev-1 incident attributed to the flag.

Manual rollback to threshold 0 is available to the flag owner and to on-call at any time, with no criteria. Rollback does not delete the flag or its configuration; it returns all users to the default code path. A subsequent re-rollout always restarts at Stage 1 with full minimum soak times — prior soak credit is never carried across a rollback, because the fix that motivated the rollback invalidates the earlier observations.

## Kill Switch

The kill switch is distinct from rollback: it is a latching, service-wide override that forces the default code path for 100% of traffic regardless of thresholds, cohorts, or in-flight promotions. It exists for incident response when even the flag service's normal write path may be suspect.

Activation propagates over a push channel to all SDK clients, with polling as fallback: clients poll configuration every 30 seconds, and a configuration build takes at most 15 seconds, so worst-case pickup via polling alone is 45 seconds — inside the 60-second activation budget the service commits to. Push-connected clients typically converge in under 5 seconds.

While latched, all promotions and threshold changes for the flag are blocked. Releasing the kill switch requires a manual reset by the flag owner plus one other engineer (two-person action). After reset the flag is at threshold 0, and any re-rollout restarts at Stage 1, identical to post-rollback semantics.

## Lifecycle and Cleanup

After 30 consecutive days at Stage 5 with the error budget intact, the flag is scheduled for code removal: the default path becomes the launched behavior and the flag is deleted from the service. The kill switch remains available until the code removal ships. Flags past their removal date appear on the weekly debt report until cleaned up.
