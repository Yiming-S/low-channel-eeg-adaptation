#!/usr/bin/env python3
"""Describe paired old-test prediction changes for the original Stieger 25% arm.

No model is fitted and no significance test or resampling is performed.
Ordinary execution uses the compact input JSON beside this script. Maintenance
extraction reads only the original v1 model scores and v3 identity/label arrays.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import numpy as np

V1 = 'experiments/reliability_budget_v1/results/eeg/stieger62/'
V3 = 'experiments/feedback_retention_v3/results/eeg/stieger62/'
ANALYSIS = 'experiments/reliability_budget_v1/results/eeg/analysis.json'
POLICY = 'label25__none'
BASELINE_MANUSCRIPT_SHA256 = 'e34c3c8293106dec8cfb2e74782ab59141498392ca808c3b747d30a92013844d'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def resolve(document, pointer):
    value = document
    for part in pointer.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def extract(root):
    root = Path(root)
    specs = [
        ('initial', V1+'initial_old.npz', ['ids', 'indices', 'label25_logit', 'label25_probability']),
        ('final', V1+'session_07_old.npz', ['ids', 'indices', 'label25_logit', 'label25_probability']),
        ('labels', V3+'initial_old.npz', ['ids', 'y']),
    ]
    arrays, array_sources = {}, []
    for name, relative, keys in specs:
        with np.load(root/relative, allow_pickle=False) as archive:
            selected = {key: archive[key].copy() for key in keys}
        arrays[name] = {k: x.tolist() for k, x in selected.items()}
        array_sources.append(dict(role=name, source_file=relative, sha256=sha(root/relative),
            bytes=(root/relative).stat().st_size, keys_read=keys,
            array_shapes={k:list(x.shape) for k,x in selected.items()},
            array_dtypes={k:str(x.dtype) for k,x in selected.items()}))
    assert np.array_equal(arrays['initial']['ids'], arrays['final']['ids'])
    assert np.array_equal(arrays['initial']['ids'], arrays['labels']['ids'])
    assert np.array_equal(arrays['initial']['indices'], arrays['final']['indices'])
    records = []
    for relative in [V1+'initial_old.json', V1+'old_metrics.json']:
        original = read(root/relative)
        for index, row in enumerate(original):
            if row['policy']==POLICY and (relative.endswith('initial_old.json') or row['session']==7):
                records.append(dict(source=relative, json_pointer='/'+str(index), value=row,
                    sha256=sha(root/relative), units='original participant old-test metric record'))
    original = read(root/ANALYSIS)
    for pointer in ['/cohorts/stieger62/fixed_groups/all',
                    '/cohorts/stieger62/final_old_test/label25__none/all/balanced_accuracy']:
        records.append(dict(source=ANALYSIS, json_pointer=pointer, value=resolve(original,pointer),
            sha256=sha(root/ANALYSIS), units='original participant identities or old-test summaries'))
    return dict(schema='stieger25_paired_old_inputs_v1', policy=POLICY,
        initial_session=1, final_session=7, threshold_probability=.5,
        severe_decline_fraction=.05, floating_comparison_tolerance=1e-12,
        manuscript_baseline_sha256=BASELINE_MANUSCRIPT_SHA256,
        expected_reported_counts=dict(participants=62, declining=19, severe_declining=12),
        array_sources=array_sources, arrays=arrays, records=records,
        score_provenance='Initial and final model logits/probabilities are v1 label25 only. v3 contributes ids and y only; no v3 scores are read.',
        description='Classes 0 and 1 are the stored binary labels. All 1,550 permanent-old trials and all 62 participants remain included.')


def source_check(document, root):
    if root is None:
        return dict(mode='compact source-bound values; original files not reopened')
    root=Path(root)
    for source in document['array_sources']:
        assert sha(root/source['source_file'])==source['sha256']
        with np.load(root/source['source_file'],allow_pickle=False) as archive:
            for key in source['keys_read']:
                assert np.array_equal(archive[key],np.asarray(document['arrays'][source['role']][key]))
    cache={}
    for r in document['records']:
        if r['source'] not in cache:
            assert sha(root/r['source'])==r['sha256']
            cache[r['source']]=read(root/r['source'])
        assert resolve(cache[r['source']],r['json_pointer'])==r['value']
    return dict(mode='all source hashes, selected source arrays and JSON pointers matched',
        source_npz_files=len(document['array_sources']), source_json_files=len(cache),
        json_records=len(document['records']))


def describe(document):
    a=document['arrays']; ids=np.asarray(a['initial']['ids'],dtype=np.int64)
    assert np.array_equal(ids,np.asarray(a['final']['ids']))
    assert np.array_equal(ids,np.asarray(a['labels']['ids']))
    assert len(np.unique(ids,axis=0))==len(ids)==1550
    assert np.array_equal(a['initial']['indices'],a['final']['indices'])
    assert np.all(ids[:,1]==1)
    y=np.asarray(a['labels']['y'],dtype=np.int64)
    assert set(y)=={0,1}
    p0=np.asarray(a['initial']['label25_probability'],float)
    p1=np.asarray(a['final']['label25_probability'],float)
    for part,p in [('initial',p0),('final',p1)]:
        logits=np.asarray(a[part]['label25_logit'],float)
        assert np.max(abs(np.exp(-np.logaddexp(0,-logits))-p))<1e-13
    h0=(p0>=document['threshold_probability']).astype(int)
    h1=(p1>=document['threshold_probability']).astype(int)
    c0=h0==y; c1=h1==y
    original={}
    expected_summary=None
    for r in document['records']:
        if isinstance(r['value'],dict) and 'subject' in r['value']:
            row=r['value'];original[(row['subject'],row['session'])]=row
        elif r['json_pointer'].endswith('balanced_accuracy'):
            expected_summary=r['value']
    people=sorted(np.unique(ids[:,0]).tolist());assert people==list(range(1,63))
    rows=[]; maximum_error=0.
    for subject in people:
        mask=ids[:,0]==subject; counts=[]; class_records=[]
        initial_correct=[];final_correct=[]
        for klass in (0,1):
            take=mask & (y==klass); n=int(take.sum());assert n>0
            cc=int((take & c0 & c1).sum());cw=int((take & c0 & ~c1).sum())
            wc=int((take & ~c0 & c1).sum());ww=int((take & ~c0 & ~c1).sum())
            assert cc+cw+wc+ww==n
            counts.append(n);initial_correct.append(cc+cw);final_correct.append(cc+wc)
            class_records.append(dict(label=klass,n=n,correct_to_correct=cc,correct_to_wrong=cw,
                wrong_to_correct=wc,wrong_to_wrong=ww,initial_correct=cc+cw,final_correct=cc+wc,
                single_trial_flip_ba_pp=50/n,net_ba_change_pp=50*(wc-cw)/n))
        ba0=.5*sum(k/n for k,n in zip(initial_correct,counts))
        ba1=.5*sum(k/n for k,n in zip(final_correct,counts));change=ba1-ba0
        for session,actual in [(1,ba0),(7,ba1)]:
            ref=original[(subject,session)]
            assert ref['class_counts']==counts and ref['n']==int(mask.sum())
            error=abs(actual-ref['balanced_accuracy']);maximum_error=max(maximum_error,error);assert error<1e-12
        assert abs(sum(x['net_ba_change_pp'] for x in class_records)-100*change)<1e-12
        rows.append(dict(subject=subject,n=int(mask.sum()),class_counts=counts,classes=class_records,
            initial_ba=ba0,final_ba=ba1,change_ba_pp=100*change,
            declining=bool(change < -document['floating_comparison_tolerance']),
            severe_declining=bool(change <= -document['severe_decline_fraction']+document['floating_comparison_tolerance'])))
    declining=[r['subject'] for r in rows if r['declining']]
    severe=[r['subject'] for r in rows if r['severe_declining']]
    assert len(declining)==document['expected_reported_counts']['declining']
    assert len(severe)==document['expected_reported_counts']['severe_declining']
    means={'initial':np.mean([r['initial_ba'] for r in rows]),'final':np.mean([r['final_ba'] for r in rows]),'change':np.mean([r['change_ba_pp']/100 for r in rows])}
    for key,actual in means.items():
        error=abs(actual-expected_summary[key]['mean']);maximum_error=max(maximum_error,error);assert error<1e-12
    paired=[]
    for i in range(len(ids)):
        paired.append(dict(id=ids[i].tolist(),label=int(y[i]),initial_probability=float(p0[i]),
            final_probability=float(p1[i]),initial_prediction=int(h0[i]),final_prediction=int(h1[i]),
            initial_correct=bool(c0[i]),final_correct=bool(c1[i])))
    return dict(schema='stieger25_paired_old_evidence_v1',status='PASS_DESCRIPTIVE_PAIRED_PREDICTION_AUDIT',
        policy=POLICY,manuscript_baseline_sha256=document['manuscript_baseline_sha256'],
        method=dict(classification='probability >=0.5, exactly as original v1 metric',
            ba='0.5*(correct_class0/n_class0 + correct_class1/n_class1)',
            single_trial_step='50/n_class percentage points for one correctness flip in that class',
            paired_change='50*((wrong_to_correct0-correct_to_wrong0)/n0 + (wrong_to_correct1-correct_to_wrong1)/n1)',
            decline='final BA minus own initial BA < -1e-12',
            severe_decline='final BA minus own initial BA <= -0.05+1e-12; unchanged original 5 pp criterion',
            uncertainty='No significance tests, trial or person bootstrap, individual population-risk intervals, or refitting.'),
        totals=dict(participants=len(rows),trials=len(ids),class_counts=np.bincount(y,minlength=2).tolist(),
            declining_count=len(declining),declining_ids=declining,severe_declining_count=len(severe),severe_declining_ids=severe,
            old_test_n_range=[min(r['n'] for r in rows),max(r['n'] for r in rows)],
            mean_initial_ba=float(means['initial']),mean_final_ba=float(means['final']),mean_change_ba_pp=float(100*means['change'])),
        verification=dict(exact_trial_ids_and_order=True,unique_trial_ids=True,initial_final_indices_equal=True,
            v3_used_for_labels_only=True,all_trial_counts_match_original=True,all_person_ba_match_original=True,
            maximum_ba_absolute_difference=maximum_error),
        participants=rows,severe_participants=[r for r in rows if r['severe_declining']],
        paired_trial_predictions=paired,array_sources=document['array_sources'],records=document['records'],
        interpretation='Observed score changes on a single fixed permanent-old test. Class counts and paired flips describe score resolution; they do not establish participant-specific population risk. A class with one observation cannot acquire additional independent information through within-class resampling.')


def tables(result):
    rows=result['participants'];left=rows[:31];right=rows[31:]
    text=[r'% Insert after the old-loss threshold sensitivity paragraph (baseline manuscript line 818).',
        r'\begin{table}[htbp]',r'\centering',r'\small',r'\setlength{\tabcolsep}{3pt}',
        r'\caption{Permanent-old test size and single-trial balanced-accuracy resolution for all 62 participants in the original Stieger reduced-label shared-model experiment. The initial and final models are evaluated on the same trials. $n_0$ and $n_1$ are the stored class counts, and $N=n_0+n_1$. A single correctness flip in class $c$ changes BA by $50/n_c$ percentage points (pp), with the sign determined by the direction of the flip. Values are rounded to three decimals. The two column groups list participants 1--31 and 32--62; they are not separate cohorts.}',
        r'\label{tab:old-test-resolution}',r'\begin{tabular}{@{}rrrrrr@{\hspace{9pt}}rrrrrr@{}}',r'\toprule',
        r'ID & $n_0$ & $n_1$ & $N$ & $50/n_0$ & $50/n_1$ & ID & $n_0$ & $n_1$ & $N$ & $50/n_0$ & $50/n_1$\\',r'\midrule']
    def cells(r):
        c=r['class_counts'];return f"{r['subject']} & {c[0]} & {c[1]} & {r['n']} & {50/c[0]:.3f} & {50/c[1]:.3f}"
    for a,b in zip(left,right):text.append(cells(a)+' & '+cells(b)+r'\\')
    text += [r'\bottomrule',r'\end{tabular}',r'\end{table}','',r'\begin{table}[htbp]',r'\centering',r'\small',r'\setlength{\tabcolsep}{3pt}',
        r'\caption{Paired prediction changes for the 12 participants with the predefined decline of at least five BA percentage points in the original Stieger reduced-label shared-model experiment. Counts compare the final prediction saved at session 7 with its own initialized prediction on the identical permanent-old trial; no fitting occurs after the terminal session. $C\!\to\!W$ denotes correct to wrong; $W\!\to\!C$ denotes wrong to correct. Initial and final BA are percentages, and $\Delta$ is final minus initial BA in percentage points. All 62 participants remain in the analysis; this table displays the predefined severe-decline subset. Counts are descriptive and do not estimate individual population risk.}',
        r'\label{tab:old-test-paired-flips}',r'\begin{tabular}{@{}rrr rrr rrrr@{}}',r'\toprule',
        r' & & & \multicolumn{3}{c}{BA} & \multicolumn{2}{c}{Class 0} & \multicolumn{2}{c}{Class 1}\\',
        r'\cmidrule(lr){4-6}\cmidrule(lr){7-8}\cmidrule(l){9-10}',
        r'ID & $n_0$ & $n_1$ & Initial & Final & $\Delta$ & $C\!\to\!W$ & $W\!\to\!C$ & $C\!\to\!W$ & $W\!\to\!C$\\',r'\midrule']
    for r in result['severe_participants']:
        a,b=r['classes'];text.append(f"{r['subject']} & {a['n']} & {b['n']} & {100*r['initial_ba']:.3f} & {100*r['final_ba']:.3f} & {r['change_ba_pp']:+.3f} & {a['correct_to_wrong']} & {a['wrong_to_correct']} & {b['correct_to_wrong']} & {b['wrong_to_correct']}"+r'\\')
    text += [r'\bottomrule',r'\end{tabular}',r'\end{table}','']
    return '\n'.join(text)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs',type=Path,default=Path(__file__).with_name('old_test_trial_inputs.json'))
    ap.add_argument('--out-dir',type=Path,default=Path(__file__).parent)
    ap.add_argument('--extract-from',type=Path,help='Maintain compact inputs from archived source files; writes --inputs.')
    ap.add_argument('--source-root',type=Path,help='Additionally compare every source array and JSON pointer.')
    a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
    if a.extract_from:write(a.inputs,extract(a.extract_from))
    document=read(a.inputs);result=describe(document)
    result['source_verification']=source_check(document,a.source_root)
    result['reproduction']=dict(input_sha256=sha(a.inputs),script_sha256=sha(__file__),numpy_version=np.__version__,
        computed_utc=datetime.now(timezone.utc).isoformat())
    write(a.out_dir/'old_test_trial_evidence.json',result)
    (a.out_dir/'old_test_trial_tables.tex').write_text(tables(result))
    print(json.dumps(dict(status=result['status'],totals=result['totals'],verification=result['verification'],
        outputs=['old_test_trial_evidence.json','old_test_trial_tables.tex']),indent=2))


if __name__=='__main__':main()
