# Statistical methods and historical software record

This record documents completed analyses without changing their comparisons, intervals or decision rules. Raw JSON values and source SHA-256 digests are in `statistical_methods.json`.

## Manuscript text

EEG endpoints were summarized within participant before equal-participant averaging. Paired, two-sided percentile bootstrap intervals used 10,000 participant resamples for the main results and subsequent extensions; the earlier continual-information stage used 5,000. Resampling preserved paired conditions while fitted models, shared teachers and realized donor assignments remained fixed. The 2.5 th and 97.5 th percentiles define the original descriptive 95% intervals. Three original two-comparison families retain Bonferroni-adjusted 97.5% intervals (1.25 th and 98.75 th percentiles): the two Lee common-history future-AUC contrasts in 42 participants, and the other-versus-own and mixed-versus-own future-BA contrasts separately in Stieger 62 and Farabbi 12. Remaining comparisons retain their original descriptive 95% interpretation; the nested 41-person Stieger cohort is not an independent replication. The joint retention criterion requires both its predefined future-performance lower-bound criterion and its old-loss-proportion upper-bound criterion. Stage-specific seeds, exact resampling rules and archived software records are listed in the reproducibility record.

## Participant analyses

All intervals below are paired, two-sided percentile intervals with linear interpolation. Original 95% intervals use quantiles 0.025/0.975. Original 97.5% intervals use 0.0125/0.9875. The three two-comparison families are listed explicitly; all other intervals retain their original descriptive/exploratory interpretation.

| Stage | Participants | Draws | Bootstrap seed | Original interval rule |
|---|---|---:|---:|---|
| Lee original-event ERP | 12 development /42 excluded from development /54 combined descriptive | 10,000 | 20261003 | Descriptive 95% |
| Lee common-history ERP | 12 development /42 confirmation /54 combined descriptive | 10,000 | 20261005 | 97.5% stated family; other 95% |
| Lee development diagnostics | 12 | 10,000 | 20261004 | Descriptive 95% |
| Yang original joint-update replication | 51 | 10,000 | 20261003 | Descriptive 95% |
| Early continual-information EEG | 62 /nested 41 | 5,000 | 20261002 | Descriptive 95% |
| Initial-readout diagnostics | Stieger 62 /nested 41 /Yang 51 | 10,000 | 20261004 | Descriptive 95% |
| Ridge true-pair/mismatch controls | Stieger 62 /nested 41 /Yang 51 | 10,000 | 20261004 | Descriptive 95% |
| Stieger/Yang history diagnostics | Stieger 62 /nested 41 /Yang 51 | 10,000 | 2026100504 | Descriptive 95% |
| Label-budget and calibration policies | 62 /nested 41 | 10,000 | 2026100511 | Descriptive 95% |
| Output-penalty retention | 62 /nested 41 | 10,000 | 2026100611 | Descriptive 95% |
| Feedback source and line constraint | 62 /nested 41 | 10,000 | 2026100711 | 97.5% stated family; other 95% |
| Full-space risk constraint | 62 /nested 41 | 10,000 | 2026100811 | Descriptive 95% |
| Farabbi source and retention evaluation | 12 | 10,000 | 2026100821 | 97.5% stated family; other 95% |
| Initial-training classification diagnosis | 12 | 10,000 | 2026100911 | Descriptive 95% |
| Initial-training retention diagnosis | 62 | 10,000 | 2026100912 | Descriptive 95% |
| Expanded-regularization control | 12 | 10,000 | 2026101011 | Descriptive 95% |
| Replay/radius controls final R 2 | 62 | 10,000 | 2026101012 | Descriptive 95% |
| Finite correctness/persistence reference | 62 /qualified 29 /nested 41 /nested qualified 19 | 10,000 | 2026101111 | Descriptive 95% |

### Lee original-event ERP

Scope: Main results and appendix. Comparisons: True-pair/control omitted-feature error; mapped and label-only task endpoints.

RNG: `default_rng(seed); shared integer indices (10000,n) within group`.

The 42-person group was excluded from development, but the original-event intervals explicitly remain descriptive 95%. This is distinct from the common-history event set. Five within-class shuffle allocations are averaged within person, not treated as independent samples.

- Analyzer: [experiments/lee2019_erp_history_v1/pilot_run.py](../../experiments/lee2019_erp_history_v1/pilot_run.py), line 140.
- Protocol/freeze: [experiments/lee2019_erp_history_v1/protocol.json](../../experiments/lee2019_erp_history_v1/protocol.json), [experiments/lee2019_erp_history_v1/protocol_freeze.json](../../experiments/lee2019_erp_history_v1/protocol_freeze.json), [experiments/lee2019_erp_history_v1/execution_freeze.json](../../experiments/lee2019_erp_history_v1/execution_freeze.json).
- Archived independent verification: [experiments/lee2019_erp_history_v1/results/verification_pilot.json](../../experiments/lee2019_erp_history_v1/results/verification_pilot.json), status `{"status": "PASS"}`.

