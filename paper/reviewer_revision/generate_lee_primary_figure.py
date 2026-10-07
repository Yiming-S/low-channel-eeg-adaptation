"""Render saved Lee endpoints; no fitting, resampling, or inference is performed.

The first three inline axes are copied from the immutable original-figure template.
Only their placement/size is changed. Panel d reads original participant contrasts
and their saved intervals from pilot_summary_groups.json.
"""
from pathlib import Path
import hashlib
import json
import re

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "paper/figures"
STEM = "eeg_lee_primary_contrasts"
SOURCE = "experiments/lee2019_erp_history_v1/results/pilot_summary_groups.json"
TEMPLATE = HERE / "lee_original_figure_template.tex"
PREFIX = ["groups", "confirmation"]
RECORDS = []
CACHE = {}
BLUE = "#0072B2"
ORANGE = "#D55E00"
GRAY = "#8a8a8a"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(source, parts, units):
    if source not in CACHE:
        CACHE[source] = json.loads((ROOT / source).read_text())
    value = CACHE[source]
    for part in parts:
        value = value[part]
    pointer = "/" + "/".join(str(x).replace("~", "~0").replace("/", "~1") for x in parts)
    RECORDS.append(dict(source=source, json_pointer=pointer, value=value,
                        units=units, sha256=sha(ROOT / source)))
    return value


def group(parts, units):
    return read(SOURCE, PREFIX + parts, units)


def contrast(key, units="AUC difference"):
    pre = ["contrasts", key]
    result = {"key": key,
              "mean": group(pre + ["difference"], units),
              "interval": group(pre + ["ci95"], "original descriptive paired 95% interval; " + units),
              "individual": group(pre + ["individual"], units + "; original participant order")}
    assert len(result["individual"]) == 42
    assert np.isclose(np.mean(result["individual"]), result["mean"], rtol=0, atol=1e-14)
    return result


def coords(xs, ys):
    return " ".join(f"({x:.12g},{y:.12g})" for x, y in zip(xs, ys))


def plot_line(xs, ys, opts):
    return "\\addplot[" + opts + "] coordinates {" + coords(xs, ys) + "};\n"


def extract_axes(text):
    return re.findall(r"\\begin\{axis\}\[.*?\\end\{axis\}", text, re.S)


def axis_payload(axis):
    """The first line contains options; all plot/node source after it is immutable."""
    return axis.split("\n", 1)[1]


def load_data():
    ids = group(["subjects"], "participant identifiers")
    assert group(["n_subjects"], "participant count") == 42
    assert ids == list(range(13, 55))
    frozen = contrast("future:mapped_true_pairs-mapped_frozen:auc")
    shuffle = contrast("future:mapped_true_pairs-shuffle_average:auc")
    target = contrast("future:true_pairs-frozen:mse", "standardized omitted-target MSE difference")
    task_keys = ["low_frozen", "low_labels_updated", "mapped_frozen", "mapped_true_pairs",
                 "high_frozen_reference", "high_updated_reference"]
    task_labels = ["Low: frozen", "Low: labels", "Map: frozen", "Map: pairs", "High: frozen", "High: labels"]
    mse_keys = ["initial_mean_target", "frozen", "class_centroid", None, "true_pairs"]
    mse_labels = ["Initial mean", "Frozen", "Centroid", "Shuffled", "True pairs"]
    tasks = [dict(key=k, label=label, mean=group(["means", "future", "classification", k, "auc"], "AUC"), individual=[])
             for k, label in zip(task_keys, task_labels)]
    targets = []
    for key, label in zip(mse_keys, mse_labels):
        keys = [key] if key else [f"shuffle_{1701 + j}" for j in range(5)]
        vals = [group(["means", "future", "structure", k, "mse"], "standardized omitted-target MSE") for k in keys]
        targets.append(dict(key=key, label=label, mean=float(np.mean(vals)), individual=[]))
    person_shuffle_auc = []
    for subject in ids:
        src = f"experiments/lee2019_erp_history_v1/results/sub-{subject:02d}/summary.json"
        assert read(src, ["subject"], "participant identifier") == subject
        for row in tasks:
            row["individual"].append(read(src, ["evaluation", "future", "classification", row["key"], "auc"], "individual original-event AUC"))
        for row in targets:
            keys = [row["key"]] if row["key"] else [f"shuffle_{1701 + j}" for j in range(5)]
            vals = [read(src, ["evaluation", "future", "structure", key, "mse"], "individual standardized omitted-target MSE") for key in keys]
            row["individual"].append(float(np.mean(vals)))
        vals = [read(src, ["evaluation", "future", "classification", f"mapped_shuffle_{1701 + j}", "auc"], "individual original-event shuffled-map AUC") for j in range(5)]
        person_shuffle_auc.append(float(np.mean(vals)))
    for row in tasks + targets:
        assert np.isclose(np.mean(row["individual"]), row["mean"], rtol=0, atol=1e-14)
    assert np.allclose(np.array(tasks[3]["individual"]) - tasks[2]["individual"], frozen["individual"], rtol=0, atol=1e-14)
    assert np.allclose(np.array(tasks[3]["individual"]) - person_shuffle_auc, shuffle["individual"], rtol=0, atol=1e-14)
    assert np.allclose(np.array(targets[4]["individual"]) - targets[1]["individual"], target["individual"], rtol=0, atol=1e-14)
    return dict(subjects=ids, task_controls=tasks, target_controls=targets,
                frozen_contrast=frozen, shuffle_contrast=shuffle, target_contrast=target)


