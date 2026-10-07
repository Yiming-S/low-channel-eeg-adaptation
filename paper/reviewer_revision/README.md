# Four manuscript revisions from existing results

The current manuscript adds empirical contribution statements, Lee participant-level distribution summaries, class-specific Stieger old-test resolution and paired prediction changes, and a fourth Lee figure panel. All original participants, principal estimates, interval bounds, evidence roles and the five-percentage-point severe-decline threshold are retained.

## Lee distribution

From the research root:

```bash
python3 paper/reviewer_revision/recompute_lee_distribution.py --self-test --out /tmp/lee_distribution_check.json
```

The standard-library script reads the 42 original-event participant summaries and their archived group contrasts. It checks 186 numeric equalities and records 700 source values with JSON pointers and file hashes. The added quantities are strict directions of observed changes and participant 24's share of the signed net MSE reduction. It performs no fitting, resampling or significance test.

## Stieger fixed old-test records

```bash
python3 paper/reviewer_revision/old_test_trial_audit.py --source-root . --out-dir /tmp/old_test_check
```

The compact input retains trial identities, binary labels and initialized/final predictions from the original 25%-label shared-model experiment. The later v3 archive supplies labels only, after exact trial-identity and order checks; no v3 model score is used. The audit recomputes class-specific counts, balanced accuracy and paired correctness transitions for all 62 participants and checks them against the original metrics. The two inline tables are generated in `old_test_trial_tables.tex`.

The script and `old_test_trial_inputs.json` can also be copied together to an independent directory and run without `--source-root`. That execution verifies the compact-input arithmetic and archived metric records. Checking the compact input against the original prediction-array hashes and selected values requires the research checkout and `--source-root`.

A correctness flip in class c changes balanced accuracy by 50/n_c percentage points. The new tables describe score changes on the fixed held-out trials. They do not estimate individual population risk or replace the original group intervals.

## Lee main figure

```bash
python3 paper/reviewer_revision/generate_lee_primary_figure.py
```

The generator retains the original three panels' inline plotting payloads and adds all 42 mapped-classifier differences against frozen mapping and the within-person mean of five class-preserving shuffles. The original means and 95% intervals are read directly from the archived results. `lee_figure.tex` is inserted into the standalone manuscript; PNG/PDF exports and 908 source-value records are under `paper/figures/`.

The revised generator is also included in `paper/reproducibility/run.py`'s isolated figure build. Version v1.1.0 includes these descriptive inputs, scripts, evidence and the revised figure. The original combined six-panel export and v1.0.0 archive are retained.

`manuscript_before_four_items.tex` records the source immediately before these four changes. These descriptive additions require no new EEG acquisition or model training.