### Lee common-history ERP

Scope: Appendix. Comparisons: Label-updated ordered-timing minus current-timing and minus mean five shuffled-timing future AUC; remaining controls.

RNG: `default_rng(20261005); one shared integer matrix (10000,n) for each group`.

Only the two primary future-AUC contrasts in the 42-person group use 97.5%; other endpoints/groups retain 95%.

Original Bonferroni family: 42-person common-history group: ordered-timing minus current-timing; ordered-timing minus average five shuffled-timing; future label-updated AUC. Each of the two intervals has 97.5% coverage.

- Analyzer: [experiments/lee2019_erp_history_v1/run_history.py](../../experiments/lee2019_erp_history_v1/run_history.py), line 154.
- Protocol/freeze: [experiments/lee2019_erp_history_v1/protocol.json](../../experiments/lee2019_erp_history_v1/protocol.json), [experiments/lee2019_erp_history_v1/execution_freeze.json](../../experiments/lee2019_erp_history_v1/execution_freeze.json).
- Archived independent verification: [experiments/lee2019_erp_history_v1/results/verification_history.json](../../experiments/lee2019_erp_history_v1/results/verification_history.json), status `{"status": "PASS"}`.

### Lee development diagnostics

Scope: Appendix. Comparisons: Common/spatial omitted-feature skill and task/teacher diagnostics.

RNG: `default_rng(20261004); shared (10000,12) participant indices`.

Only summaries that have archived intervals use this bootstrap; ratios/correlations reported as descriptive means are not assigned new intervals. Development diagnostics do not establish the mechanism of the 42-person result.

- Analyzer: [experiments/lee2019_erp_diagnostics_v1/run.py](../../experiments/lee2019_erp_diagnostics_v1/run.py), line 212.
- Protocol/freeze: [experiments/lee2019_erp_diagnostics_v1/protocol.json](../../experiments/lee2019_erp_diagnostics_v1/protocol.json).
- Archived independent verification: [experiments/lee2019_erp_diagnostics_v1/results/verification.json](../../experiments/lee2019_erp_diagnostics_v1/results/verification.json), status `{"status": "PASS"}`.

### Yang original joint-update replication

Scope: Appendix. Comparisons: Original joint task/mapping-update contrasts.

RNG: `default_rng(seed) reset per metric; valid paired participants; integer matrix (10000,n)`.

This is a distinct estimator/stage from the subsequent ridge mapping-only controls.

- Analyzer: [experiments/yang2025_replication_v1/results/analyzer.executed.py](../../experiments/yang2025_replication_v1/results/analyzer.executed.py), line 33.
- Protocol/freeze: [experiments/yang2025_replication_v1/protocol.json](../../experiments/yang2025_replication_v1/protocol.json), [experiments/yang2025_replication_v1/freeze_manifest.json](../../experiments/yang2025_replication_v1/freeze_manifest.json).
- Archived independent verification: [experiments/yang2025_replication_v1/results/verification/run_verification.json](../../experiments/yang2025_replication_v1/results/verification/run_verification.json), status `{"status": "PASS"}`.

### Early continual-information EEG

Scope: Appendix historical exploratory stage. Comparisons: Personal/shared updates and task/structural endpoint contrasts.

RNG: `default_rng(seed); shared integer indices (5000,n) per contrast`.

Archived stage uses 5000 resamples, not 10000. Models remain fixed.

- Analyzer: [experiments/continual_information_v1/eeg/results/analyzer.executed.py](../../experiments/continual_information_v1/eeg/results/analyzer.executed.py), line 30.
- Protocol/freeze: [experiments/continual_information_v1/protocol.json](../../experiments/continual_information_v1/protocol.json).
- Archived independent verification: [experiments/continual_information_v1/verification/eeg_verification.json](../../experiments/continual_information_v1/verification/eeg_verification.json), status `{"status": "PASS_ARTIFACT_MATH_AND_PROTOCOL_CHECKS"}`.

### Initial-readout diagnostics

Scope: Appendix. Comparisons: Initial-readout diagnostics.

RNG: `default_rng(seed).choice(paired differences,(10000,n),replace=True)`.

Exploratory data reuse. Shuffle allocations are sensitivity replicates; five shuffle outcomes are averaged within person for the pairing comparator.

