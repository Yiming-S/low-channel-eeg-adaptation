#!/usr/bin/env python3
"""Reconstruct descriptive Lee original-event distributions from saved records.

No model fitting, resampling, new test, exclusion, or replacement of the original
cohort mean/interval is performed. Uses Python's standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


GROUP = "experiments/lee2019_erp_history_v1/pilot_groups/confirmation/results/summary.json"
PERSON = "experiments/lee2019_erp_history_v1/results/sub-{subject:02d}/summary.json"
SHUFFLES = tuple(range(1701, 1706))
ATOL = 1e-12


def pointer(parts):
    return "/" + "/".join(str(x).replace("~", "~0").replace("/", "~1") for x in parts)


def mean(values):
    return math.fsum(values) / len(values)


def directions(values, ids):
    return {
        "positive": [i for i, v in zip(ids, values) if v > 0],
        "zero": [i for i, v in zip(ids, values) if v == 0],
        "negative": [i for i, v in zip(ids, values) if v < 0],
    }


def self_test():
    ids = [1, 2, 4, 7]
    values = [0.0, 1e-20, -1e-20, 2.0]
    assert directions(values, ids) == {
        "positive": [2, 7], "zero": [1], "negative": [4]
    }
    assert math.isclose(4.0 / math.fsum([4.0, 2.0, -1.0]), 0.8)
    assert pointer(["a/b", "x~y"]) == "/a~1b/x~0y"
    return {"status": "PASS", "checks": 3,
            "scope": "Strict point-estimate signs, signed net denominator, RFC6901 escaping."}


def reconstruct(root: Path):
    records, sources, cache, checks = [], {}, {}, []

    def read(source, parts, units):
        if source not in cache:
            raw = (root / source).read_bytes()
            cache[source] = json.loads(raw)
            sources[source] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
        value = cache[source]
        for part in parts:
            value = value[part]
        records.append({"source": source, "json_pointer": pointer(parts),
                        "value": value, "units": units, "sha256": sources[source]["sha256"]})
        return value

    def close(observed, expected, name):
        error = abs(observed - expected)
        if not math.isfinite(error) or error > ATOL:
            raise AssertionError((name, observed, expected, error))
        checks.append({"name": name, "absolute_error": error})

    ids = read(GROUP, ["subjects"], "participant identifiers in archived order")
    assert ids == list(range(13, 55)) and len(set(ids)) == 42
    assert read(GROUP, ["n_subjects"], "participants") == len(ids)
    individual = []
    for subject in ids:
        source = PERSON.format(subject=subject)
        assert read(source, ["subject"], "participant identifier") == subject
        n = read(source, ["evaluation", "future", "n"], "original-event future trials")
        mse, auc = {}, {}
        for key in ["frozen", "true_pairs"] + [f"shuffle_{s}" for s in SHUFFLES]:
            mse[key] = read(source, ["evaluation", "future", "structure", key, "mse"],
                            "MSE in fixed standardized omitted-channel ERP coordinates")
        for key in ["mapped_frozen", "mapped_true_pairs"] + [f"mapped_shuffle_{s}" for s in SHUFFLES]:
            auc[key] = read(source, ["evaluation", "future", "classification", key, "auc"],
                            "original-event future AUC")
        mse_shuffle = mean([mse[f"shuffle_{s}"] for s in SHUFFLES])
        auc_shuffle = mean([auc[f"mapped_shuffle_{s}"] for s in SHUFFLES])
        individual.append({
            "subject": subject, "future_n": n,
            "mse_frozen": mse["frozen"], "mse_true_pairs": mse["true_pairs"],
            "mse_five_shuffle_mean": mse_shuffle,
            "auc_mapped_frozen": auc["mapped_frozen"],
            "auc_mapped_true_pairs": auc["mapped_true_pairs"],
            "auc_mapped_five_shuffle_mean": auc_shuffle,
            "mse_reduction_vs_frozen": mse["frozen"] - mse["true_pairs"],
            "auc_change_vs_frozen": auc["mapped_true_pairs"] - auc["mapped_frozen"],
            "mse_reduction_vs_shuffle": mse_shuffle - mse["true_pairs"],
            "auc_change_vs_shuffle": auc["mapped_true_pairs"] - auc_shuffle,
        })

    contrasts = {}
    specifications = [
        ("future:true_pairs-frozen:mse", "mse_reduction_vs_frozen", -1),
        ("future:mapped_true_pairs-mapped_frozen:auc", "auc_change_vs_frozen", 1),
        ("future:true_pairs-shuffle_average:mse", "mse_reduction_vs_shuffle", -1),
        ("future:mapped_true_pairs-shuffle_average:auc", "auc_change_vs_shuffle", 1),
    ]
    for key, field, sign in specifications:
        base = ["contrasts", key]
        expected = read(GROUP, base + ["individual"], "archived true-pair minus reference participant differences")
        assert len(expected) == len(ids)
        values = [sign * row[field] for row in individual]
        for subject, actual, wanted in zip(ids, values, expected):
            close(actual, wanted, f"{key}:participant{subject}")
        archived_mean = read(GROUP, base + ["difference"], "archived equal-participant mean difference")
        close(mean(values), archived_mean, f"{key}:mean")
        archived_interval = read(GROUP, base + ["ci95"], "original descriptive 95% paired-participant interval")
        contrasts[key] = {"mean_reconstructed": mean(values), "archived_mean": archived_mean,
                          "original_ci95_unmodified": archived_interval,
                          "interval_recomputed": False, "n": len(ids)}

    # Match every included absolute outcome to its saved group mean as well.
    for category, keys in [
        ("structure", ["frozen", "true_pairs"] + [f"shuffle_{s}" for s in SHUFFLES]),
        ("classification", ["mapped_frozen", "mapped_true_pairs"] + [f"mapped_shuffle_{s}" for s in SHUFFLES]),
    ]:
        metric = "mse" if category == "structure" else "auc"
        for key in keys:
            values = [cache[PERSON.format(subject=i)]["evaluation"]["future"][category][key][metric] for i in ids]
            saved = read(GROUP, ["means", "future", category, key, metric], f"archived equal-participant {metric}")
            close(mean(values), saved, f"absolute:{category}:{key}:{metric}")

    gain = [r["mse_reduction_vs_frozen"] for r in individual]
    auc_gain = [r["auc_change_vs_frozen"] for r in individual]
    mse_direction = directions(gain, ids)
    auc_direction = directions(auc_gain, ids)
    discordant = [r["subject"] for r in individual if r["mse_reduction_vs_frozen"] > 0 and r["auc_change_vs_frozen"] <= 0]
    subject24 = next(r for r in individual if r["subject"] == 24)
    net_gain = math.fsum(gain)
    assert net_gain > 0
    assert max(individual, key=lambda r: r["mse_reduction_vs_frozen"])["subject"] == 24
    share = subject24["mse_reduction_vs_frozen"] / net_gain
    return {
        "status": "PASS", "source_population": "Lee participants 13–54; original-event future test; all 42 retained",
        "scope": "Descriptive arithmetic on existing participant endpoints; no new inference or model execution.",
        "definitions": {
            "g_i": "frozen MSE_i minus true-pair MSE_i, so positive values denote lower MSE after paired calibration",
            "a_i": "mapped_true_pairs AUC_i minus mapped_frozen AUC_i",
            "lower_mse_count": "sum_i 1[g_i > 0]",
            "higher_auc_count": "sum_i 1[a_i > 0]",
            "lower_mse_without_higher_auc_count": "sum_i 1[g_i > 0 and a_i <= 0]",
            "id24_net_reduction_share": "100 * g_24 / sum_i g_i, with MSE increases retained as negative contributions in the denominator",
            "shuffle_reference": "Within each participant, arithmetic mean of the five saved class-preserving assignments 1701–1705; assignments are not additional participants.",
            "sign_convention": "Strict unrounded >0, ==0, <0; arithmetic-comparison tolerance does not alter signs.",
            "interpretation": "Sign counts describe observed point estimates, not participant-specific significance. ID24 share describes the net arithmetic reduction, not a variance-explained fraction. All original means and intervals are retained.",
        },
        "summary": {
            "n": len(ids), "mse_reduced": len(mse_direction["positive"]),
            "auc_increased": len(auc_direction["positive"]),
            "mse_reduced_auc_not_increased": len(discordant),
            "mse_reduction_subjects_by_sign": mse_direction, "auc_change_subjects_by_sign": auc_direction,
            "mse_reduced_auc_not_increased_subjects": discordant,
            "id24_mse_reduction": subject24["mse_reduction_vs_frozen"],
            "total_net_mse_reduction": net_gain, "id24_share_fraction": share,
            "id24_share_percent": 100 * share, "id24_share_percent_display": f"{100*share:.2f}",
            "auc_positive_change_sum": math.fsum(x for x in auc_gain if x > 0),
            "auc_negative_change_sum": math.fsum(x for x in auc_gain if x < 0),
        },
        "individual": individual, "original_contrasts": contrasts,
        "verification": {"status": "PASS", "numeric_checks": len(checks), "atol": ATOL,
                         "maximum_absolute_error": max(c["absolute_error"] for c in checks), "checks": checks},
        "sources": sources, "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("lee_distribution_evidence.json"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    result = reconstruct(args.source_root.resolve())
    result["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if args.self_test:
        result["self_test"] = self_test()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": result["status"], "summary": result["summary"],
                      "checks": result["verification"]["numeric_checks"],
                      "maximum_absolute_error": result["verification"]["maximum_absolute_error"],
                      "out": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
