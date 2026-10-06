#!/usr/bin/env python3
"""Rebuild archived-result figures by invoking the existing paper scripts."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PAPER = ROOT / "paper"
SCRIPTS = (
    "make_figures.py", "validate_figures.py", "figure_assets_eeg.py",
    "figure_assets_retention.py", "figure_assets_dynamics.py",
    "figure_assets_source.py",
)
FIGURES = (
    "update_layers", "eeg_budget_calibration", "eeg_pairing_forest",
    "eeg_lee_endpoints", "feedback_source", "retention_heterogeneity",
    "retention_tradeoffs", "dynamics_history_schedules",
    "dynamics_parameter_information", "dynamics_prior_stability",
    "dynamics_reliability_reference",
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def collect_manifest(require_existing_exports=False):
    """Discover local dependencies from existing evidence, without duplicating checks."""
    roles = defaultdict(set)
    declared_hashes = defaultdict(set)

    def add(relative, role, expected=None):
        relative = str(relative)
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Expected a repository-relative input path: {relative}")
        roles[relative].add(role)
        if expected:
            declared_hashes[relative].add(expected)

    def discover(obj):
        if isinstance(obj, dict):
            if all(key in obj for key in ("source", "json_pointer", "value")):
                add(obj["source"], "archived_evidence_source", obj.get("sha256"))
                # A recorded value can itself contain a descriptive 'source'
                # field; the entire value is data, not another file reference.
                return
            if isinstance(obj.get("source"), str) and any(
                key in obj for key in ("sha256", "lines", "line_start")
            ):
                add(obj["source"], "archived_evidence_source", obj.get("sha256"))
            # EEG evidence also has a path-keyed source-hash catalogue.
            for catalogue_key in ("sources", "source_catalog"):
                if isinstance(obj.get(catalogue_key), dict):
                    for name, spec in obj[catalogue_key].items():
                        if isinstance(spec, dict) and "sha256" in spec:
                            add(name, "archived_evidence_source", spec["sha256"])
            for value in obj.values():
                discover(value)
        elif isinstance(obj, list):
            for value in obj:
                discover(value)

    for name in SCRIPTS:
        add("paper/" + name, "existing_execution_source")
    add("paper/manuscript.tex", "manuscript_for_source_checks_only")
    evidence_files = sorted(PAPER.glob("*evidence.json"))
    discovery_files = (evidence_files + sorted((PAPER / "figures").glob("*figure_data.json"))
                       + sorted(HERE.glob("*statistic*.json")))
    for path in discovery_files:
        add(path.relative_to(ROOT), "evidence_document" if path in evidence_files else "discovery_catalogue")
        discover(json.loads(path.read_text()))
    for name in ("evidence_manifest.json", "figure_source_manifest.json"):
        path = PAPER / name
        add(path.relative_to(ROOT), "source_manifest" if name == "evidence_manifest.json" else "discovery_catalogue")
        for item in json.loads(path.read_text())["files"]:
            add(item["path"], "archived_evidence_source", item["sha256"])
    catalogue_path = HERE / "pipeline_catalog.json"
    catalogue = json.loads(catalogue_path.read_text())
    for family in catalogue["pipelines"]:
        for name in family["protocols"] + family["entry_points"]:
            add(name, "end_to_end_pipeline_catalogue_only")
    delivery_names = {"run.py", "README.md", "INPUT_FORMAT.md", "requirements.txt", "pipeline_catalog.json"}
    delivery_names.update(p.name for p in HERE.glob("*.py"))
    delivery_names.update(p.name for p in HERE.glob("*.md"))
    delivery_names.update(p.name for p in HERE.glob("*statistic*.json"))
    for name in sorted(delivery_names):
        add((HERE / name).relative_to(ROOT), "reproduction_delivery_source")
    for stem in FIGURES:
        for extension in ("png", "pdf"):
            relative = f"paper/figures/{stem}.{extension}"
            if require_existing_exports or (ROOT / relative).is_file():
                add(relative, "current_export_for_check_action")

    files, errors = [], []
    supplementary_counts, parsed_sources = {}, {}

    def direct_records(obj):
        if isinstance(obj, dict):
            if all(k in obj for k in ("source", "json_pointer", "value")):
                yield obj
            else:
                for value in obj.values():
                    yield from direct_records(value)
        elif isinstance(obj, list):
            for value in obj:
                yield from direct_records(value)

    for path in sorted(HERE.glob("*statistic*.json")):
        count = 0
        for record in direct_records(json.loads(path.read_text())):
            relative = record["source"]
            if relative not in parsed_sources:
                parsed_sources[relative] = json.loads((ROOT / relative).read_text())
            value = parsed_sources[relative]
            for token in record["json_pointer"].split("/")[1:]:
                token = token.replace("~1", "/").replace("~0", "~")
                value = value[int(token)] if isinstance(value, list) else value[token]
            if value != record["value"]:
                errors.append("Statistical evidence pointer mismatch: " + relative + record["json_pointer"])
            count += 1
        supplementary_counts[str(path.relative_to(ROOT))] = count
    for relative in sorted(roles):
        path = ROOT / relative
        if not path.is_file():
            errors.append("Missing input: " + relative)
            continue
        digest = sha(path)
        for expected in declared_hashes[relative]:
            if digest != expected:
                errors.append("Declared source hash mismatch: " + relative)
        file_roles = sorted(roles[relative])
        if "existing_execution_source" in file_roles:
            staging = "hard_link_existing_source"
        elif any(r in file_roles for r in (
            "archived_evidence_source", "evidence_document", "source_manifest",
            "manuscript_for_source_checks_only",
        )):
            staging = "symbolic_link_read_only_input"
        elif "current_export_for_check_action" in file_roles or relative.startswith("paper/figures/"):
            staging = "symbolic_link_in_check_action_only"
        else:
            staging = "catalogued_only"
        files.append({
            "path": relative, "bytes": path.stat().st_size, "sha256": digest,
            "roles": file_roles, "staging": staging,
        })
    return {
        "schema": "local_archived_result_reproduction_v1",
        "created_utc": utc_now(),
        "scope": "Rebuild scientific figures and validate archived evidence; no model fitting or manuscript compilation.",
        "release_status": "Archived-result reproduction inventory; versioned distribution metadata and upload verification are recorded separately.",
        "expected_scientific_export_stems": list(FIGURES),
        "additional_manuscript_figure": "The information-timing schematic is inline in manuscript.tex; it is checked as source and not rendered separately.",
        "discovery_documents": [str(p.relative_to(ROOT)) for p in discovery_files],
        "supplementary_statistical_pointer_checks": supplementary_counts,
        "files": files,
        "total_catalogued_bytes": sum(f["bytes"] for f in files),
        "errors": errors,
    }


def stage_inputs(build, manifest, action, staging="links"):
    for item in manifest["files"]:
        method = item["staging"]
        if method == "catalogued_only":
            continue
        if method == "symbolic_link_in_check_action_only" and action != "check":
            continue
        src, dst = ROOT / item["path"], build / item["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        if staging == "copy":
            shutil.copyfile(src, dst)
        elif method == "hard_link_existing_source":
            # A symlink would resolve __file__ back to the canonical output tree.
            # Hard links execute the same source bytes with an isolated __file__.
            os.link(src, dst)
        else:
            dst.symlink_to(src)


def execute(build, script, environment):
    command = [sys.executable, str(build / "paper" / script)]
    started = time.monotonic()
    result = subprocess.run(command, cwd=build, env=environment, capture_output=True, text=True)
    stem = Path(script).stem
    (build / f"{stem}.stdout.log").write_text(result.stdout)
    (build / f"{stem}.stderr.log").write_text(result.stderr)
    return {
        "command": command, "exit_code": result.returncode,
        "wall_seconds": time.monotonic() - started,
        "stdout_log": f"{stem}.stdout.log", "stderr_log": f"{stem}.stderr.log",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("manifest", "check", "build"), default="build")
    parser.add_argument("--staging", choices=("links", "copy"), default="links",
                        help="Use copy for portable, link-free isolated builds.")
    args = parser.parse_args()
    manifest = collect_manifest(require_existing_exports=args.action == "check")
    write_json(HERE / "input_manifest.json", manifest)
    if manifest["errors"]:
        print(json.dumps({"status": "fail", "errors": manifest["errors"]}, indent=2))
        return 1
    if args.action == "manifest":
        print(json.dumps({"status": "pass", "manifest": str(HERE / "input_manifest.json"), "files": len(manifest["files"])}))
        return 0

    run_name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    build = HERE / "builds" / run_name
    build.mkdir(parents=True)
    write_json(build / "input_manifest.json", manifest)
    stage_inputs(build, manifest, args.action, args.staging)
    environment = os.environ.copy()
    environment["MPLCONFIGDIR"] = str(build / ".matplotlib")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    commands = []
    if args.action == "build":
        commands.append(execute(build, "make_figures.py", environment))
    if not commands or commands[-1]["exit_code"] == 0:
        commands.append(execute(build, "validate_figures.py", environment))

    changed = [item["path"] for item in manifest["files"] if sha(ROOT / item["path"]) != item["sha256"]]
    validation_path = build / "paper" / "figure_validation.json"
    validation = json.loads(validation_path.read_text()) if validation_path.is_file() else None
    missing_exports = [stem for stem in FIGURES if any(
        not (build / "paper" / "figures" / f"{stem}.{ext}").is_file()
        for ext in ("png", "pdf")
    )]
    outputs = []
    for path in sorted((build / "paper").rglob("*")):
        if path.is_file() and not path.is_symlink() and path.suffix != ".py":
            outputs.append({"path": str(path.relative_to(build)), "bytes": path.stat().st_size, "sha256": sha(path)})
    result = {
        "schema": "local_reproduction_run_v1", "action": args.action,
        "staging": args.staging,
        "status": "pass" if (all(c["exit_code"] == 0 for c in commands)
                                 and not changed and not missing_exports
                                 and validation and validation["status"] == "pass") else "fail",
        "completed_utc": utc_now(), "build_directory": str(build.relative_to(ROOT)),
        "runtime": {"python": sys.version, "executable": sys.executable,
                    "platform": platform.platform(),
                    "packages": {k: importlib.metadata.version(k) for k in ("numpy", "matplotlib")}},
        "commands": commands, "catalogued_input_files": len(manifest["files"]),
        "canonical_inputs_changed": changed, "missing_export_stems": missing_exports,
        "validation": validation, "outputs": outputs,
        "scope": "Archived-result figure rendering, exact JSON pointer/hash checks, and manuscript source checks. No raw EEG processing, fitting, new resampling, manuscript PDF, or external publication.",
    }
    write_json(build / "run_report.json", result)
    write_json(HERE / "last_run.json", result)
    print(json.dumps({k: result[k] for k in ("status", "action", "build_directory", "catalogued_input_files", "canonical_inputs_changed", "missing_export_stems")}, indent=2))
    print("Detailed report:", build / "run_report.json")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