- Analyzer: [experiments/information_mechanisms_v2/results/initial_refined/runner.executed.py](../../experiments/information_mechanisms_v2/results/initial_refined/runner.executed.py), line 64.
- Protocol/freeze: [experiments/information_mechanisms_v2/protocol.json](../../experiments/information_mechanisms_v2/protocol.json), [experiments/information_mechanisms_v2/freeze_manifest.json](../../experiments/information_mechanisms_v2/freeze_manifest.json).
- Archived independent verification: [experiments/information_mechanisms_v2/results/initial_refined/verification.json](../../experiments/information_mechanisms_v2/results/initial_refined/verification.json), status `{"status": "PASS"}`.

### Ridge true-pair/mismatch controls

Scope: Appendix. Comparisons: Ridge true-pair/mismatch controls.

RNG: `default_rng(20261004) reset per contrast/metric; integer indices (10000,n)`.

Exploratory data reuse. Shuffle allocations are sensitivity replicates; five shuffle outcomes are averaged within person for the pairing comparator.

- Analyzer: [experiments/information_mechanisms_v2/pairing/summarize.py](../../experiments/information_mechanisms_v2/pairing/summarize.py), line 38.
- Protocol/freeze: [experiments/information_mechanisms_v2/protocol.json](../../experiments/information_mechanisms_v2/protocol.json), [experiments/information_mechanisms_v2/freeze_manifest.json](../../experiments/information_mechanisms_v2/freeze_manifest.json).
- Archived independent verification: [experiments/information_mechanisms_v2/results/pairing/verification.json](../../experiments/information_mechanisms_v2/results/pairing/verification.json), status `{"status": "PASS_INDEPENDENT_PAIRING_RECONSTRUCTION"}`.

### Stieger/Yang history diagnostics

Scope: Appendix. Comparisons: Stieger/Yang history diagnostics.

RNG: `default_rng(2026100504) created per contrast collection; sequential draws across ordered contrasts/metrics`.

Exploratory data reuse. Shuffle allocations are sensitivity replicates; five shuffle outcomes are averaged within person for the pairing comparator.

- Analyzer: [experiments/information_mechanisms_v2/history/run_history.py](../../experiments/information_mechanisms_v2/history/run_history.py), line 96.
- Protocol/freeze: [experiments/information_mechanisms_v2/protocol.json](../../experiments/information_mechanisms_v2/protocol.json), [experiments/information_mechanisms_v2/freeze_manifest.json](../../experiments/information_mechanisms_v2/freeze_manifest.json).
- Archived independent verification: [experiments/information_mechanisms_v2/results/history/verification.json](../../experiments/information_mechanisms_v2/results/history/verification.json), status `{"status": "PASS_MATH_CAUSAL_TIMING_AND_SUMMARIES"}`.

### Label-budget and calibration policies

Scope: Main and appendix. Comparisons: 25% minus 0% feedback;100% minus 0%; final old score minus own initialization.

RNG: `default_rng(SeedSequence([seed,cohort_index,n,*sorted_person_ids])); shared (10000,n) indices`.

Main future benefit uses 25% versus 0%; old-test change uses each model own initialization. These are different reference contrasts.

- Analyzer: [experiments/reliability_budget_v1/eeg/analyze.py](../../experiments/reliability_budget_v1/eeg/analyze.py), line 13.
- Protocol/freeze: [experiments/reliability_budget_v1/eeg/protocol_fragment.json](../../experiments/reliability_budget_v1/eeg/protocol_fragment.json), [experiments/reliability_budget_v1/protocol.json](../../experiments/reliability_budget_v1/protocol.json), [experiments/reliability_budget_v1/freeze_manifest.json](../../experiments/reliability_budget_v1/freeze_manifest.json).
- Archived independent verification: [experiments/reliability_budget_v1/verification/eeg_analysis.json](../../experiments/reliability_budget_v1/verification/eeg_analysis.json), status `{"status": "PASS_INDEPENDENT_EEG_ANALYSIS"}`.

### Output-penalty retention

Scope: Appendix. Comparisons: Output-penalty versus own update; future and old-loss endpoints.

RNG: `default_rng(SeedSequence([seed,cohort_index,n,*sorted_person_ids])); shared (10000,n) indices`.

Exploratory reused Stieger development data.

- Analyzer: [experiments/reliability_followup_v2/eeg/analyze.py](../../experiments/reliability_followup_v2/eeg/analyze.py), line 11.
- Protocol/freeze: [experiments/reliability_followup_v2/eeg/protocol_fragment.json](../../experiments/reliability_followup_v2/eeg/protocol_fragment.json), [experiments/reliability_followup_v2/protocol.json](../../experiments/reliability_followup_v2/protocol.json), [experiments/reliability_followup_v2/freeze_manifest.json](../../experiments/reliability_followup_v2/freeze_manifest.json).
- Archived independent verification: [experiments/reliability_followup_v2/verification/eeg_analysis.json](../../experiments/reliability_followup_v2/verification/eeg_analysis.json), status `{"status": "PASS_INDEPENDENT_EEG_V2_ANALYSIS"}`.

