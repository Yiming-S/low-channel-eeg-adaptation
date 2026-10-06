# Reproduction from archived results

This entry point rebuilds the paper's **11 scientific figure exports** from saved analysis artifacts and checks each recorded source value and file hash. It invokes the existing figure generators and validator. All outputs are written under `paper/reproducibility/builds/`; the archived results and canonical paper files are read-only inputs to this workflow. The current manuscript splits some exported panels between the main text and appendices: its 14 figure environments are not 14 separate exported files.

The manuscript contains an additional information-timing schematic written directly in LaTeX. Its source is included in the label, citation, and standalone-document checks. The reproduction entry point does not compile the manuscript.

## Run

Use Python 3.10 or later in an environment containing the packages in `requirements.txt`. The checked local environment is CPython 3.10.5, NumPy 2.2.6, and Matplotlib 3.10.8. No GPU, PyTorch, network access, or TeX installation is required for this archived-results workflow.

From the repository root:

```bash
python3 -m pip install -r paper/reproducibility/requirements.txt
python3 paper/reproducibility/run.py --action build --staging copy
```

Use the first command only when preparing an environment. The build command performs four steps:

1. Discover the archived inputs through the existing evidence manifests, all `paper/*evidence.json` files, and the figure-data records. This includes the editorial evidence and its original JSON and text sources.
2. Record the current input sizes and SHA-256 hashes in `input_manifest.json` and compare them with the hashes already declared in the evidence.
3. Create an isolated tree and run the existing `paper/make_figures.py`, which calls the EEG, retention, dynamics, and feedback-source figure scripts.
4. Run the existing `paper/validate_figures.py`, check that all 11 PNG/PDF pairs exist, and confirm that the canonical input files have not changed during execution.

Two smaller actions are available:

```bash
python3 paper/reproducibility/run.py --action manifest
python3 paper/reproducibility/run.py --action check --staging copy
```

`manifest` inventories the current files and checks their declared hashes. `check` uses the existing canonical figure exports and runs the pointer/hash and manuscript-source checks in an isolated tree without rendering figures again. Each command exits with a nonzero status if a required file or a checked value/hash is inconsistent.

## Inspect the output

`last_run.json` points to the latest run and records the commands, runtime versions, validation counts, unchanged-input check, and output hashes. Each build retains its own `input_manifest.json`, `run_report.json`, standard-output and error logs, generated figure-data JSON, inline LaTeX fragments, PNG/PDF exports, and original validator report.

The output directory has this layout:

```text
paper/reproducibility/builds/<UTC timestamp>/
  input_manifest.json
  run_report.json
  make_figures.stdout.log
  make_figures.stderr.log
  validate_figures.stdout.log
  validate_figures.stderr.log
  paper/
    figures/                    # 11 scientific PNG/PDF pairs and provenance JSON
    figure_blocks_*.tex          # generated inline coordinates
    figure_validation.json
    figure_source_manifest.json
```

With `--staging copy`, the wrapper copies the six existing Python figure/validation sources and their inputs into an isolated output tree. The build then contains no hard links or symbolic links. It does not maintain a second implementation. The optional `--staging links` mode, retained for the original local workflow, uses hard links to scripts and symbolic links to read-only inputs; use the copy mode when checking an extracted release.

The existing validator checks exact source JSON values, recorded source hashes, exported-file presence, manuscript labels and citations, and the absence of external file dependencies in the standalone LaTeX source. This run does not repeat the experiments' independent mathematical verification or compile and visually inspect the manuscript. PDF metadata and rendering libraries can change output bytes across machines; recorded source values and hashes provide the numeric reproducibility checks, while each run records the hashes of its own exports.

## Figure inventory

The names below are stable export identifiers; the manuscript controls figure numbering and placement.

| Export stem | Evidence shown |
|---|---|
| `update_layers` | State, dynamics, and observation-map update controls |
| `eeg_budget_calibration` | Label budgets and equal-pair-budget calibration timing |
| `eeg_pairing_forest` | True-pair and class-shuffled target predictions |
| `eeg_lee_endpoints` | Lee task and omitted-target endpoints and legal history |
| `feedback_source` | Own, other-person, and mixed feedback |
| `retention_heterogeneity` | Individual retention and future-task changes |
| `retention_tradeoffs` | Training-risk constraints and retention tradeoffs |
| `dynamics_history_schedules` | History information and high-observation schedules |
| `dynamics_parameter_information` | Exact and noisy parameter measurements |
| `dynamics_prior_stability` | Prior sensitivity and particle-scale diagnostics |
| `dynamics_reliability_reference` | Model-based and EEG sampling references |

## From figures back to experiments

