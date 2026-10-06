# Required archived inputs

The rendering scripts consume the existing saved JSON artifacts in their original schemas. The reproduction wrapper discovers their paths; it does not convert results to a new experimental schema. Keep the repository-relative paths listed in `input_manifest.json` when moving an archive to another checkout. A portable release uses `RELEASE_MANIFEST.json` to bind the complete packaged file set; its extraction preserves these paths without links.

## Evidence record

Figure-data files use records with these fields:

```json
{
  "source": "experiments/<study>/<stage>/analysis.json",
  "json_pointer": "/groups/all/metric/mean",
  "value": 0.5,
  "units": "example unit; use the actual source endpoint",
  "sha256": "<SHA-256 of the complete source file>"
}
```

This example describes the format and is not a study result. `value` stores the exact original JSON value: a scalar, string, Boolean, list, or object. `json_pointer` follows RFC 6901: array positions are numeric tokens; `~1` escapes `/`, and `~0` escapes `~`. `source` is relative to the research repository root. Values can be nested under an `evidence` or `records` collection. Figure transformations and panel metadata are stored separately from the original records.

Some earlier evidence records omit `sha256`; their original files are bound by the source manifest. Some metadata also supplies a path-keyed `sources` dictionary or a `text_sources` list with line ranges and hashes. The wrapper inventories those sources as well.

## Source manifests

`paper/evidence_manifest.json` and `paper/figure_source_manifest.json` contain a `files` list:

```json
{
  "files": [
    {
      "path": "experiments/<study>/<stage>/analysis.json",
      "bytes": 1234,
      "sha256": "<SHA-256 of the complete file>"
    }
  ]
}
```

The wrapper verifies the original declared hashes before staging inputs. The validator regenerates its figure-source manifest inside the isolated build.

## Minimal layout for rendering and checking

The required material consists of:

- The six existing Python files listed in `run.py:SCRIPTS` and their NumPy/Matplotlib dependencies.
- The current standalone `paper/manuscript.tex` source, `paper/evidence_manifest.json`, `paper/figure_source_manifest.json`, all `paper/*evidence.json`, and current `paper/figures/*figure_data.json` catalogues.
- Every original archived result and text source referenced by those records/manifests, at the same relative path.
- The files in `paper/reproducibility/` and the small protocol/entry-point files in `pipeline_catalog.json`, which provide the local package inventory.
- For the `check` action, the existing 11 PNG/PDF pairs. The `build` action replaces these only inside its isolated output tree.

The input manifest distinguishes execution sources, evidence documents, archived evidence sources, source manifests, discovery catalogues, current exports, and pipeline files retained only for inspection. Current figure-data catalogues are used to discover participant-level source files, even when their corresponding figure-data JSON is regenerated during a build.

## Numeric interpretation

The generators retain the units, participant identities, confidence coverage, event masks, and cohort definitions stored in the original artifacts. Percentage-point displays multiply proportions by 100 where specified. Logarithmic or inverse-hyperbolic-sine axes change display coordinates, not source values. Nested Stieger cohorts, original-event versus common-history Lee evaluations, and model-based versus empirical EEG reliability references remain separately identified.

The entry point performs no fitting, bootstrap resampling, hypothesis testing, or new participant exclusion. It reads existing interval bounds and per-participant results. The checker establishes pointer/hash consistency; the protocols and experiment verification reports establish how those saved results were produced.

## Portable release records

The archive contains ordinary files only. Each `RELEASE_MANIFEST.json.files` entry has `path`, `bytes`, `sha256`, and `roles`. `SOURCE_INVENTORY.json` identifies the analysis/training/verification Python sources retained for inspection and separately names the small set executed by the figure-reproduction workflow. Static imports and historical path literals are an inventory, not a claim that a raw-data rerun has all dependencies available.

The builder's external verification report records the archive checksum, manuscript checksum, link check, temporary extraction location scope, actual build/check exit codes, runtime versions, and the original validator's pointer/hash counts. The report and manifest are stored next to the archive under `paper/releases/`; `latest_release.json` selects a matched version. All saved result JSON bytes are copied unchanged, preserving their original checksums and RFC 6901 pointers.