### Feedback source and line constraint

Scope: Main and appendix. Comparisons: Other minus own; mixed minus own; line constraint minus own; replay controls.

RNG: `default_rng(SeedSequence([seed,cohort_index,n,*sorted_person_ids])); shared (10000,n) indices`.

Family correction applies only to all 62 future BA source contrasts. Nested 41 and all other endpoints are descriptive 95%. Donor assignments and teachers remain fixed. Original line CI uses this stage seed, not the v4 reference reanalysis seed.

Original Bonferroni family: Stieger all 62 future BA: other minus own and mixed minus own. Each of the two intervals has 97.5% coverage.

- Analyzer: [experiments/feedback_retention_v3/eeg/analyze.py](../../experiments/feedback_retention_v3/eeg/analyze.py), line 11.
- Protocol/freeze: [experiments/feedback_retention_v3/eeg/protocol_fragment.json](../../experiments/feedback_retention_v3/eeg/protocol_fragment.json), [experiments/feedback_retention_v3/protocol.json](../../experiments/feedback_retention_v3/protocol.json), [experiments/feedback_retention_v3/freeze_manifest.json](../../experiments/feedback_retention_v3/freeze_manifest.json).
- Archived independent verification: [experiments/feedback_retention_v3/verification/eeg_analysis.json](../../experiments/feedback_retention_v3/verification/eeg_analysis.json), status `{"status": "PASS_INDEPENDENT_EEG_V3_ANALYSIS"}`.

### Full-space risk constraint

Scope: Main retention table and appendix. Comparisons: Full-space minus own; full-space minus line; reused references.

RNG: `default_rng(SeedSequence([seed,cohort_index,n,*sorted_person_ids])); shared (10000,n) indices`.

Exploratory Stieger reuse. Both retention criteria retain their original 95% intervals. The manuscript original v3 line interval retains its own seed.

- Analyzer: [experiments/confirmation_prior_constraints_v4/eeg/analyze.py](../../experiments/confirmation_prior_constraints_v4/eeg/analyze.py), line 10.
- Protocol/freeze: [experiments/confirmation_prior_constraints_v4/eeg/PROTOCOL.md](../../experiments/confirmation_prior_constraints_v4/eeg/PROTOCOL.md), [experiments/confirmation_prior_constraints_v4/eeg/protocol_fragment.json](../../experiments/confirmation_prior_constraints_v4/eeg/protocol_fragment.json), [experiments/confirmation_prior_constraints_v4/freeze_eeg.json](../../experiments/confirmation_prior_constraints_v4/freeze_eeg.json).
- Archived independent verification: [experiments/confirmation_prior_constraints_v4/verification/eeg_analysis.json](../../experiments/confirmation_prior_constraints_v4/verification/eeg_analysis.json), status `{"status": "PASS_INDEPENDENT_EEG_V4_ANALYSIS"}`.

### Farabbi source and retention evaluation

Scope: Appendix. Comparisons: Other/mixed minus own future BA; line/full-space minus own and each other.

RNG: `default_rng(SeedSequence([2026100821,n,*subjects])); shared (10000,n) indices`.

Only source future-BA contrasts use 97.5%. Other endpoints and retention comparisons use 95%. Day 3 future and permanent day 1 old tests are separate endpoints.

Original Bonferroni family: Farabbi future BA: other minus own and mixed minus own; separate from Stieger family. Each of the two intervals has 97.5% coverage.

- Analyzer: [experiments/confirmation_prior_constraints_v4/confirmation/analyze.py](../../experiments/confirmation_prior_constraints_v4/confirmation/analyze.py), line 22.
- Protocol/freeze: [experiments/confirmation_prior_constraints_v4/confirmation/protocol_fragment.json](../../experiments/confirmation_prior_constraints_v4/confirmation/protocol_fragment.json), [experiments/confirmation_prior_constraints_v4/freeze_confirmation.json](../../experiments/confirmation_prior_constraints_v4/freeze_confirmation.json).
- Archived independent verification: [experiments/confirmation_prior_constraints_v4/verification/confirmation_analysis.json](../../experiments/confirmation_prior_constraints_v4/verification/confirmation_analysis.json), status `{"status": "PASS_INDEPENDENT_CONFIRMATION_ANALYSIS"}`.

### Initial-training classification diagnosis

