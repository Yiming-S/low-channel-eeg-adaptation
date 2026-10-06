#!/usr/bin/env python3
"""Recompute primary paper statistics from portable, source-bound endpoints.

Only NumPy and the Python standard library are required. No experiment modules,
EEG recordings, feature arrays, estimators, or production analysis functions are
imported. The optional extraction mode is for maintaining the compact input;
ordinary reproduction reads only that input JSON.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys

import numpy as np


REPETITIONS = 10000
ATOL = 1e-10


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pointer(document, path):
    """Resolve an RFC 6901 pointer without consulting experiment code."""
    value = document
    for token in path.split("/")[1:] if path else []:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def write(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def extract(root):
    """Copy exact archived endpoint records, identities, and reference results."""
    root = Path(root).resolve()
    records, documents, hashes, lookup = [], {}, {}, {}

    def ref(source, path, units="stored endpoint or metadata"):
        key = (source, path)
        if key not in lookup:
            if source not in documents:
                documents[source] = read(root / source)
                hashes[source] = digest(root / source)
            index = len(records)
            records.append(dict(source=source, json_pointer=path,
                                value=pointer(documents[source], path), units=units,
                                sha256=hashes[source]))
            lookup[key] = index
        return lookup[key]

    lee_root = "experiments/lee2019_erp_history_v1"
    lee_summary = lee_root + "/results/pilot_summary_groups.json"
    lee_protocol = lee_root + "/protocol.json"
    lee_group = "/groups/confirmation"
    subjects_ref = ref(lee_summary, lee_group + "/subjects", "participant identifiers")
    subjects = records[subjects_ref]["value"]
    lee = dict(subjects=subjects_ref, seed=ref(lee_protocol, "/inference/seed", "RNG seed"),
               inference_rule=ref(lee_protocol, "/inference/bootstrap", "original rule"),
               shuffle_seeds=ref(lee_protocol, "/mapping/shuffle_seeds", "assignment RNG seeds"),
               endpoints=[dict(subject=s, record=ref(
                   f"{lee_root}/results/sub-{s:02d}/summary.json", "/evaluation/future",
                   "participant original-event future AUC, BA, MSE, and skill")) for s in subjects],
               expected_means=ref(lee_summary, lee_group + "/means/future"), contrasts={})
    for name in ["low_labels_updated-low_frozen:auc", "mapped_true_pairs-mapped_frozen:auc",
                 "mapped_true_pairs-shuffle_average:auc", "true_pairs-frozen:mse",
                 "true_pairs-shuffle_average:mse"]:
        lee["contrasts"][name] = ref(lee_summary, lee_group + "/contrasts/future:" + name)

    budget_root = "experiments/reliability_budget_v1/results/eeg"
    budget_analysis = budget_root + "/analysis.json"
    budget_doc = read(root / budget_analysis)
    co = budget_doc["cohorts"]["stieger62"]
    base = "/cohorts/stieger62"
    primary = co["primary_key"]
    budget = dict(cohort="stieger62", cohort_index=0,
                  subjects=ref(budget_analysis, base + "/fixed_groups/all", "participant identifiers"),
                  seed=ref(budget_analysis, "/bootstrap_seed", "RNG seed"),
                  repetitions=ref(budget_analysis, "/bootstrap_repetitions", "resamples"),
                  seed_rule=ref(budget_analysis, "/bootstrap_seed_definition", "original rule"),
                  draw_rule=ref(budget_analysis, "/bootstrap_draw_definition", "original rule"),
                  primary_key=ref(budget_analysis, "/primary_key"),
                  policies={}, contrasts={})
    folder = budget_root + "/stieger62"
    future_source = folder + "/future_metrics.json"
    initial_source = folder + "/initial_old.json"
    old_source = folder + "/old_metrics.json"
    future, initial, old = [read(root / s) for s in [future_source, initial_source, old_source]]
    last = max(r["session"] for r in old)
    budget["final_session"] = last
    budget["expected_sessions"] = list(range(2, last + 1))
    for label in ["label0", "label25", "label100"]:
        policy = label + "__none"
        case_path = base + "/grid/" + primary + "/cases/" + policy
        case = dict(future=[ref(future_source, "/" + str(i), "one participant/session endpoint record")
                            for i, r in enumerate(future) if r["policy"] == policy],
                    participant_future=ref(budget_analysis, case_path + "/per_person"),
                    expected_future=ref(budget_analysis, case_path + "/groups/all/future/future_balanced_accuracy"),
                    label_budget=ref(budget_analysis, base + "/information_budgets/" + policy + "/additional_labels", "new labels"))
        if label == "label25":
            case["initial_old"] = [ref(initial_source, "/" + str(i), "initial permanent-old endpoint record")
                                   for i, r in enumerate(initial) if r["policy"] == policy]
            case["final_old"] = [ref(old_source, "/" + str(i), "final permanent-old endpoint record")
                                 for i, r in enumerate(old) if r["policy"] == policy and r["session"] == last]
            case["expected_old"] = ref(budget_analysis, base + "/final_old_test/" + policy + "/all/balanced_accuracy")
        budget["policies"][policy] = case
    for left, right in [("label25__none", "label0__none"), ("label100__none", "label25__none")]:
        name = left + "_minus_" + right
        budget["contrasts"][name] = ref(budget_analysis, base + "/paired_primary_contrasts/" + name + "/all/future_balanced_accuracy")

    constraints = []
    for stage, target, stage_name in [("feedback_retention_v3", "own_functional", "v3_line"),
                                      ("confirmation_prior_constraints_v4", "own_constrained", "v4_full_space")]:
        source = f"experiments/{stage}/results/eeg/analysis.json"
        analysis = read(root / source)
        for ci, cohort in enumerate(["stieger62", "stieger41"]):
            base = "/cohorts/" + cohort
            subject_ref = ref(source, base + "/fixed_groups/all", "participant identifiers")
            item = dict(stage=stage_name, cohort=cohort, cohort_index=ci, target=target,
                        subjects=subject_ref, seed=ref(source, "/bootstrap_seed", "RNG seed"),
                        repetitions=ref(source, "/bootstrap_repetitions", "resamples"),
                        seed_rule=ref(source, "/bootstrap_rule", "original rule"), policies={},
                        expected_contrast=ref(source, base + "/paired_contrasts/" + target + "_minus_own/all"))
            for policy in ["own", target]:
                item["policies"][policy] = dict(
                    participants=[dict(subject=s, record=ref(source, base + f"/cases/{policy}/per_person/{s}",
                                                            "participant future mean and initial/final old endpoints"))
                                  for s in records[subject_ref]["value"]],
                    expected_metrics=ref(source, base + f"/cases/{policy}/groups/all/metrics"),
                    expected_counts=ref(source, base + f"/cases/{policy}/groups/all/counts"))
            dual = "/functional_dual_target" if stage_name == "v3_line" else "/dual_targets/own_constrained"
            item["expected_dual"] = ref(source, base + dual)
            constraints.append(item)

    return dict(schema="primary_statistical_inputs_v1", extracted_utc=datetime.now(timezone.utc).isoformat(),
                scope="Archived original-event Lee42; Stieger62 label budget; v3 line and v4 full-space constraints in 62 and nested41. Endpoints only, no raw signals or predictions.",
                units="AUC and BA are stored on 0..1; MSE uses original standardized ERP coordinates. Multiply BA/proportion differences by100 for percentage points.",
                provenance="Every records entry is an exact JSON value copied from the named original source and RFC6901 pointer; source hashes are SHA256 of complete original files.",
                boundaries=["All intervals condition on fitted models and archived endpoints; no model refitting.",
                            "Stieger is development evidence and41 is nested, not independent.",
                            "Five Lee shuffles are averaged within participant, not treated as extra participants.",
                            "Future benefit and permanent-old change use different reference models.",
                            "No new comparison families, p-values, optimization, eligibility selection, or raw-data validation."],
                records=records, lee=lee, budget=budget, constraints=constraints)


class Audit:
    def __init__(self):
        self.checks = 0
        self.maximum_absolute_error = 0.0
        self.errors = []

    def close(self, name, actual, expected):
        self.checks += 1
        a, b = np.asarray(actual, float), np.asarray(expected, float)
        if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
            self.errors.append(name + ": shape/nonfinite mismatch")
            return
        error = float(np.max(np.abs(a - b))) if a.size else 0.0
        self.maximum_absolute_error = max(self.maximum_absolute_error, error)
        if error > ATOL:
            self.errors.append(f"{name}: maximum absolute difference {error:.12g}")

    def exact(self, name, actual, expected):
        self.checks += 1
        if actual != expected:
            self.errors.append(f"{name}: identity/value mismatch")


def percentile(values, probabilities=(.025, .975)):
    """Explicit linear interpolation at (N-1)*q, independently of np.quantile."""
    ordered = np.sort(np.asarray(values, float))
    output = []
    for q in probabilities:
        pos = (len(ordered) - 1) * q
        lo, hi = int(np.floor(pos)), int(np.ceil(pos))
        output.append(float(ordered[lo] + (pos - lo) * (ordered[hi] - ordered[lo])))
    return output


def indices(seed, subjects, cohort_index=None):
    entropy = int(seed) if cohort_index is None else np.random.SeedSequence(
        [int(seed), int(cohort_index), len(subjects), *map(int, subjects)])
    return np.random.default_rng(entropy).integers(0, len(subjects), size=(REPETITIONS, len(subjects)))


def estimate(values, draws):
    values = np.asarray(values, float)
    # Direct participant indexing instead of the production count-matrix shortcut.
    distribution = values[draws].sum(axis=1) / len(values)
    return dict(n=len(values), mean=float(values.mean()), interval95=percentile(distribution))


def compare_estimate(audit, name, result, expected):
    audit.close(name + "/mean", result["mean"], expected.get("mean", expected.get("difference")))
    key = next((k for k in ["conditional95", "conditional_interval", "ci95"] if k in expected), None)
    if key:
        audit.close(name + "/interval", result["interval95"], expected[key])
    if "n" in expected:
        audit.exact(name + "/n", result["n"], expected["n"])


def self_test():
    a = Audit()
    a.close("linear percentile interpolation", percentile([0, 10, 20, 30]), [.75, 29.25])
    a.close("constant endpoints", estimate([.25, .25], np.array([[0, 1], [1, 1]]))["interval95"], [.25, .25])
    a.close("pair before resampling", np.array([.7, .2]) - np.array([.6, .3]), [.1, -.1])
    a.exact("strict zero harm upper bound fails", 0.0 < 0, False)
    a.exact("future tolerance includes boundary", -.005 >= -.005, True)
    if a.errors:
        raise ValueError(a.errors)
    return dict(status="PASS", checks=a.checks)


def recompute(document, source_root=None):
    records = document["records"]
    value = lambda i: records[i]["value"]
    audit = Audit()
    sources = {}
    for record in records:
        previous = sources.setdefault(record["source"], record["sha256"])
        audit.exact("consistent source hash", previous, record["sha256"])
    source_audit = dict(mode="embedded records only", files=len(sources), records=len(records))
    if source_root is not None:
        source_root = Path(source_root)
        loaded = {}
        for path, expected_sha in sources.items():
            audit.exact(path + "/sha256", digest(source_root / path), expected_sha)
            loaded[path] = read(source_root / path)
        for r in records:
            audit.exact(r["source"] + r["json_pointer"], pointer(loaded[r["source"]], r["json_pointer"]), r["value"])
        source_audit["mode"] = "full source hashes and every original JSON pointer checked"

    lee = document["lee"]
    subjects = value(lee["subjects"])
    audit.exact("Lee identity", [r["subject"] for r in lee["endpoints"]], subjects)
    draws = indices(value(lee["seed"]), subjects)
    rows = [value(r["record"]) for r in lee["endpoints"]]
    shuffle_seeds = value(lee["shuffle_seeds"])
    vectors = {}
    means = {}
    for family, metric in [("classification", "auc"), ("structure", "mse")]:
        for policy in rows[0][family]:
            vector = np.array([r[family][policy][metric] for r in rows])
            vectors[family, policy] = vector
            means[policy] = float(vector.mean())
            audit.close("Lee/mean/" + policy, vector.mean(), value(lee["expected_means"])[family][policy][metric])
    vectors["classification", "shuffle_average"] = np.array([
        vectors["classification", f"mapped_shuffle_{s}"] for s in shuffle_seeds]).mean(axis=0)
    vectors["structure", "shuffle_average"] = np.array([
        vectors["structure", f"shuffle_{s}"] for s in shuffle_seeds]).mean(axis=0)
    lee_results = {}
    for name, expected_ref in lee["contrasts"].items():
        operands, metric = name.split(":")
        left, right = operands.split("-")
        family = "classification" if metric == "auc" else "structure"
        delta = vectors[family, left] - vectors[family, right]
        result = estimate(delta, draws)
        expected = value(expected_ref)
        compare_estimate(audit, "Lee/" + name, result, expected)
        audit.close("Lee/" + name + "/individual", delta, expected["individual"])
        lee_results[name] = result

    budget = document["budget"]
    people = value(budget["subjects"])
    audit.exact("Budget sorted participants", people, sorted(people))
    audit.exact("Budget repetitions", value(budget["repetitions"]), REPETITIONS)
    draws = indices(value(budget["seed"]), people, budget["cohort_index"])
    future, budget_results = {}, {}
    for policy, case in budget["policies"].items():
        rows = [value(i) for i in case["future"]]
        audit.exact("Budget policy identity", sorted({r["policy"] for r in rows}), [policy])
        audit.exact("Budget participant identity", sorted({r["subject"] for r in rows}), people)
        vector = []
        for person in people:
            selected = sorted([r for r in rows if r["subject"] == person], key=lambda r: r["session"])
            audit.exact(f"Budget/{policy}/{person}/sessions", [r["session"] for r in selected], budget["expected_sessions"])
            mean = float(np.mean([r["balanced_accuracy"] for r in selected]))
            audit.close(f"Budget/{policy}/{person}/mean", mean,
                        value(case["participant_future"])[str(person)]["future_balanced_accuracy"])
            vector.append(mean)
        future[policy] = np.array(vector)
        result = estimate(vector, draws)
        compare_estimate(audit, "Budget/" + policy, result, value(case["expected_future"]))
        budget_results[policy] = result
    budget_contrasts = {}
    for name, expected_ref in budget["contrasts"].items():
        left, right = name.split("_minus_")
        result = estimate(future[left] - future[right], draws)
        compare_estimate(audit, "Budget/" + name, result, value(expected_ref))
        budget_contrasts[name] = result
    case = budget["policies"]["label25__none"]
    initial = {value(i)["subject"]: value(i) for i in case["initial_old"]}
    final = {value(i)["subject"]: value(i) for i in case["final_old"]}
    audit.exact("Budget initial old identities", sorted(initial), people)
    audit.exact("Budget final old identities", sorted(final), people)
    old0 = np.array([initial[s]["balanced_accuracy"] for s in people])
    old1 = np.array([final[s]["balanced_accuracy"] for s in people])
    for person in people:
        audit.exact("Budget permanent old class counts", initial[person]["class_counts"], final[person]["class_counts"])
        audit.exact("Budget final old session", final[person]["session"], budget["final_session"])
    old = {}
    for name, vector in [("initial", old0), ("final", old1), ("change", old1-old0)]:
        result = estimate(vector, draws)
        compare_estimate(audit, "Budget/old/" + name, result, value(case["expected_old"])[name])
        old[name] = result
    declines = old1 - old0 < -1e-12
    severe = old1 - old0 <= -.05 + 1e-12
    benefit = future["label25__none"] - future["label0__none"]
    old["participant_counts"] = dict(declined=int(declines.sum()), declined_at_least_5pp=int(severe.sum()),
        declined_with_positive_future_gain=int((declines & (benefit > 0)).sum()),
        declined_ids=[s for s, flag in zip(people, declines) if flag],
        declined_at_least_5pp_ids=[s for s, flag in zip(people, severe) if flag])
    budgets = {k:value(v["label_budget"]) for k,v in budget["policies"].items()}
    savings = 100*(1-budgets["label25__none"]/budgets["label100__none"])
    gain_ratio = 100*(future["label25__none"].mean()-future["label0__none"].mean())/(future["label100__none"].mean()-future["label0__none"].mean())

    constraint_results = {}
    table_rows = []
    for item in document["constraints"]:
        people = value(item["subjects"])
        audit.exact("Constraint sorted participants", people, sorted(people))
        audit.exact("Constraint repetitions", value(item["repetitions"]), REPETITIONS)
        draws = indices(value(item["seed"]), people, item["cohort_index"])
        tag = item["stage"] + "/" + item["cohort"]
        policy_results, policy_vectors = {}, {}
        for policy, case in item["policies"].items():
            audit.exact(tag + "/participant order", [r["subject"] for r in case["participants"]], people)
            rows = [value(r["record"]) for r in case["participants"]]
            old_change = np.array([r["old_final_ba"]-r["old_initial_ba"] for r in rows])
            harm = (old_change <= -.05 + 1e-12).astype(int)
            audit.close(tag + "/" + policy + "/old change", old_change, [r["old_ba_change"] for r in rows])
            audit.exact(tag + "/" + policy + "/harm identities", harm.tolist(), [r["old_harm_ge5pp"] for r in rows])
            audit.exact(tag + "/" + policy + "/harm count", int(harm.sum()), value(case["expected_counts"])["old_harm_ge5pp"])
            vectors = dict(future_ba=np.array([r["future_ba"] for r in rows]),
                           old_initial_ba=np.array([r["old_initial_ba"] for r in rows]),
                           old_final_ba=np.array([r["old_final_ba"] for r in rows]),
                           old_ba_change=old_change, old_harm_ge5pp=harm)
            policy_vectors[policy] = vectors
            policy_results[policy] = {}
            for metric, vector in vectors.items():
                result = estimate(vector, draws)
                compare_estimate(audit, tag + "/" + policy + "/" + metric,
                                 result, value(case["expected_metrics"])[metric])
                policy_results[policy][metric] = result
        target = item["target"]
        contrasts = {}
        for metric in policy_vectors[target]:
            result = estimate(policy_vectors[target][metric]-policy_vectors["own"][metric], draws)
            compare_estimate(audit, tag + "/contrast/" + metric, result, value(item["expected_contrast"])[metric])
            contrasts[metric] = result
        future_lower = contrasts["future_ba"]["interval95"][0]
        harm_upper = contrasts["old_harm_ge5pp"]["interval95"][1]
        dual = dict(future_pass=bool(future_lower >= -.005), harm_pass=bool(harm_upper < 0))
        dual["both_pass"] = dual["future_pass"] and dual["harm_pass"]
        expected_dual = value(item["expected_dual"])
        for field, result in dual.items():
            audit.exact(tag + "/" + field, result, expected_dual[field])
        audit.close(tag + "/future bound", future_lower, expected_dual["future_95_lower_bound"])
        audit.close(tag + "/harm bound", harm_upper, expected_dual["harm_95_upper_bound"])
        constraint_results[tag] = dict(policies=policy_results, contrasts=contrasts, dual_criterion=dual)
        def formatted(metric):
            r=contrasts[metric]
            return dict(mean_pp=100*r["mean"], interval95_pp=[100*x for x in r["interval95"]])
        table_rows.append(dict(stage=item["stage"],cohort=item["cohort"],
                               future_ba=formatted("future_ba"),old_harm_fraction=formatted("old_harm_ge5pp"),
                               joint_criterion_passed=dual["both_pass"]))
    return dict(status="PASS" if not audit.errors else "FAIL", checks=audit.checks,
                maximum_absolute_error=audit.maximum_absolute_error, absolute_tolerance=ATOL,
                errors=audit.errors, source_verification=source_audit,
                lee42=dict(means=means, paired_contrasts=lee_results),
                stieger62_budget=dict(future=budget_results, paired_contrasts=budget_contrasts,
                                      new_label_counts=budgets,label_reduction_percent=savings,
                                      ratio_of_group_mean_gains_percent=gain_ratio,permanent_old=old),
                constraint_stages=constraint_results, retention_table_rows=table_rows,
                scope=document["scope"], boundaries=document["boundaries"],
                method="10000 original-seed paired participant draws; direct index resampling; explicitly interpolated percentile intervals; no production statistics imports")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs",type=Path,default=Path(__file__).with_name("primary_statistical_inputs.json"))
    parser.add_argument("--out",type=Path,help="Write the complete verification report here; otherwise print it.")
    parser.add_argument("--source-root",type=Path,help="Optional repository/package root for exact source SHA256 and JSON-pointer validation.")
    parser.add_argument("--extract-from",type=Path,help="Maintenance only: extract exact archived endpoints from this root into --inputs before verification.")
    parser.add_argument("--self-test",action="store_true",help="Also run small artificial interpolation/pairing/boundary fixtures.")
    args=parser.parse_args()
    if args.extract_from:
        write(args.inputs,extract(args.extract_from))
    report=recompute(read(args.inputs),args.source_root)
    report.update(completed_utc=datetime.now(timezone.utc).isoformat(),
                  input_sha256=digest(args.inputs),script_sha256=digest(__file__),
                  runtime=dict(python=platform.python_version(),numpy=np.__version__))
    if args.self_test:
        report["artificial_self_test"]=self_test()
    if args.out:
        write(args.out,report)
        print(json.dumps(dict(status=report["status"],checks=report["checks"],
                              maximum_absolute_error=report["maximum_absolute_error"],report=str(args.out))))
    else:
        print(json.dumps(report,indent=2,allow_nan=False))
    return 0 if report["status"]=="PASS" else 1


if __name__=="__main__":
    sys.exit(main())
