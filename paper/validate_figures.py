"""Validate saved manuscript figure provenance without fitting any model."""
from pathlib import Path
import hashlib
import json
import re
from functools import lru_cache

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(obj):
    if isinstance(obj, dict):
        if all(k in obj for k in ("source", "json_pointer", "value")):
            yield obj
        else:
            for value in obj.values():
                yield from records(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from records(value)


@lru_cache(maxsize=None)
def source_document(relative):
    return json.loads((ROOT / relative).read_text())


def resolve(relative, pointer):
    value = source_document(relative)
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def main():
    manifest = json.loads((PAPER / "evidence_manifest.json").read_text())
    errors = []
    for item in manifest["files"]:
        if sha(ROOT / item["path"]) != item["sha256"]:
            errors.append("Changed original source: " + item["path"])

    original_counts = {}
    for name in ("eeg_evidence.json", "dynamics_evidence.json", "additional_evidence.json"):
        document = json.loads((PAPER / name).read_text())
        # Derived-statistic pointers identify input containers, not their
        # computed scalar. Validate the explicitly direct evidence collection.
        original = list(records(document.get("evidence", document)))
        for item in original:
            if resolve(item["source"], item["json_pointer"]) != item["value"]:
                errors.append(name + ": mismatched " + item["json_pointer"])
        original_counts[name] = len(original)

    editorial_counts, editorial_sources = {}, {}
    editorial_path = PAPER / "editorial_evidence.json"
    if editorial_path.exists():
        editorial = json.loads(editorial_path.read_text())
        direct = list(records(editorial))
        for item in direct:
            if resolve(item["source"], item["json_pointer"]) != item["value"]:
                errors.append("editorial_evidence.json: mismatched " + item["json_pointer"])
            path = ROOT / item["source"]
            digest = sha(path)
            if digest != item["sha256"]:
                errors.append("Changed editorial source: " + item["source"])
            editorial_sources[item["source"]] = {
                "path": item["source"], "bytes": path.stat().st_size, "sha256": digest
            }
        for item in editorial.get("text_sources", []):
            path = ROOT / item["source"]
            digest = sha(path)
            if digest != item["sha256"]:
                errors.append("Changed editorial text source: " + item["source"])
            if not 1 <= item["line_start"] <= item["line_end"] <= len(path.read_text().splitlines()):
                errors.append("Invalid editorial text location: " + item["source"])
            editorial_sources[item["source"]] = {
                "path": item["source"], "bytes": path.stat().st_size, "sha256": digest
            }
        editorial_counts = {"records": len(direct),
                            "text_locations": len(editorial.get("text_sources", [])),
                            "unique_sources": len(editorial_sources)}
        (PAPER / "editorial_source_manifest.json").write_text(json.dumps({
            "purpose": "Original sources for editorial diagnostic and threshold additions",
            "files": [editorial_sources[k] for k in sorted(editorial_sources)]
        }, indent=2) + "\n")

    files = sorted((PAPER / "figures").glob("*figure_data.json"))
    counts, sources = {}, {}
    for path in files:
        count = 0
        for item in records(json.loads(path.read_text())):
            actual = resolve(item["source"], item["json_pointer"])
            if actual != item["value"]:
                errors.append(str(path.name) + ": mismatched " + item["json_pointer"])
            source = ROOT / item["source"]
            digest = sha(source)
            if "sha256" in item and item["sha256"] != digest:
                errors.append("Figure source hash mismatch: " + item["source"])
            sources[item["source"]] = {
                "path": item["source"], "bytes": source.stat().st_size, "sha256": digest
            }
            count += 1
        counts[str(path.relative_to(ROOT))] = count

    manuscript = (PAPER / "manuscript.tex").read_text()
    labels = re.findall(r"\\label\{([^}]+)\}", manuscript)
    references = re.findall(r"\\(?:ref|eqref|autoref)\{([^}]+)\}", manuscript)
    citations = {k.strip() for s in re.findall(r"\\cite\{([^}]+)\}", manuscript) for k in s.split(",")}
    bibliography = set(re.findall(r"\\bibitem\{([^}]+)\}", manuscript))
    if len(labels) != len(set(labels)):
        errors.append("Duplicate manuscript labels")
    errors += ["Unresolved label: " + r for r in references if r not in labels]
    errors += ["Unresolved citation: " + k for k in citations - bibliography]
    if re.search(r"\\(?:input|include|includegraphics|bibliography)\b", manuscript):
        errors.append("External file dependency in standalone LaTeX")
    exported = []
    for path in sorted((PAPER / "figures").glob("*.png")):
        pdf = path.with_suffix(".pdf")
        if not pdf.is_file() or pdf.stat().st_size == 0:
            errors.append("Missing vector export: " + str(pdf))
        exported.append(str(path.relative_to(ROOT)))

    result = {
        "status": "pass" if not errors else "fail",
        "manuscript_sha256": sha(PAPER / "manuscript.tex"),
        "original_source_files_checked": len(manifest["files"]),
        "original_evidence_pointer_checks": original_counts,
        "editorial_evidence_checks": editorial_counts,
        "figure_pointer_checks": counts,
        "unique_figure_sources": len(sources),
        "figure_count": manuscript.count(r"\begin{figure}"),
        "table_count": manuscript.count(r"\begin{table}"),
        "bibliography_count": len(bibliography),
        "vector_and_raster_exports": exported,
        "errors": errors,
        "verification_scope": "Exact original JSON values, source hashes, exported-file presence, citations, labels, and standalone-source dependencies. Compilation and rendered-image inspection are recorded separately.",
    }
    (PAPER / "figure_source_manifest.json").write_text(json.dumps({
        "purpose": "Formal source files for the expanded manuscript figures; experimental artifacts unchanged",
        "files": [sources[k] for k in sorted(sources)]
    }, indent=2) + "\n")
    (PAPER / "figure_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