Scope: Appendix training-only development. Comparisons: Initial-training classification diagnosis.

RNG: `default_rng(SeedSequence([seed,n,*sorted_valid_person_ids])); shared paired indices (10000,n)`.

Outer-fold predictions are pooled within participant; folds are not independent units. All 240 original training labels remain available to model selection, including across dose comparisons.

- Analyzer: [experiments/diagnostics_generalization_v5/classification/analyze.py](../../experiments/diagnostics_generalization_v5/classification/analyze.py), line 18.
- Protocol/freeze: [experiments/diagnostics_generalization_v5/classification/protocol_fragment.json](../../experiments/diagnostics_generalization_v5/classification/protocol_fragment.json), [experiments/diagnostics_generalization_v5/freeze_classification.json](../../experiments/diagnostics_generalization_v5/freeze_classification.json).
- Archived independent verification: [experiments/diagnostics_generalization_v5/verification/classification_analysis.json](../../experiments/diagnostics_generalization_v5/verification/classification_analysis.json), status `{"status": "PASS"}`.

### Initial-training retention diagnosis

Scope: Appendix training-only development. Comparisons: Initial-training retention diagnosis.

RNG: `default_rng(SeedSequence([seed,n,*sorted_valid_person_ids])); shared paired indices (10000,n)`.

Outer-fold predictions are pooled within participant before metrics; folds are not independent units. S 2/S 6 retention snapshots use the same people and draws. Final v6 retention uses R 2; original/R 1 failures remain archived.

- Analyzer: [experiments/diagnostics_generalization_v5/retention/analyze.py](../../experiments/diagnostics_generalization_v5/retention/analyze.py), line 17.
- Protocol/freeze: [experiments/diagnostics_generalization_v5/retention/protocol_fragment.json](../../experiments/diagnostics_generalization_v5/retention/protocol_fragment.json), [experiments/diagnostics_generalization_v5/freeze_retention.json](../../experiments/diagnostics_generalization_v5/freeze_retention.json).
- Archived independent verification: [experiments/diagnostics_generalization_v5/verification/retention_analysis.json](../../experiments/diagnostics_generalization_v5/verification/retention_analysis.json), status `{"status": "PASS_INDEPENDENT_RETENTION_ANALYSIS_V5"}`.

### Expanded-regularization control

Scope: Appendix training-only development. Comparisons: Expanded-regularization control.

RNG: `default_rng(SeedSequence([seed,n,*sorted_valid_person_ids])); shared paired indices (10000,n)`.

Outer-fold predictions are pooled within participant; folds are not independent units. All 240 original training labels remain available to model selection, including across dose comparisons.

- Analyzer: [experiments/closure_controls_v6/classification/analyze.py](../../experiments/closure_controls_v6/classification/analyze.py), line 14.
- Protocol/freeze: [experiments/closure_controls_v6/classification/protocol_fragment.json](../../experiments/closure_controls_v6/classification/protocol_fragment.json), [experiments/closure_controls_v6/freeze_classification.json](../../experiments/closure_controls_v6/freeze_classification.json).
- Archived independent verification: [experiments/closure_controls_v6/verification/classification_analysis.json](../../experiments/closure_controls_v6/verification/classification_analysis.json), status `{"status": "PASS_INDEPENDENT_CLASSIFICATION_ANALYSIS_V6"}`.

### Replay/radius controls final R 2

Scope: Appendix training-only development. Comparisons: Replay/radius controls final R 2.

RNG: `default_rng(SeedSequence([seed,n,*sorted_valid_person_ids])); shared paired indices (10000,n)`.

Outer-fold predictions are pooled within participant before metrics; folds are not independent units. S 2/S 6 retention snapshots use the same people and draws. Final v6 retention uses R 2; original/R 1 failures remain archived.

- Analyzer: [experiments/closure_controls_v6/revisions/retention_r2/analyze.py](../../experiments/closure_controls_v6/revisions/retention_r2/analyze.py), line 18.
- Protocol/freeze: [experiments/closure_controls_v6/revisions/retention_r2/protocol_fragment.json](../../experiments/closure_controls_v6/revisions/retention_r2/protocol_fragment.json), [experiments/closure_controls_v6/freeze_retention_r2.json](../../experiments/closure_controls_v6/freeze_retention_r2.json).
- Archived independent verification: [experiments/closure_controls_v6/verification/retention_analysis.json](../../experiments/closure_controls_v6/verification/retention_analysis.json), status `{"status": "PASS_INDEPENDENT_RETENTION_V6_ANALYSIS"}`.

### Finite correctness/persistence reference

Scope: Appendix. Comparisons: Four arms and fixed factorial contrasts.