def make_inline(data):
    original = TEMPLATE.read_text()
    axes = extract_axes(original)
    assert len(axes) == 3
    modified = []
    for index, axis in enumerate(axes):
        first, rest = axis.split("\n", 1)
        x, y = [(0, 0), (7.65, 0), (0, -5.65)][index]
        first = re.sub(r"at=\{\([^)]*\)\},anchor=north west,width=[\d.]+cm,height=[\d.]+cm",
                       f"at={{({x}cm,{y}cm)}},anchor=north west,width=5.85cm,height=4.5cm", first)
        # The zero reference line remains; these labels avoid crowding the near-zero ticks.
        if index == 2:
            first = first.replace("xtick={-0.88137358702,0,0.88137358702,2.9982229503,5.29834236561,7.24422802581},xticklabels={-0.01,0,0.01,0.1,1,7}",
                                  "xtick={-0.88137358702,0.88137358702,2.9982229503,5.29834236561,7.24422802581},xticklabels={-0.01,0.01,0.1,1,7}")
        modified.append(first + "\n" + rest)
        assert axis_payload(modified[-1]) == axis_payload(axis)
    fourth = (r"\begin{axis}[axis lines=left,tick align=outside,tick label style={font=\scriptsize},"
              r"label style={font=\scriptsize},title style={font=\small,align=left,at={(0,1.06)},anchor=south west},"
              r"at={(7.65cm,-5.65cm)},anchor=north west,width=5.85cm,height=4.5cm,"
              r"title={d\quad Paired task contrasts},ylabel={AUC difference},"
              r"xmin=-.42,xmax=1.42,ymin=-.11,ymax=.12,xtick={0,1},"
              r"xticklabels={Frozen mapping,Class shuffle},scaled y ticks=false,"
              r"ytick={-.10,-.05,0,.05,.10},ymajorgrids=true,grid style={gray!15}]" + "\n")
    fourth += plot_line([-.42, 1.42], [0, 0], "gray,dashed,forget plot")
    for j, row in enumerate([data["frozen_contrast"], data["shuffle_contrast"]]):
        color = ["blue!70!black", "orange!85!black"][j]
        values = np.array(row["individual"])
        ranks = np.argsort(np.argsort(values, kind="stable"), kind="stable")
        jitter = (ranks % 7 - 3) * .055
        fourth += plot_line(j + jitter, values, color + ",only marks,mark=*,mark size=.95pt,opacity=.65")
        m, (lo, hi) = row["mean"], row["interval"]
        fourth += (f"\\addplot+[black,only marks,mark=diamond*,mark size=2.1pt,error bars/.cd,"
                   f"y dir=both,y explicit,error bar style={{line width=.9pt}},error mark options={{mark size=3pt}}] "
                   f"coordinates {{({j},{m:.12g}) += (0,{hi-m:.12g}) -= (0,{m-lo:.12g})}};\n")
        fourth += f"\\node[font=\\scriptsize,anchor=south] at (axis cs:{j},.104) {{{m:+.4f}}};\n"
    fourth += r"\end{axis}" + "\n"
    caption = (r"Original-event controls and participant-level outcomes in Lee's 42-person confirmation group. "
               r"(a,b) Gray points show individual outcomes; blue diamonds show equal-participant means. "
               r"The logarithmic MSE axis includes all extreme values. High-view classifiers use 62 observed channels "
               r"with frozen or label-updated readouts. Mapped classifiers combine observed Cz/Pz features with "
               r"predictions for the omitted channels and keep the original high-view readout fixed. "
               r"(c) Each point shows one participant's MSE reduction and mapped AUC change relative to frozen mapping. "
               r"The orange diamond and whiskers show means and the original marginal 95\% intervals, not a joint confidence region. "
               r"Positions use $\operatorname{asinh}(\mathrm{MSE\ reduction}/0.01)$, with ticks in original units. "
               r"(d) True-pair mapped AUC minus each indicated control: frozen mapping or the within-participant mean of five "
               r"class-preserving shuffled mappings. Each contrast includes all 42 participant differences; horizontal offsets "
               r"only separate points. Black diamonds and whiskers show the saved paired means and original descriptive "
               r"95\% participant-bootstrap intervals. Positive values favor true pairs. "
               r"Figure~\ref{fig:eeg-lee-history} reports the separate common-history event set.")
    text = ("% FIGURE_BEGIN:eeg-lee-primary-contrasts\n\\begin{figure}[p]\n\\centering\n\\begin{tikzpicture}\n" +
            "\n".join(modified) + "\n" + fourth + "\\end{tikzpicture}\n\\caption{" + caption +
            "}\n\\label{fig:eeg-lee-endpoints}\n\\end{figure}\n% FIGURE_END:eeg-lee-primary-contrasts\n")
    return text, caption, [sha_bytes(axis_payload(a)) for a in axes]


