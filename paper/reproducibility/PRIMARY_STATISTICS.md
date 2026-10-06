# Independent reproduction of primary statistics

This entry point recalculates the primary EEG summaries and participant-bootstrap intervals from compact, archived endpoints. It runs independently of the experiment estimators, the production analysis programs, the figure generators, and the manuscript. It requires Python 3.10 or later and NumPy; it does not require a GPU, EEG recordings, feature arrays, saved model weights, network access, or the original Ubuntu directories.

## Run with the portable input

From the package root:

```bash
python3 paper/reproducibility/recompute_primary_statistics.py \
  --self-test --out primary_statistics_report.json
```

The default input is `primary_statistical_inputs.json` beside the script. It can be overridden with `--inputs`. The input is about 2.26 MB and contains 1,756 exact records from 50 archived JSON sources. Every record has the original repository-relative source, RFC 6901 JSON pointer, raw value, units, and complete-source SHA-256. The script reads those embedded values without requiring the original files.

The output contains the recalculated estimates, intervals, old-test decline identities and counts, the four retention table rows, the joint-criterion decisions, check count, largest numerical discrepancy, runtime versions, and hashes of the script and compact input. It exits nonzero if a checked result differs from the archived result. The fixed absolute comparison tolerance is `1e-10` in the original stored units; no tolerance is added to the joint-criterion decision.

If the original result JSON files are also included in the package or repository, check every embedded value and original source hash as well:

```bash
python3 paper/reproducibility/recompute_primary_statistics.py \
  --source-root . --self-test --out primary_statistics_source_report.json
```

Both commands leave the input and original research files unchanged. `--out` controls the only verification output. Without `--out`, the full report is printed to standard output.

## Recalculated results

| Analysis | Input endpoints | Independent calculations |
|---|---|---|
| Lee, original-event confirmation group, participants 13–54 | Each participant's original future classification and mapping endpoints, including all five class-preserving shuffles | Equal-participant AUC/MSE means; label-updated minus frozen low-view AUC; true-pair minus frozen and shuffled mapped-classifier AUC; true-pair minus frozen and shuffled mapping MSE; original paired 95% intervals |
| Stieger 62, original label-budget stage | Each participant/session endpoint for 0%, approximately 25%, and 100% labels with no new pairs; initial and final permanent-old endpoints for the 25% arm | Session means within each participant; equal-participant means and original 95% intervals; 25%-minus-0% and 100%-minus-25% paired differences; 25% permanent-old initial/final/change; decline counts and identities; label savings and the ratio of the two cohort-mean gains |
| Stieger 62 and nested 41, original line-constraint stage (v3) | Saved per-participant future means and initial/final permanent-old BA for `own` and `own_functional` | Means and 95% intervals; severe-harm indicators recalculated from initial/final scores; paired constrained-minus-own differences; original joint criterion |
| Stieger 62 and nested 41, full-space stage (v4) | Saved per-participant future means and initial/final permanent-old BA for `own` and `own_constrained` | The same endpoint calculations, using the v4 stage's own RNG seed and archived comparisons |

The input preserves the original within-stage reference models. The v3 line interval is not regenerated using the v4 seed, and the two constraint stages are not treated as an architecture-controlled comparison with the shared budget classifier. Lee shuffles are averaged within participant before computing the participant's difference; five assignments do not increase the sample size.

The Stieger future BA input remains on the 0–1 scale. Multiply BA and harm-proportion differences by 100 to obtain percentage points. Label savings use `1 - 8833/35787`. The proportion of the all-label gain retained uses the ratio of group-mean gains, not the mean of individual ratios. Neither quantity establishes noninferiority to the all-label arm.

## Exact resampling rules

All reproduced intervals use 10,000 paired participant resamples and linear percentiles at 0.025 and 0.975. The same participant indices are used across conditions within a stage and cohort. Participants are averaged equally; repeated Stieger sessions are first averaged within participant.

| Stage | Original RNG initialization |
|---|---|
| Lee original-event 42 | `numpy.random.default_rng(20261003)` |
| Stieger label-budget v1 | `default_rng(SeedSequence([2026100511, cohort_index, n, *participant_ids]))` |
| Stieger line constraints v3 | `default_rng(SeedSequence([2026100711, cohort_index, n, *participant_ids]))` |
| Stieger full-space constraints v4 | `default_rng(SeedSequence([2026100811, cohort_index, n, *participant_ids]))` |

The draw is `integers(0, n, size=(10000, n))`. Participant IDs are in their original sorted order. Cohort index 0 denotes all 62; index 1 denotes the nested 41. The budget calculation here covers cohort 0. Seeds and original seed-rule descriptions are copied from archived protocol/analysis records into the input and are checked when `--source-root` is supplied.

The independent implementation indexes each participant vector directly for each resample. It sorts the resulting means and interpolates explicitly at `(10000 - 1) * q`, without calling the production bootstrap functions or `numpy.quantile`. The later production analyses used equivalent participant-count matrix products; numerical differences at floating-point summation precision are expected.

Old decline is `final_BA - initial_BA < -1e-12`. Severe decline is `final_BA - initial_BA <= -0.05 + 1e-12`, preserving the archived score-rounding convention. The joint criterion is evaluated without a relaxed decision threshold: the future-difference lower 95% bound must be at least `-0.005`, and the severe-harm-proportion difference upper 95% bound must be strictly below zero. An upper bound equal to zero fails.

## Verification and scope

The initial full-source check passed 4,370 comparisons; the largest numerical difference was `2.220446049250313e-16`. It reproduced the main Stieger 62 line row (+0.411 pp future, −8.065 pp harm fraction) and full-space row (+0.070 pp future, −3.226 pp harm fraction), including their original intervals. Both cohorts in both constraint stages passed the future criterion and failed the harm-reduction criterion. The budget-stage counts were 19 old-test declines, 12 declines of at least 5 pp, and 19 old-test declines with a positive future point difference against zero new labels. The verification output retains full precision; the manuscript displays rounded values.

This is statistical reproduction from saved participant and session endpoints. It does not recompute AUC or BA from trial-level predictions, repeat EEG preprocessing or model fitting, rerun the experiment-wide mathematical audits, or validate every appendix comparison. For the constraint stages, future session aggregation is already embodied in the saved participant means; the budget stage separately recalculates that aggregation from saved session endpoints. Original endpoint/model audits remain separate records in the archived experiment folders.

Intervals condition on the fitted models and observed endpoint values. The script does not refit shared models or account for dependence introduced by shared training and feedback donors. Stieger remains development evidence; the 41-participant cohort is nested. It does not introduce new tests, choose a method, change eligibility, alter any comparison family, or infer population-level decline for each individual.

## Maintaining the compact input

When maintaining this package in the full research checkout, regenerate the input from the exact source paths encoded in the extraction routine, then verify it:

```bash
python3 paper/reproducibility/recompute_primary_statistics.py \
  --extract-from . --source-root . --self-test \
  --out primary_statistics_source_report.json
```

This explicit maintenance mode replaces `--inputs` with freshly extracted source records. Ordinary public reproduction does not use `--extract-from`. The source selection is fixed to the primary comparisons listed above; the extraction process does not consult model performance to include or exclude participants.