RNG: `Generator(PCG64DXSM(SeedSequence([bootstrap_seed,group_code])));10000 group_n indices; codes0/1/2/3`.

Participant intervals use fixed person-specific finite-model probabilities, teachers and fitted probability/persistence models. Individual unconditional probabilities have separate Wilson 95 Monte Carlo intervals with 32768 repetitions. Conditional recovery ratios use actual failure denominators, are per-person descriptive, and are excluded from group bootstrap and paired contrasts. Qualification retains original observed identities.

- Analyzer: [experiments/prior_reliability_v7/reliability/analyze.py](../../experiments/prior_reliability_v7/reliability/analyze.py), line 88.
- Protocol/freeze: [experiments/prior_reliability_v7/reliability/protocol_fragment.json](../../experiments/prior_reliability_v7/reliability/protocol_fragment.json), [experiments/prior_reliability_v7/freeze_reliability.json](../../experiments/prior_reliability_v7/freeze_reliability.json).
- Archived independent verification: [experiments/prior_reliability_v7/verification/reliability_analysis.json](../../experiments/prior_reliability_v7/verification/reliability_analysis.json), status `{"status": "PASS_INDEPENDENT_RELIABILITY_V7_ANALYSIS"}`.

## Retention criterion and statistical dependence

The original joint rule requires both a future-BA difference lower 95% bound of at least−0.005 and an old-loss-proportion difference upper 95% bound below zero, each relative to the unconstrained personal update. Old-score loss is at least 5 percentage points below each model own initialization. The original 95% intervals are retained; this documentation does not create a new 97.5% family.

Repeated Stieger sessions are summarized within participant. The two training-only retention snapshots use the same people; disjoint outer-fold predictions are pooled before person-level metrics. Shared teachers, fitted models and donor assignments remain fixed during participant resampling. These intervals do not estimate uncertainty from refitting shared models or sampling new donor pools.

## Simulation intervals

Simulation intervals use independent trajectory endpoints and the normal Monte Carlo formula mean ±1.959963984540054 × sample standard deviation (ddof=1) /sqrt(n). Within-path differences are formed first; repeated proposal seeds are averaged within path. These are pointwise descriptive intervals, without multiple-comparison adjustment. No participant bootstrap is used.

| Stage | Paths | Recorded random seeds | Notes |
|---|---:|---|---|
| continual_information_v1 | 512 | `{"seed": 2026100201}` | Known-data base seed; unknown-data seed+100; true candidate allocation seed+101. |
| reliability_budget_v1 | 512 | `{"seed": 2026100502}` | All 21 conditions; original three-step failure rule. |
| reliability_followup_v2 | 512 | `{"seed": 2026100602}` | Independent null calibration uses 4096 trajectories, seed 2026100601 and fixed rank 3893. Null validation proportions use Wilson 95, not a bootstrap. |
| feedback_retention_v3 | 512 | `{"seed": 2026100702, "proposal_seed": 2026100703}` | 1024-particle sensitivity uses 8 fixed paths, kept separate from 512 primary paths. |
| confirmation_prior_constraints_v4 | 512 | `{"seed": 2026100802, "proposal_seeds": [2026100803, 2026100813, 2026100823, 2026100833]}` | Primary 512; repeated 512/1024-particle diagnostics use 32 fixed paths; four algorithm seeds averaged within path. |
| diagnostics_generalization_v5 | 32 | `{"proposal_seeds": [2026100903, 2026100913, 2026100923, 2026100933], "measurement_seed": 2026100904, "random_capacity": 4096}` | Four proposal seeds averaged within each fixed trajectory, not 128 independent trajectories. |
| closure_controls_v6 | 32 | `{"proposal_seeds": [2026100903, 2026100913, 2026100923, 2026100933], "measurement_seed": 2026100904, "random_capacity": 4096}` | Reuses v5 paths, observations, algorithm seeds and references;32 independent data units. |
| prior_reliability_v7 | 32 | `{"proposal_seeds": [2026100903, 2026100913, 2026100923, 2026100933], "random_capacity": 4096}` | 16 primary 4096-particle alternative-minus-baseline prior contrasts.2048 is sensitivity.20 numerical-stability cells are operational diagnostics, not hypothesis tests. |

- **continual_information_v1**: [experiments/continual_information_v1/dynamics/run_dynamics.py](../../experiments/continual_information_v1/dynamics/run_dynamics.py), line 210; [protocol](../../experiments/continual_information_v1/dynamics/config.json); [archived verification](../../experiments/continual_information_v1/verification/dynamics_verification.json).