def sha_bytes(text):
    return hashlib.sha256(text.encode()).hexdigest()


def preview(data):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.3,
                         "axes.labelsize": 7.3, "axes.titlesize": 8,
                         "xtick.labelsize": 7, "ytick.labelsize": 7,
                         "axes.spines.right": False, "axes.spines.top": False,
                         "pdf.fonttype": 42})
    fig, axes = plt.subplots(2, 2, figsize=(15/2.54, 11.7/2.54))
    fig.subplots_adjust(left=.175, right=.985, top=.94, bottom=.12, wspace=.58, hspace=.65)
    jitter = (np.arange(42) % 7 - 3) * .035
    for index, (rows, title) in enumerate([(data["task_controls"], "a  Task controls"),
                                           (data["target_controls"], "b  Mapping controls")]):
        ax = axes[0, index]
        ys = np.arange(len(rows)-1, -1, -1)
        for row, y in zip(rows, ys):
            ax.scatter(row["individual"], y+jitter, s=5, color=GRAY, alpha=.4, edgecolors="none")
            ax.plot(row["mean"], y, "D", ms=3.5, color=BLUE)
            x = row["mean"]
            ax.text(x+.008 if index == 0 else x*1.12, y if index == 0 else y+.19,
                    f"{x:.3f}", va="center", fontsize=7)
        ax.set(yticks=ys, yticklabels=[r["label"] for r in rows], ylim=(-.6, len(rows)-.4))
        if index == 0:
            ax.set(xlim=(.2,1.035), xlabel="Original-event AUC")
            assert all(.2 <= v <= 1.035 for row in rows for v in row["individual"])
        else:
            ax.set(xscale="log", xlim=(.05,40), xlabel="Original-event MSE (log scale)")
            assert all(.05 <= v <= 40 for row in rows for v in row["individual"])
        ax.set_title(title, loc="left", pad=11)
        ax.grid(axis="x", alpha=.18)
    ax = axes[1,0]
    target, frozen = data["target_contrast"], data["frozen_contrast"]
    tx = np.arcsinh(-np.array(target["individual"])/.01)
    y = np.array(frozen["individual"])
    ax.scatter(tx, y, s=10, color=BLUE, alpha=.75, edgecolors="none")
    ax.axhline(0, color=GRAY, lw=.7, ls="--"); ax.axvline(0, color=GRAY, lw=.7, ls="--")
    xm = np.arcsinh(-target["mean"]/.01)
    xl, xh = np.arcsinh(-np.array(target["interval"])[::-1]/.01)
    ax.errorbar(xm, frozen["mean"], xerr=[[xm-xl],[xh-xm]],
                yerr=[[frozen["mean"]-frozen["interval"][0]],[frozen["interval"][1]-frozen["mean"]]],
                fmt="D", color=ORANGE, ms=4, capsize=2)
    ticks=[-.01,.01,.1,1,7]
    ax.set(xticks=np.arcsinh(np.array(ticks)/.01), xticklabels=[f"{v:g}" for v in ticks],
           xlim=(-1.2,7.35), ylim=(-.105,.04), xlabel="MSE reduction (asinh scale)", ylabel="Mapped AUC change")
    ax.set_title("c  Mapping and task changes",loc="left",pad=11)
    assert np.all((tx >= -1.2) & (tx <= 7.35) & (y >= -.105) & (y <= .04))
    ax=axes[1,1]
    for j, row in enumerate([frozen, data["shuffle_contrast"]]):
        values=np.asarray(row["individual"])
        ranks=np.argsort(np.argsort(values,kind="stable"),kind="stable")
        jitter=(ranks%7-3)*.055
        ax.scatter(j+jitter,values,s=9,color=[BLUE,ORANGE][j],alpha=.65,edgecolors="none")
        m,(lo,hi)=row["mean"],row["interval"]
        ax.errorbar(j,m,yerr=[[m-lo],[hi-m]],fmt="D",color="black",ms=4,capsize=3,lw=1)
        ax.text(j,.104,f"{m:+.4f}",ha="center",va="bottom",fontsize=7)
        assert np.all((values >= -.11) & (values <= .12)) and -.11 <= lo <= hi <= .12
    ax.axhline(0,color=GRAY,lw=.7,ls="--")
    ax.set(xticks=[0,1],xticklabels=["Frozen mapping","Class shuffle"],xlim=(-.42,1.42),ylim=(-.11,.12),
           yticks=[-.10,-.05,0,.05,.10],ylabel="AUC difference")
    ax.grid(axis="y",alpha=.18)
    ax.set_title("d  Paired task contrasts",loc="left",pad=11)
    for ext in ["png","pdf"]:
        fig.savefig(OUT/f"{STEM}.{ext}",dpi=250,facecolor="white")
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    data=load_data()
    text, caption, payload_hashes=make_inline(data)
    (HERE/"lee_figure.tex").write_text(text)
    preview(data)
    for item in RECORDS:
        value=CACHE[item["source"]]
        for token in item["json_pointer"].split("/")[1:]:
            token=token.replace("~1","/").replace("~0","~")
            value=value[int(token)] if isinstance(value,list) else value[token]
        assert value==item["value"] and sha(ROOT/item["source"])==item["sha256"]
    report=dict(records=RECORDS,panels=data,caption=caption,
                generator=str(Path(__file__).resolve().relative_to(ROOT)),generator_sha256=sha(Path(__file__)),
                text_sources=[dict(source=str(TEMPLATE.relative_to(ROOT)),sha256=sha(TEMPLATE),
                                   role="immutable original three-panel figure; plot and node payload preserved byte-for-byte")],
                transformations=["Panel d uses saved paired AUC differences; original 95% interval endpoints are copied without resampling.",
                                 "The five shuffle scores are averaged within person before comparison; all 42 subjects are retained.",
                                 "Panel c retains asinh(MSE reduction / 0.01); omitting only its zero tick label prevents crowding; zero line remains.",
                                 "Within-column point offsets in d use stable ranks modulo seven, only to separate marks."],
                validation=dict(status="PASS",records=len(RECORDS),sources=len(CACHE),
                                original_three_axis_payload_sha256=payload_hashes,
                                original_three_axis_payloads_identical=True,
                                participant_count_per_new_contrast=42,
                                all_original_and_new_extrema_inside_axes=True,
                                no_new_model_fit_or_resampling=True),
                dimensions=dict(width_cm=15,height_cm=11.7,inline_axis_width_cm=5.85,
                                inline_axis_height_cm=4.5,column_offset_cm=7.65,row_offset_cm=5.65),
                artifacts=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p)) for p in
                           [HERE/"lee_figure.tex",OUT/f"{STEM}.png",OUT/f"{STEM}.pdf"]])
    (OUT/"lee_primary_figure_data.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(dict(status="PASS",records=len(RECORDS),sources=len(CACHE),
                         output=str(HERE/"lee_figure.tex"),export=STEM),indent=2))


if __name__=="__main__":
    main()
