#!/usr/bin/env python3
"""Create and test a portable archived-results package; never fit models."""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PAPER = ROOT / "paper"
SKIP_PARTS = {"development", "__pycache__", "builds", "releases", ".git", "node_modules"}
TEXT_SUFFIXES = {".py", ".json", ".md", ".txt", ".tex", ".html", ".yml", ".yaml", ".toml"}
KEY_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"\b(?:ghp_|github_pat_)[A-Za-z0-9_]{30,}\b"),
    re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{35,}\b"),
    re.compile(rb"\bAKIA[A-Z0-9]{16}\b"),
)
REVIEWER_FILES = (
    "recompute_lee_distribution.py", "lee_distribution_evidence.json",
    "old_test_trial_audit.py", "old_test_trial_inputs.json",
    "old_test_trial_evidence.json", "old_test_trial_tables.tex",
    "generate_lee_primary_figure.py", "lee_original_figure_template.tex",
    "lee_figure.tex", "lee_figure_isolated_validation.json",
    "integration_verification.json", "README.md", "LEE_FIGURE_INTEGRATION.md",
)
REVIEWER_SCRIPTS = (
    "paper/reviewer_revision/recompute_lee_distribution.py",
    "paper/reviewer_revision/old_test_trial_audit.py",
)


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def wrapper():
    spec = importlib.util.spec_from_file_location("archive_reproduction", HERE / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def safe_relative(name):
    p = Path(name)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("Not a package-relative path: " + str(name))
    return p


def source_inventory():
    base = wrapper().collect_manifest(require_existing_exports=True)
    if base["errors"]:
        raise ValueError("; ".join(base["errors"]))
    roles = defaultdict(set)
    for item in base["files"]:
        roles[item["path"]].update(item["roles"])

    def add(path, role):
        roles[str(path.relative_to(ROOT))].add(role)

    # Retain current paper evidence/documentation, but not editable-history
    # snapshots, obsolete validation reports, generated runs, or release files.
    for p in PAPER.iterdir():
        if p.is_file() and (p.suffix in {".md", ".txt"} or p.name.endswith("evidence.json")):
            add(p, "paper_documentation")
        elif p.is_file() and p.name.startswith("figure_blocks_") and p.suffix == ".tex":
            add(p, "original_inline_figure_coordinates")
    for p in HERE.iterdir():
        if p.is_file() and (p.suffix in {".py", ".md", ".txt"} or "statistic" in p.name.lower()
                            or p.name == "release_metadata.json"):
            add(p, "reproduction_delivery_source")
    # Package the current revision's runnable material explicitly, excluding
    # editorial snapshots. Compact trial values are JSON; original NPZ arrays
    # remain outside this archived-results route.
    revision_sources = {}
    for name in REVIEWER_FILES:
        p = PAPER / "reviewer_revision" / name
        if not p.is_file():
            raise FileNotFoundError(p)
        add(p, "reviewer_revision_reproduction_material")
        if p.suffix != ".json":
            continue
        records = json.loads(p.read_text()).get("records", [])
        if not isinstance(records, list):
            continue  # Validation summaries also use "records" for a count.
        for record in records:
            relative = str(safe_relative(record["source"]))
            source = ROOT / relative
            if source.suffix != ".json":
                raise ValueError("Expected compact JSON dependency: " + relative)
            if relative not in revision_sources:
                revision_sources[relative] = (sha(source), json.loads(source.read_text()))
            digest, value = revision_sources[relative]
            if digest != record["sha256"]:
                raise ValueError("Revision source hash mismatch: " + relative)
            for token in record["json_pointer"].split("/")[1:]:
                token = token.replace("~1", "/").replace("~0", "~")
                value = value[int(token)] if isinstance(value, list) else value[token]
            if value != record["value"]:
                raise ValueError("Revision source value mismatch: " + relative + record["json_pointer"])
            add(source, "reviewer_revision_archived_json_source")
    # Bibliography metadata and original verification reports are small and
    # useful for review. Do not copy experimental arrays or entire run trees.
    for dirname in ("reference_expansion", "reference_verification", "editorial_completion"):
        for p in (PAPER / dirname).rglob("*"):
            if p.is_file() and p.suffix in {".json", ".md"}:
                add(p, "bibliographic_verification_archive")
    for name in ("reference_audit.json", "REFERENCE_VERIFICATION.md"):
        if (PAPER / name).is_file():
            add(PAPER / name, "bibliographic_verification_archive")

    families = {Path(*Path(name).parts[:2]) for name in roles
                if name.startswith("experiments/")}
    for family in sorted(families):
        for p in (ROOT / family).rglob("*"):
            if not p.is_file() or SKIP_PARTS.intersection(p.parts):
                continue
            name = p.name.lower()
            if name.startswith(("license", "copying", "notice")):
                add(p, "original_license_or_notice")
            elif p.suffix == ".py":
                add(p, "available_experiment_source_inspection_only")
            elif p.suffix in {".md", ".txt", ".yml", ".yaml", ".toml"} and any(
                k in name for k in ("protocol", "readme", "requirements", "environment", "pyproject")
            ):
                add(p, "experiment_protocol_or_environment")
            elif p.suffix == ".json" and any(k in name for k in (
                "protocol", "freeze", "preflight", "execution_commands", "run_identity"
            )):
                add(p, "experiment_protocol_or_frozen_identity")
            elif p.suffix == ".json" and "verification" in p.parts:
                # Only already-computed compact verification reports, not
                # caches of numerical arrays or CPU refitting coefficients.
                if p.stat().st_size <= 2_000_000 and "cache" not in p.parts and not any(
                    k in name for k in ("refit", "reference_cache", "prediction", "bootstrap")
                ):
                    add(p, "archived_independent_verification_report")

    files, imports, absolute_paths = [], defaultdict(set), []
    for relative in sorted(roles):
        p = ROOT / safe_relative(relative)
        if not p.is_file():
            raise FileNotFoundError(p)
        figure_export = relative.startswith("paper/figures/") and p.suffix in {".png", ".pdf"}
        license_notice = "original_license_or_notice" in roles[relative]
        if p.suffix.lower() not in TEXT_SUFFIXES and not figure_export and not license_notice:
            raise ValueError("Excluded file type required by inventory: " + relative)
        if p.stat().st_size > 50_000_000:
            raise ValueError("Unexpected large file: " + relative)
        if p.suffix.lower() in TEXT_SUFFIXES or license_notice:
            data = p.read_bytes()
            if any(pattern.search(data) for pattern in KEY_PATTERNS):
                raise ValueError("Credential-pattern review required: " + relative)
            if p.suffix == ".py":
                text = data.decode("utf-8")
                try:
                    tree = ast.parse(text)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imports[alias.name.split(".")[0]].add(relative)
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            imports[node.module.split(".")[0]].add(relative)
                except SyntaxError:
                    # These are archived sources, not executed by this route.
                    imports["<syntax_not_parsed>"].add(relative)
                paths = sorted(set(re.findall(r"/(?:home|mnt|Users)/[^\s\"'<>]+", text)))
                if paths:
                    absolute_paths.append({"source": relative, "historical_path_literals": paths})
        files.append({"path": relative, "bytes": p.stat().st_size,
                      "sha256": sha(p), "roles": sorted(roles[relative])})
    return files, {
        "schema": "archived_source_inventory_v1",
        "scope": "Source and protocol inspection inventory; not an end-to-end execution claim.",
        "experiment_families": [str(p) for p in sorted(families)],
        "python_sources": [f for f in files if f["path"].endswith(".py")],
        "imports_observed_static_only": {k: sorted(v) for k, v in sorted(imports.items())},
        "historical_absolute_paths_in_python": absolute_paths,
        "missing_runtime_inputs": [
            "Third-party raw EEG distributions and acquisition permissions where applicable",
            "Pinned encoder/model weights, stage feature caches, saved predictions and fitted model arrays",
            "Original stage-specific training dependencies and translated execution paths",
        ],
        "executed_by_release_test": ["paper/reproducibility/run.py", *["paper/" + p for p in wrapper().SCRIPTS]]
            + (["paper/reproducibility/recompute_primary_statistics.py"]
               if (HERE / "recompute_primary_statistics.py").exists() else [])
            + list(REVIEWER_SCRIPTS),
    }


def write_tar(directory, target, top):
    # Explicit regular members prevent tarfile's inode-based hard-link
    # optimization from producing a link in the deliverable.
    with target.open("wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w") as archive:
            for p in sorted(directory.rglob("*")):
                if p.is_dir():
                    continue
                if p.is_symlink():
                    raise ValueError("Unexpected release symlink: " + str(p))
                info = tarfile.TarInfo(top + "/" + str(p.relative_to(directory)))
                info.size, info.mode, info.mtime = p.stat().st_size, 0o644, 0
                with p.open("rb") as f:
                    archive.addfile(info, f)


def extract_regular(archive_path, destination):
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                raise ValueError("Non-regular archive member: " + member.name)
            name = safe_relative(member.name)
            p = destination / name
            p.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as src, p.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def verify_files(directory, files):
    bad = []
    for item in files:
        p = directory / item["path"]
        if not p.is_file() or p.is_symlink() or p.stat().st_nlink != 1 or sha(p) != item["sha256"]:
            bad.append(item["path"])
    if bad:
        raise ValueError("Package bytes/link check failed: " + ", ".join(bad))


def compare_revision_values(actual, expected):
    """Compare all scientific fields; permit only numeric roundoff of 1e-12."""
    checked, maximum = 0, 0.0

    def compare(a, b, path):
        nonlocal checked, maximum
        if isinstance(b, dict):
            if not isinstance(a, dict) or set(a) != set(b):
                raise ValueError("Revision result keys differ: " + path)
            for key in b:
                compare(a[key], b[key], path + "/" + str(key))
        elif isinstance(b, list):
            if not isinstance(a, list) or len(a) != len(b):
                raise ValueError("Revision result list differs: " + path)
            for i, (av, bv) in enumerate(zip(a, b)):
                compare(av, bv, path + "/" + str(i))
        else:
            checked += 1
            if isinstance(b, float) and isinstance(a, (int, float)) and not isinstance(a, bool):
                error = abs(a - b)
                if not math.isfinite(error) or error > 1e-12:
                    raise ValueError("Revision numeric result differs: " + path)
                maximum = max(maximum, error)
            elif a != b:
                raise ValueError("Revision result differs: " + path)

    compare(actual, expected, "")
    return {"status": "pass", "scalar_checks": checked,
            "absolute_tolerance": 1e-12, "maximum_absolute_difference": maximum}


def test_reviewer_revisions(package, destination, env):
    """Run the added descriptive routes using only the copied package inputs."""
    revision = package / "paper/reviewer_revision"
    outputs = {
        "lee_distribution": destination / "lee_distribution_report.json",
        "old_test_compact": destination / "old_test_compact/old_test_trial_evidence.json",
    }
    commands = {
        "lee_distribution": [sys.executable, REVIEWER_SCRIPTS[0], "--source-root", ".",
                             "--self-test", "--out", str(outputs["lee_distribution"])],
        "old_test_compact": [sys.executable, REVIEWER_SCRIPTS[1],
                             "--out-dir", str(outputs["old_test_compact"].parent)],
    }
    reports = {}
    for name, command in commands.items():
        start = time.monotonic()
        result = subprocess.run(command, cwd=package, env=env, capture_output=True, text=True)
        (destination / (name + ".stdout.log")).write_text(result.stdout)
        (destination / (name + ".stderr.log")).write_text(result.stderr)
        if result.returncode:
            raise RuntimeError(name + " failed: " + result.stdout[-4000:] + result.stderr[-2000:])
        actual = json.loads(outputs[name].read_text())
        evidence_name = "lee_distribution_evidence.json" if name == "lee_distribution" else "old_test_trial_evidence.json"
        expected = json.loads((revision / evidence_name).read_text())
        if name == "lee_distribution":
            if actual["status"] != "PASS" or actual["self_test"]["status"] != "PASS":
                raise ValueError("Lee descriptive verification did not pass")
            comparison = compare_revision_values(actual, expected)
            detail = {"summary": actual["summary"], "source_json_files": len(actual["sources"]),
                      "source_records": len(actual["records"]), "numeric_checks": actual["verification"]["numeric_checks"]}
        else:
            if actual["status"] != "PASS_DESCRIPTIVE_PAIRED_PREDICTION_AUDIT":
                raise ValueError("Old-test compact verification did not pass")
            # The original report additionally verified NPZ sources. This
            # package run deliberately checks the compact values only, with
            # the input/script byte identities preserved and no array access.
            for key, filename in (("input_sha256", "old_test_trial_inputs.json"),
                                  ("script_sha256", "old_test_trial_audit.py")):
                if actual["reproduction"][key] != sha(revision / filename) or actual["reproduction"][key] != expected["reproduction"][key]:
                    raise ValueError("Old-test compact provenance differs: " + key)
            omit = {"source_verification", "reproduction"}
            comparison = compare_revision_values({k: v for k, v in actual.items() if k not in omit},
                                                 {k: v for k, v in expected.items() if k not in omit})
            generated_table = outputs[name].with_name("old_test_trial_tables.tex")
            if generated_table.read_bytes() != (revision / "old_test_trial_tables.tex").read_bytes():
                raise ValueError("Recomputed old-test tables differ from the archived tables")
            detail = {"totals": actual["totals"], "tables_byte_identical": True,
                      "source_verification": actual["source_verification"],
                      "excluded_from_comparison": ["source_verification mode", "runtime/time metadata"],
                      "input_and_script_hashes_match_original_evidence": True}
        reports[name] = {"executed": True, "command": command, "exit_code": result.returncode,
                         "wall_seconds": time.monotonic() - start,
                         "report": str(outputs[name].relative_to(destination)),
                         "report_sha256": sha(outputs[name]), "comparison_to_archived_evidence": comparison,
                         **detail}
    return {"status": "pass", "runs": reports,
            "scope": "All 42 original-event Lee participant summaries and all 62 Stieger shared-label25 compact paired-trial records; no model fitting, resampling, new significance tests, original NPZ reads, or raw EEG processing."}


def test_extracted(archive_path, destination, top, source_files):
    extract_regular(archive_path, destination)
    package = destination / top
    verify_files(package, source_files)
    # All package inputs are real files. This additional Python audit hook
    # denies access to the original research checkout and network connection.
    guard = destination / "guard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        "import os, sys\n"
        "forbidden = os.path.realpath(os.environ['REPRO_FORBIDDEN_ROOT'])\n"
        "def audit(event, args):\n"
        "    if event in ('socket.connect', 'socket.getaddrinfo'):\n"
        "        raise RuntimeError('Network is disabled during release verification')\n"
        "    if event == 'open' and args and isinstance(args[0], (str, bytes)):\n"
        "        path = os.path.realpath(os.fsdecode(args[0]))\n"
        "        if path == forbidden or path.startswith(forbidden + os.sep):\n"
        "            raise RuntimeError('Read of original research tree: ' + path)\n"
        "sys.addaudithook(audit)\n"
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(guard)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["REPRO_FORBIDDEN_ROOT"] = str(ROOT)
    env["MPLCONFIGDIR"] = str(destination / "matplotlib")
    probe = subprocess.run([
        sys.executable, "-c",
        "import os, sys, socket; assert 'sitecustomize' in sys.modules; "
        "exec(\"try:\\n open(os.environ['REPRO_FORBIDDEN_ROOT']+'/paper/manuscript.tex')\\n"
        "except RuntimeError:\\n pass\\nelse:\\n raise AssertionError('original-root guard inactive')\\n\"); "
        "exec(\"try:\\n socket.getaddrinfo('example.com',443)\\n"
        "except RuntimeError:\\n pass\\nelse:\\n raise AssertionError('network guard inactive')\\n\")"
    ], cwd=package, env=env, capture_output=True, text=True)
    if probe.returncode:
        raise RuntimeError("Release audit guard self-check failed: " + probe.stderr)
    commands, runs = [], {}
    for action in ("build", "check"):
        cmd = [sys.executable, "paper/reproducibility/run.py", "--action", action, "--staging", "copy"]
        start = time.monotonic()
        result = subprocess.run(cmd, cwd=package, env=env, capture_output=True, text=True)
        (destination / (action + ".stdout.log")).write_text(result.stdout)
        (destination / (action + ".stderr.log")).write_text(result.stderr)
        commands.append({"command": cmd, "action": action, "exit_code": result.returncode,
                         "wall_seconds": time.monotonic() - start})
        if result.returncode:
            raise RuntimeError(action + " failed in " + str(destination) + "\n" + result.stdout[-4000:] + result.stderr[-2000:])
        runs[action] = json.loads((package / "paper/reproducibility/last_run.json").read_text())
    statistical = {"executed": False, "scope": "No independent primary-statistics entry point was packaged."}
    statistics_script = package / "paper/reproducibility/recompute_primary_statistics.py"
    if statistics_script.is_file():
        statistics_output = destination / "primary_statistics_report.json"
        cmd = [sys.executable, "paper/reproducibility/recompute_primary_statistics.py",
               "--source-root", ".", "--self-test", "--out", str(statistics_output)]
        start = time.monotonic()
        result = subprocess.run(cmd, cwd=package, env=env, capture_output=True, text=True)
        (destination / "primary_statistics.stdout.log").write_text(result.stdout)
        (destination / "primary_statistics.stderr.log").write_text(result.stderr)
        if result.returncode:
            raise RuntimeError("Primary-statistics recomputation failed: " + result.stdout[-4000:] + result.stderr[-2000:])
        statistical = {"executed": True, "command": cmd, "exit_code": result.returncode,
                       "wall_seconds": time.monotonic() - start,
                       "report": json.loads(statistics_output.read_text())}
    reviewer_recomputation = test_reviewer_revisions(package, destination, env)
    all_files = [p for p in package.rglob("*") if p.is_file()]
    links = [str(p.relative_to(package)) for p in all_files if p.is_symlink() or p.stat().st_nlink != 1]
    if links:
        raise ValueError("Extracted/build tree contains links: " + ", ".join(links))
    return {
        "status": "pass", "commands": commands, "runs": runs,
        "temporary_extraction_outside_research_tree": not destination.is_relative_to(ROOT),
        "package_and_generated_build_link_count": len(links),
        "audit_guard_self_test": "pass: attempted original-root read and network resolution were rejected",
        "primary_statistical_recomputation": statistical,
        "reviewer_revision_recomputation": reviewer_recomputation,
        "source_read_guard": "Python audit hook rejected original research-root reads and socket connections in all verification commands.",
        "scope": "Archived-results figures, source/pointer/hash checks, primary-statistics recomputation, and added Lee distribution/Stieger compact paired-trial arithmetic; no raw EEG processing, model fitting, manuscript compilation, or external publication.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=PAPER / "releases")
    parser.add_argument("--inventory-only", action="store_true")
    args = parser.parse_args()
    files, source_info = source_inventory()
    if args.inventory_only:
        print(json.dumps({"files": len(files), "bytes": sum(f["bytes"] for f in files),
                          "python_files": len(source_info["python_sources"]),
                          "families": source_info["experiment_families"]}, indent=2))
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    metadata_file = HERE / "release_metadata.json"
    metadata = json.loads(metadata_file.read_text()) if metadata_file.exists() else {}
    if metadata:
        slug, version = metadata["archive_slug"], metadata["version"]
        if not re.fullmatch(r"[A-Za-z0-9._-]+", slug) or not re.fullmatch(r"[A-Za-z0-9._-]+", version):
            raise ValueError("Release slug/version must be filename-safe")
        top = slug + "-" + version
    else:
        top = "eeg-adaptation-archived-results-" + stamp
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if (out / (top + ".tar.gz")).exists():
        raise FileExistsError("Existing release is immutable; use another version or output directory")
    # tempfile is intentionally outside the research tree. Keep the work
    # directory on failure for diagnosis; successful runs retain small reports.
    work = Path(tempfile.mkdtemp(prefix="eeg-release-"))
    if work.is_relative_to(ROOT):
        raise ValueError("Temporary release test must be outside the research tree")
    stage = work / "stage"
    stage.mkdir()
    for item in files:
        src, dst = ROOT / item["path"], stage / item["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    write_json(stage / "SOURCE_INVENTORY.json", source_info)
    (stage / "README.md").write_text(
        "# EEG adaptation: archived-results reproduction package\n\n"
        "Start with [the reproduction instructions](paper/reproducibility/README.md).\n\n"
        "```sh\npython3 -m pip install -r paper/reproducibility/requirements.txt\n"
        "python3 paper/reproducibility/run.py --action build --staging copy\n"
        "python3 paper/reproducibility/run.py --action check --staging copy\n```\n\n"
        "The [current descriptive revision checks](paper/reviewer_revision/README.md) "
        "recompute Lee participant distributions and Stieger paired-trial tables:\n\n"
        "```sh\npython3 paper/reviewer_revision/recompute_lee_distribution.py --self-test --out lee_distribution_report.json\n"
        "python3 paper/reviewer_revision/old_test_trial_audit.py --out-dir old_test_check\n```\n\n"
        "RELEASE_MANIFEST.json binds all packaged source and input bytes. "
        "SOURCE_INVENTORY.json lists available experiment code, protocols, dependencies, and historical paths. "
        "This package rebuilds figures and validates saved results; it does not reproduce raw EEG preprocessing or model fitting. "
        "The configured versioned distribution location, when present, is recorded in the release manifest. "
        "The builder itself does not upload files or verify public availability.\n"
    )
    manifest_files = []
    for p in sorted(stage.rglob("*")):
        if p.is_file():
            relative = str(p.relative_to(stage))
            role = next((f["roles"] for f in files if f["path"] == relative), ["release_generated_documentation"])
            manifest_files.append({"path": relative, "bytes": p.stat().st_size, "sha256": sha(p), "roles": role})
    manifest = {
        "schema": "portable_archived_result_release_v1", "created_utc": now(),
        "manuscript_sha256": sha(stage / "paper/manuscript.tex"),
        "scope": "Archived results, all figure/evidence dependencies, protocols and available analysis/training source for inspection.",
        "exclusions": ["Raw EEG", "Feature caches", "Encoder weights", "Bulk fitted-model/prediction-array files; the specified compact paired-trial JSON is included", "Credentials", "Manuscript PDF"],
        "public_release_status": "Prepared at packaging; the builder does not upload. Public upload/download verification is recorded separately.",
        "release_metadata": metadata,
        "files": manifest_files,
        "total_uncompressed_bytes": sum(f["bytes"] for f in manifest_files),
        "manifest_self_hash": "Excluded to avoid a circular hash; the archive SHA-256 covers this manifest.",
    }
    write_json(stage / "RELEASE_MANIFEST.json", manifest)
    candidate = work / (top + ".tar.gz")
    write_tar(stage, candidate, top)
    report = test_extracted(candidate, work / "extracted", top, manifest_files)
    # Reject a race with edits in another task before sealing this snapshot.
    changed = [f["path"] for f in files if sha(ROOT / f["path"]) != f["sha256"]]
    if changed:
        raise RuntimeError("Canonical inputs changed during build: " + ", ".join(changed))
    current_files, _ = source_inventory()
    if {f["path"] for f in current_files} != {f["path"] for f in files}:
        raise RuntimeError("Release dependency inventory changed during build; rerun after source finalization")
    target = out / candidate.name
    shutil.copyfile(candidate, target)
    report.update({
        "schema": "portable_release_verification_v1", "completed_utc": now(),
        "archive": target.name, "archive_sha256": sha(target), "archive_bytes": target.stat().st_size,
        "manuscript_sha256": manifest["manuscript_sha256"], "packaged_files": len(manifest_files) + 1,
        "source_files": len(files), "source_bytes": manifest["total_uncompressed_bytes"],
        "unchanged_canonical_inputs": True, "public_upload_performed": False,
    })
    log_directory = out / (top + ".verification_logs")
    log_directory.mkdir()
    log_records = []
    verification_outputs = sorted((work / "extracted").glob("*.log"))
    if (work / "extracted/primary_statistics_report.json").exists():
        verification_outputs.append(work / "extracted/primary_statistics_report.json")
    for name in ("lee_distribution_report.json", "old_test_compact/old_test_trial_evidence.json",
                 "old_test_compact/old_test_trial_tables.tex"):
        verification_outputs.append(work / "extracted" / name)
    for p in verification_outputs:
        dst = log_directory / p.name
        shutil.copyfile(p, dst)
        log_records.append({"path": str(dst.relative_to(out)), "bytes": dst.stat().st_size, "sha256": sha(dst)})
    report["verification_logs"] = log_records
    write_json(out / (top + ".verification.json"), report)
    write_json(out / (top + ".manifest.json"), manifest)
    (out / (top + ".sha256")).write_text(report["archive_sha256"] + "  " + target.name + "\n")
    write_json(out / "latest_release.json", {k: report[k] for k in (
        "status", "completed_utc", "archive", "archive_sha256", "archive_bytes", "manuscript_sha256", "packaged_files"
    )} | {"verification_report": top + ".verification.json", "manifest": top + ".manifest.json"})
    print(json.dumps({k: report[k] for k in ("status", "archive", "archive_bytes", "archive_sha256", "source_files", "manuscript_sha256")}, indent=2))
    print("Verification report:", out / (top + ".verification.json"))
    shutil.rmtree(work)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