- **reliability_budget_v1**: [experiments/reliability_budget_v1/dynamics/analyze.py](../../experiments/reliability_budget_v1/dynamics/analyze.py), line 15; [protocol](../../experiments/reliability_budget_v1/results/dynamics/protocol.executed.json); [archived verification](../../experiments/reliability_budget_v1/verification/dynamics_analysis.json).

- **reliability_followup_v2**: [experiments/reliability_followup_v2/dynamics/analyze.py](../../experiments/reliability_followup_v2/dynamics/analyze.py), line 14; [protocol](../../experiments/reliability_followup_v2/results/dynamics/protocol.executed.json); [archived verification](../../experiments/reliability_followup_v2/verification/dynamics_analysis.json).

- **feedback_retention_v3**: [experiments/feedback_retention_v3/dynamics/analyze.py](../../experiments/feedback_retention_v3/dynamics/analyze.py), line 13; [protocol](../../experiments/feedback_retention_v3/results/dynamics/protocol.executed.json); [archived verification](../../experiments/feedback_retention_v3/verification/dynamics_analysis.json).

- **confirmation_prior_constraints_v4**: [experiments/confirmation_prior_constraints_v4/dynamics/analyze.py](../../experiments/confirmation_prior_constraints_v4/dynamics/analyze.py), line 9; [protocol](../../experiments/confirmation_prior_constraints_v4/results/dynamics/protocol.executed.json); [archived verification](../../experiments/confirmation_prior_constraints_v4/verification/dynamics_analysis.json).

- **diagnostics_generalization_v5**: [experiments/diagnostics_generalization_v5/dynamics/analyze.py](../../experiments/diagnostics_generalization_v5/dynamics/analyze.py), line 10; [protocol](../../experiments/diagnostics_generalization_v5/results/dynamics/protocol.executed.json); [archived verification](../../experiments/diagnostics_generalization_v5/verification/dynamics_analysis.json).

- **closure_controls_v6**: [experiments/closure_controls_v6/dynamics/analyze.py](../../experiments/closure_controls_v6/dynamics/analyze.py), line 9; [protocol](../../experiments/closure_controls_v6/results/dynamics/protocol.executed.json); [archived verification](../../experiments/closure_controls_v6/verification/dynamics_analysis.json).

- **prior_reliability_v7**: [experiments/prior_reliability_v7/dynamics/analyze.py](../../experiments/prior_reliability_v7/dynamics/analyze.py), line 10; [protocol](../../experiments/prior_reliability_v7/results/dynamics/protocol.executed.json); [archived verification](../../experiments/prior_reliability_v7/verification/dynamics_analysis.json).

## Archived software versions

Version values below come only from saved records. Their roles are preserved: freeze/preflight environment, feature preparation, production identity or independent verification. A feature-preparation version is not relabeled as an analysis runtime. Missing values remain unavailable; the current environment and the paper reproduction environment are not used as substitutes.

### lee_development

- archived pilot environment: python `3.12.14`; numpy `2.5.3`; scipy `1.18.1`; sklearn `1.9.1`; torch `2.14.0+cu132`; mne `1.13.2`; moabb `1.7.2`. [Source](../../experiments/lee2019_erp_pilot/environment.json).
- archived diagnostic environment: python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; torch `2.14.0+cu132`; numpy `2.5.3`; sklearn `1.9.1`. [Source](../../experiments/lee2019_erp_diagnostics_v1/environment.json).
### lee_history

- archived feature-preparation environment; analysis runtime separately unavailable: python `3.12.14`; moabb `1.7.2`; mne `1.13.2`; numpy `2.5.3`; scipy `1.18.1`. [Source](../../experiments/lee2019_erp_history_v1/data/preparestatus.json).
- Unavailable in the listed historical records: torch.
### yang_original

- production identity: torch `2.14.0+cu132`; numpy `2.5.3`. [Source](../../experiments/yang2025_replication_v1/results/run_identity.json).
- Unavailable in the listed historical records: python, scipy.
### continual_information_v1

- archived EEG execution environment: torch `2.14.0+cu132`; numpy `2.5.3`. [Source](../../experiments/continual_information_v1/eeg/results/environment.json).
- Unavailable in the listed historical records: python, scipy.
### information_mechanisms_v2

- initial production identity: torch_version `2.14.0+cu132`; numpy_version `2.5.3`. [Source](../../experiments/information_mechanisms_v2/results/initial_refined/identity.json).
- pairing production identity: torch `2.14.0+cu132`; numpy `2.5.3`. [Source](../../experiments/information_mechanisms_v2/results/pairing/run_identity.json).
- history production identity: torch_version `2.14.0+cu132`; numpy_version `2.5.3`. [Source](../../experiments/information_mechanisms_v2/results/history/run_identity.json).
- Unavailable in the listed historical records: python, scipy.
### reliability_budget_v1