`pipeline_catalog.json` records the actual protocols and execution entry points for the EEG and dynamical-model experiment families. The catalogue includes the final `closure_controls_v6/revisions/retention_r2` retention revision. These paths are inventoried for inspection; the figure build does not execute them.

An end-to-end EEG rerun starts from each dataset's acquisition and preprocessing pipeline, pinned feature/model inputs, and frozen stage protocol. The Stieger entry points are under `experiments/reve_stieger2021/`; Lee acquisition and history preparation are under `experiments/lee2019_erp_history_v1/`; Yang preparation and execution are under `experiments/yang2025_replication_v1/`; Farabbi confirmation is under `experiments/confirmation_prior_constraints_v4/confirmation/`. Later stages consume the earlier verified features, identities, models, and feedback records specified by their protocol and execution manifests.

Those experiments used an Ubuntu execution environment, including `/home/ys/fast/envs/reve-test/bin/python`, stage runs under `/home/ys/fast/runs/`, and dataset-specific raw files and caches. Their input manifests bind the required files. A complete raw-data rerun requires acquiring the dataset distributions and reconstructing those stage inputs. The local figure-reproduction run does not establish that raw EEG preprocessing, feature extraction, or model fitting has been replayed.

## Input format and portable package

`INPUT_FORMAT.md` describes the result/evidence records and relative-path layout. `input_manifest.json` is a machine-readable inventory of the currently available source, archived-result, protocol, and inspection files, with separate roles for files executed, read, or merely catalogued.

The release builder creates a **portable archived-results package** with ordinary files at their original relative paths. It does not package the original link-based build directories. From a complete research checkout:

```bash
python3 paper/reproducibility/build_release.py --inventory-only
python3 paper/reproducibility/build_release.py
```

The second command copies the required archived results, figure scripts and evidence documents; available experiment source, frozen protocols and environment records; current statistical-methods documents; and bibliographic verification records. It creates a gzip-compressed tar archive under `paper/releases/`, extracts it into a temporary directory outside the research tree, and actually runs both `build` and `check` with `--staging copy`. When the independent primary-statistics entry point is present, it also runs that entry point against the packaged original sources, including its arithmetic self-tests. During these runs, a Python audit hook refuses reads from the original checkout and network connections. Source hashes are checked before and after the run. A race with a concurrent source edit or dependency addition fails the build instead of labeling mixed versions as verified.

`paper/releases/latest_release.json` names the latest successfully tested archive and its matching `.verification.json`, `.manifest.json`, and `.sha256` sidecars. Earlier archives are retained. Inside an archive, `RELEASE_MANIFEST.json` binds every packaged input/source file and `SOURCE_INVENTORY.json` lists the available experiment code, static imports, historical absolute paths, and missing runtime inputs. The manifest excludes its own hash to avoid a circular definition; the archive checksum covers it.

An optional `paper/reproducibility/release_metadata.json` supplies `archive_slug`, `version`, and `repository_url` for a versioned filename. Without that file, names use a UTC timestamp. The builder refuses to overwrite an existing archive. Repository metadata identifies the intended destination; the separate upload verification establishes whether the public release actually exists.

After extracting an archive, enter its top-level directory and run the commands in **Run** above. No access to the author's research directory is required. The included source manuscript is checked but is not compiled; no new manuscript PDF is produced.

## Coverage of reported results

The included JSON summaries, participant-level metrics and evidence records retain the inputs used by the figures and the recorded numerical evidence for the main and appendix tables. Original values, units, participant/cohort identities, interval bounds, and source hashes remain intact. The package is sufficient to regenerate the figure exports and audit these saved reported values. Inline table formatting and the timing schematic remain in `paper/manuscript.tex`.

`PRIMARY_STATISTICS.md` specifies the separately implemented primary-statistics route. It reconstructs the selected primary participant-bootstrap intervals from compact saved participant/session metrics and retained resampling definitions, without fitting a model. Run it with:

```bash
python3 paper/reproducibility/recompute_primary_statistics.py --source-root . --self-test --out primary_statistics_report.json
```

The package does **not** re-estimate every manuscript statistic from trial-level observations. Repeating other stage-specific bootstrap procedures or independent model-verification calculations requires inputs such as predictions, feature arrays and fitted models that are excluded from this package. Those archived intervals and verification reports remain available for inspection. The source inventory includes analysis, training and verification implementations, but only the figure-generation, pointer/hash-check and explicitly documented primary-statistics entry points are exercised by the release test.

Raw EEG, feature caches, encoder weights, fitted-model arrays and the multi-gigabyte prediction archives are not included. Third-party dataset acquisition remains governed by the original repositories and their access terms. Historical absolute paths in experiment code and freeze records document the execution environment; they are not dependencies of the archived-results figure build. Source and data licensing and the external repository location must be finalized before public distribution. Creating the package does not upload it or assign a public URL or DOI.
