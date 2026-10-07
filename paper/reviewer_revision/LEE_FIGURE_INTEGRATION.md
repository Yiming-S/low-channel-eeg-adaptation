# Lee primary figure: four-panel revision

Run from the research/package root:

```bash
python3 paper/reviewer_revision/generate_lee_primary_figure.py
```

The script writes:

- `paper/reviewer_revision/lee_figure.tex`: complete, standalone-compatible inline figure with the existing `fig:eeg-lee-endpoints` label.
- `paper/figures/eeg_lee_primary_contrasts.png` and `.pdf`: 15 × 11.7 cm figure exports, not a manuscript PDF.
- `paper/figures/lee_primary_figure_data.json`: exact source/value/pointer/hash records, derived display arrays, transformations and preservation checks.

The source is the original `results/pilot_summary_groups.json`, group `confirmation`, plus each of the 42 participant summary files. The script uses saved intervals and never resamples or fits a model. The first three inline axes are extracted from `lee_original_figure_template.tex`; their complete plot/node payloads are unchanged. Only axis layout and the redundant zero tick label in panel c change. This fixed template is an explicit input and prevents repeatedly appending panel d when the current manuscript is updated.

## Integration

1. Replace the one complete `fig:eeg-lee-endpoints` figure in `paper/manuscript.tex` with `lee_figure.tex`. Do not append a second figure with that label. The history figure remains unchanged.
2. Add `paper/reviewer_revision/generate_lee_primary_figure.py` to `paper/make_figures.py` using `runpy.run_path` after the existing generators. The original six-panel `eeg_lee_endpoints` export and EEG generator remain intact for the archived combined view and history content.
3. Add `eeg_lee_primary_contrasts` as the twelfth scientific export stem in `paper/reproducibility/run.py`. Copy/catalogue both this new generator and `lee_original_figure_template.tex` in isolated builds. Do not derive the template from the runtime manuscript.
4. Ensure `paper/figures/lee_primary_figure_data.json` is inventoried before isolated staging. All 43 JSON source dependencies are discoverable through its `records`. `text_sources` supplies the template path/hash, and `generator`/`generator_sha256` supplies the executable path/hash.
5. Existing `paper/validate_figures.py` already discovers `paper/figures/*figure_data.json` and checks each standard record. Add the new export to any explicit export-presence inventory; retain the existing label/citation checks. The figure-data validation reports preserve the first three payload hashes and retain all 42 source IDs for each contrast.
6. Update the current README's scientific export count and inventory from eleven to twelve. The number of manuscript figure environments remains unchanged because this replaces one figure.

No modification of the already published v1.0.0 release is part of this revision.

## New panel values

All values are AUC differences in the original 0–1 scale. Each shuffled comparator is the within-participant mean across five original assignments.

| Saved contrast | Mean | Original descriptive paired 95% interval |
|---|---:|---|
| True pairs − frozen mapping | −0.002200286596119919 | [−0.00967555665784833, 0.004021200764256343] |
| True pairs − mean class shuffle | 0.014272912992357448 | [0.005472164535567315, 0.022980160934744264] |

The source keys are `/groups/confirmation/contrasts/future:mapped_true_pairs-mapped_frozen:auc` and `/groups/confirmation/contrasts/future:mapped_true_pairs-shuffle_average:auc`. Panel d plots their stored `individual`, `difference` and `ci95` fields. Individual offsets have no statistical meaning. No confidence statement is assigned to an individual dot.