- archived preflight: python `3.12.14`; numpy `2.5.3`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/reliability_budget_v1/preflight.json).
- EEG production identity: torch `2.14.0+cu132`; numpy `2.5.3`. [Source](../../experiments/reliability_budget_v1/results/eeg/run_identity.json).
- dynamics production identity: torch `2.14.0+cu132`; numpy `2.5.3`. [Source](../../experiments/reliability_budget_v1/results/dynamics/run_identity.json).
- Unavailable in the listed historical records: scipy.
### reliability_followup_v2

- archived preflight: python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; numpy `2.5.3`; scipy `1.18.1`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/reliability_followup_v2/preflight.json).
- EEG production identity: torch `2.14.0+cu132`; numpy `2.5.3`. [Source](../../experiments/reliability_followup_v2/results/eeg/run_identity.json).
- dynamics production identity: torch `2.14.0+cu132`; numpy `2.5.3`. [Source](../../experiments/reliability_followup_v2/results/dynamics/run_identity.json).
### feedback_retention_v3

- archived preflight: python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; numpy `2.5.3`; scipy `1.18.1`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/feedback_retention_v3/preflight.json).
- EEG production identity: torch `2.14.0+cu132`; numpy `2.5.3`. [Source](../../experiments/feedback_retention_v3/results/eeg/run_identity.json).
- dynamics production identity: torch `2.14.0+cu132`; numpy `2.5.3`. [Source](../../experiments/feedback_retention_v3/results/dynamics/run_identity.json).
### confirmation_prior_constraints_v4

- archived stage freeze: python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; numpy `2.5.3`; scipy `1.18.1`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/confirmation_prior_constraints_v4/freeze_eeg.json).
- archived stage freeze: python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; numpy `2.5.3`; scipy `1.18.1`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/confirmation_prior_constraints_v4/freeze_confirmation.json).
- archived stage freeze: python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; numpy `2.5.3`; scipy `1.18.1`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/confirmation_prior_constraints_v4/freeze_dynamics.json).
- dynamics production identity: torch `2.14.0+cu132`; numpy `2.5.3`. [Source](../../experiments/confirmation_prior_constraints_v4/results/dynamics/run_identity.json).
### diagnostics_generalization_v5

- archived stage freeze: python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; numpy `2.5.3`; scipy `1.18.1`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/diagnostics_generalization_v5/freeze_classification.json).
- archived stage freeze: python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; numpy `2.5.3`; scipy `1.18.1`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/diagnostics_generalization_v5/freeze_retention.json).
- archived stage freeze: python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; numpy `2.5.3`; scipy `1.18.1`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/diagnostics_generalization_v5/freeze_dynamics.json).
- dynamics production identity: torch `2.14.0+cu132`; numpy `2.5.3`. [Source](../../experiments/diagnostics_generalization_v5/results/dynamics/run_identity.json).
### closure_controls_v6

- archived stage freeze: python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; numpy `2.5.3`; scipy `1.18.1`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/closure_controls_v6/freeze_classification.json).
- archived stage freeze (original retention freeze retained through R 2): python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; numpy `2.5.3`; scipy `1.18.1`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/closure_controls_v6/freeze_retention.json).
- archived stage freeze: python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; numpy `2.5.3`; scipy `1.18.1`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/closure_controls_v6/freeze_dynamics.json).
- dynamics production identity: torch `2.14.0+cu132`; numpy `2.5.3`. [Source](../../experiments/closure_controls_v6/results/dynamics/run_identity.json).
### prior_reliability_v7

- archived stage freeze: python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; numpy `2.5.3`; scipy `1.18.1`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/prior_reliability_v7/freeze_reliability.json).
- archived stage freeze: python `3.12.14 (main, Sep  2 2026, 23:27:36) [GCC 15.3.0]`; numpy `2.5.3`; scipy `1.18.1`; torch `2.14.0+cu132`; cuda `13.2`. [Source](../../experiments/prior_reliability_v7/freeze_dynamics.json).
- dynamics production identity: torch `2.14.0+cu132`; numpy `2.5.3`. [Source](../../experiments/prior_reliability_v7/results/dynamics/run_identity.json).
- reliability production identity: numpy_version `2.5.3`; torch_version `2.14.0+cu132`. [Source](../../experiments/prior_reliability_v7/results/reliability/run_identity.json).

## Documentation audit

The registry contains 18 participant-analysis entries, 8 simulation entries and 121 source files. All listed files exist and their source hashes were checked during generation. Archived verification outcomes were read rather than rerun. This record adds no new fitted model, bootstrap sample, numerical interval or comparison family.
