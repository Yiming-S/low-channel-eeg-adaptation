#!/usr/bin/env python3
"""Export fixed-artifact EEG figures and standalone-compatible inline PGFPlots.

No fitting, resampling, interval estimation, or outcome selection occurs here.
"""
from pathlib import Path
import hashlib
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'paper' / 'figures'
CM = 1 / 2.54
BLUE, ORANGE, GRAY = '#0072B2', '#D55E00', '#777777'
RECORDS, CACHE, SOURCES = [], {}, {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(source, parts, units):
    if source not in CACHE:
        path = ROOT / source
        CACHE[source] = json.loads(path.read_text())
        SOURCES[source] = sha(path)
    value = CACHE[source]
    for part in parts:
        value = value[int(part)] if isinstance(value, list) else value[part]
    pointer = '/' + '/'.join(str(p).replace('~', '~0').replace('/', '~1') for p in parts)
    record = dict(source=source, json_pointer=pointer, value=value,
                  units=units, sha256=SOURCES[source])
    if not any(r['source'] == source and r['json_pointer'] == pointer for r in RECORDS):
        RECORDS.append(record)
    return value


def style():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8,
                         'axes.labelsize': 8, 'axes.titlesize': 9,
                         'xtick.labelsize': 7.5, 'ytick.labelsize': 8,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.linewidth': .65, 'lines.linewidth': 1.2,
                         'savefig.facecolor': 'white', 'pdf.fonttype': 42,
                         'ps.fonttype': 42})


def save(fig, stem):
    # Do not use bbox_inches='tight': preserve the requested physical width.
    assert fig.get_size_inches()[0] / CM <= 15
    fig.savefig(OUT / (stem + '.pdf'), metadata={'CreationDate': None})
    fig.savefig(OUT / (stem + '.png'), dpi=300)
    plt.close(fig)


def error_array(rows):
    return np.array([[r['mean'] - r['interval'][0], r['interval'][1] - r['mean']]
                     for r in rows]).T


def pgf_coords(rows, xs=None, ys=None, horizontal=False):
    result = []
    for i, r in enumerate(rows):
        low, high = r['mean'] - r['interval'][0], r['interval'][1] - r['mean']
        if horizontal:
            result.append(f"({r['mean']:.12g},{ys[i]:.12g}) += ({high:.12g},0) -= ({low:.12g},0)")
        else:
            result.append(f"({xs[i]:.12g},{r['mean']:.12g}) += (0,{high:.12g}) -= (0,{low:.12g})")
    return ' '.join(result)


COMMON = (r'axis lines=left,tick align=outside,'
          r'tick label style={font=\scriptsize},label style={font=\scriptsize},'
          r'title style={font=\small,align=left},grid style={gray!15},'
          r'every axis plot/.append style={line width=.8pt},enlarge x limits=false')


def figure_block(name, body, caption, insertion):
    return (f'% FIGURE_BEGIN:{name}\n% Insert {insertion}\n'
            '% Requires graphicx, tikz and pgfplots; all scientific coordinates are inline.\n'
            '\\begin{figure}[t]\n\\centering\n'
            '\\resizebox{14.8cm}{!}{%\n\\begin{tikzpicture}\n' + body +
            '\\end{tikzpicture}%\n}\n' + f'\\caption{{{caption}}}\n'
            f'\\label{{fig:eeg-{name}}}\n\\end{{figure}}\n'
            f'% FIGURE_END:{name}\n')


def budgets():
    src = 'experiments/reliability_budget_v1/results/eeg/analysis.json'
    result = {}
    for cohort in ['stieger62', 'stieger41']:
        pre = ['cohorts', cohort]
        n = read(src, pre + ['n_people'], 'participants')
        key = read(src, pre + ['primary_key'], 'frozen endpoint-rule identifier')
        rows, schedules = [], []
        for policy in ['label0__none', 'label25__none', 'label100__none']:
            path = pre + ['grid', key, 'cases', policy, 'groups', 'all', 'future', 'future_balanced_accuracy']
            mean = read(src, path + ['mean'], 'BA proportion')
            interval = read(src, path + ['conditional95'], 'BA proportion; conditional 95% interval')
            labels = read(src, pre + ['information_budgets', policy, 'additional_labels'], 'new trial labels')
            rows.append(dict(policy=policy, labels=labels, mean=100 * mean,
                             interval=[100 * x for x in interval]))
        for schedule in ['none', 'early', 'uniform', 'late']:
            policy = 'label0__' + schedule
            path = pre + ['grid', key, 'cases', policy, 'groups', 'all', 'future', 'future_structural_mse']
            mean = read(src, path + ['mean'], 'source-PCA target MSE')
            interval = read(src, path + ['conditional95'], 'source-PCA target MSE; conditional 95% interval')
            budget = pre + ['information_budgets', policy]
            pairs = read(src, budget + ['high_per_subject'], 'new paired trials per participant')
            total = read(src, budget + ['additional_high_pairs'], 'new paired trials across cohort')
            sessions = read(src, budget + ['high_sessions'], 'release-after session indices')
            assert total == n * pairs
            assert pairs == (0 if schedule == 'none' else 40)
            schedules.append(dict(schedule=schedule, mean=mean, interval=interval,
                                  pairs=pairs, cohort_pairs=total, release_sessions=sessions))
        result[cohort] = dict(n=n, labels=rows, calibration=schedules)
    fig, axes = plt.subplots(2, 2, figsize=(14.8 * CM, 12.4 * CM))
    fig.subplots_adjust(left=.12, right=.975, bottom=.13, top=.88, hspace=.76, wspace=.30)
    body = ''
    for col, (cohort, color, texcolor, last) in enumerate([
            ('stieger62', BLUE, 'blue!70!black', 7), ('stieger41', ORANGE, 'orange!85!black', 11)]):
        rows, cal = result[cohort]['labels'], result[cohort]['calibration']
        xs = [r['labels'] / 1000 for r in rows]
        n = result[cohort]['n']
        suffix = ' (nested)' if n == 41 else ''
        ax = axes[0, col]
        ax.errorbar(xs, [r['mean'] for r in rows], yerr=error_array(rows), color=color,
                    marker='o', markersize=4, capsize=3)
        ax.set(xlabel='New labels (thousands)', ylabel='Future balanced accuracy (%)' if col == 0 else '',
               xticks=xs, xticklabels=[f'{x:g}' for x in xs], ylim=(57.5, 67),
               xlim=(-xs[-1] * .06, xs[-1] * 1.07))
        ax.set_title(f"{'ab'[col]}  {n} participants{suffix}\nFuture sessions 2–{last}", loc='left', pad=9)
        ax.grid(axis='y', alpha=.2)
        for x, r in zip(xs, rows):
            ax.annotate(f"{r['mean']:.3f}", (x, r['mean']), xytext=(0, 8),
                        textcoords='offset points', ha='center', fontsize=7.4, color=color)
        ax = axes[1, col]
        ax.errorbar(range(4), [r['mean'] for r in cal], yerr=error_array(cal), color=color,
                    marker='o', linestyle='none', markersize=4, capsize=3)
        ticklabels = ['None\n0 pairs'] + [r['schedule'].capitalize() + '\n' +
                      ', '.join(map(str, r['release_sessions'])) for r in cal[1:]]
        ax.set(xticks=range(4), xticklabels=ticklabels, xlim=(-.45, 3.45), ylim=(.19, .32),
               ylabel='Future target MSE' if col == 0 else '', xlabel='Pair-release sessions')
        ax.set_title(f"{'cd'[col]}  {n}: calibration timing", loc='left', pad=9)
        ax.grid(axis='y', alpha=.2)
        at = f'{col * 7.45:.2f}cm'
        ticks = ','.join(f'{x:.12g}' for x in xs)
        task_ylabel = r'Future balanced accuracy (\%)' if col == 0 else ''
        body += (f'\\begin{{axis}}[{COMMON},at={{({at},0)}},anchor=north west,width=7.1cm,height=5.0cm,'
                 f'title={{{"ab"[col]}\\quad {n} participants{suffix}\\\\Sessions 2--{last}}},'
                 f'xlabel={{New labels (thousands)}},ylabel={{{task_ylabel}}},'
                 f'xmin={-xs[-1]*.06:.8g},xmax={xs[-1]*1.07:.8g},ymin=57.5,ymax=67,ytick={{58,60,62,64,66}},'
                 f'xtick={{{ticks}}},xticklabels={{{ticks}}},ymajorgrids=true]\n'
                 f'\\addplot+[{texcolor},mark=*,mark size=1.8pt,error bars/.cd,y dir=both,y explicit] coordinates {{'
                 + pgf_coords(rows, xs=xs) + '};\n\\end{axis}\n')
        ticktex = ['None (0)'] + [r['schedule'].capitalize() + ' (' + ','.join(map(str, r['release_sessions'])) + ')' for r in cal[1:]]
        body += (f'\\begin{{axis}}[{COMMON},at={{({at},-6.0cm)}},anchor=north west,width=7.1cm,height=4.9cm,'
                 f'title={{{"cd"[col]}\\quad {n}: calibration timing}},xlabel={{Pair-release sessions}},'
                 f'ylabel={{{"Future target MSE" if col == 0 else ""}}},xmin=-.45,xmax=3.45,ymin=.19,ymax=.32,'
                 'xtick={0,1,2,3},xticklabels={' + ','.join('{' + t + '}' for t in ticktex) + '},'
                 'x tick label style={font=\\scriptsize,rotate=25,anchor=east},ymajorgrids=true]\n'
                 f'\\addplot+[{texcolor},only marks,mark=*,mark size=1.8pt,error bars/.cd,y dir=both,y explicit] coordinates {{'
                 + pgf_coords(cal, xs=list(range(4))) + '};\n\\end{axis}\n')
    save(fig, 'eeg_budget_calibration')
    caption = (r'Label budget and paired-calibration timing affect separate endpoints in Stieger. '
               r'(a,b) Task performance versus actual new-label count, with no new high-channel pairs. '
               r'The reduced budgets are 8,833/35,787 and 10,833/43,873 labels; the horizontal spacing preserves those unequal counts. '
               r'(c,d) Mapping MSE with no new task labels. Each active schedule releases two batches of 20 pairs per participant; '
               r'the zero-pair reference is a different budget. Batch-release sessions are shown in parentheses. '
               r'The separate classifier is unchanged by mapping schedule. Bars are the original conditional 95\% participant-bootstrap intervals for cohort means, '
               r'not intervals for pairwise differences. Each participant\textquotesingle s future sessions are averaged before equal-participant aggregation. '
               r'The 41-person cohort is nested and has longer follow-up; its larger total label count does not describe a subset of the same release schedule. '
               r'These panels do not establish an optimal calibration interval.')
    return result, figure_block('budget-calibration', body, caption,
                               'after the paragraph beginning "For the separate mapping, forty early pairs".'), caption


def xytext(xs, ys):
    return ' '.join(f'({float(x):.12g},{float(y):.12g})' for x,y in zip(xs,ys))


def pgfplot(xs, ys, opts):
    return r'\addplot[' + opts + '] coordinates {' + xytext(xs,ys) + '};\n'


def inline_axis(x, y, title, opts, content, width=6.0, height=4.65):
    return (f'\\begin{{axis}}[{COMMON},at={{({x}cm,{y}cm)}},anchor=north west,'
            f'width={width}cm,height={height}cm,title={{{title}}},'
            'title style={font=\\small,align=left,at={(0,1.06)},anchor=south west},'
            +opts+']\n'+content+'\\end{axis}\n')


def asinh_values(values, scale):
    return np.arcsinh(np.asarray(values,dtype=float)/scale)


def tick_options(values, scale, axis='x'):
    pos=','.join(f'{v:.12g}' for v in asinh_values(values,scale))
    labels=','.join(f'{v:g}' for v in values)
    return f'{axis}tick={{{pos}}},{axis}ticklabels={{{labels}}}'


def paired_people(src, pre):
    raw=read(src,pre+['per_subject'],'participant identifiers and within-person future-session mean metrics')
    return {int(r['subject']):float(r['structural_nmse']) for r in raw}


def pairing():
    src='experiments/information_mechanisms_v2/results/pairing/summary.json'
    groups=[]
    specs=[('stieger62','Stieger 62',BLUE,'blue!70!black'),
           ('stieger41','Stieger 41*',ORANGE,'orange!85!black'),
           ('yang51','Yang 51','#8B5A9B','violet!80!black')]
    for cohort,label,color,texcolor in specs:
        pre=['cohorts',cohort]; con=pre+['contrasts','true_pairs_minus_shuffle_average','structural_nmse']
        vals={k:read(src,con+[k],'participants' if k.startswith('n_') else 'fixed-initial-variance target NMSE difference')
              for k in ['mean_difference','conditional_subject_bootstrap_95','n_people','n_first_lower','n_first_higher']}
        cases={}; rounds={}
        for case in ['initial_frozen','class_centroid','true_pairs']+[f'shuffle_{20261004+i}' for i in range(5)]:
            cp=pre+['cases',case,'future_primary']
            cases[case]=dict(people=paired_people(src,cp),mean=read(src,cp+['equal_subject','structural_nmse'],'equal-person future-primary target NMSE'))
            rp=pre+['cases',case,'per_round']
            raw=read(src,rp,'per-session equal-person and per-participant target error metrics')
            rounds[case]={int(k):v['equal_subject']['structural_nmse'] for k,v in raw.items()}
        ids=sorted(cases['true_pairs']['people']); sh=[f'shuffle_{20261004+i}' for i in range(5)]
        shuffle=np.mean([[cases[k]['people'][i] for i in ids] for k in sh],axis=0)
        true=np.array([cases['true_pairs']['people'][i] for i in ids]); diff=true-shuffle
        assert len(ids)==vals['n_people'] and int((diff<0).sum())==vals['n_first_lower']
        assert np.isclose(diff.mean(),vals['mean_difference'],atol=1e-14)
        controls=[('Frozen','initial_frozen'),('Centroid','class_centroid'),('Shuffled',None),('True pairs','true_pairs')]
        absrows=[dict(label=l,mean=float(shuffle.mean()) if k is None else cases[k]['mean'],
                      individual=shuffle.tolist() if k is None else [cases[k]['people'][i] for i in ids]) for l,k in controls]
        sessions=sorted(rounds['true_pairs'])
        curve=[rounds['true_pairs'][s]-float(np.mean([rounds[k][s] for k in sh])) for s in sessions]
        groups.append(dict(cohort=cohort,label=label,color=color,texcolor=texcolor,subjects=ids,
                           mean=vals['mean_difference'],interval=vals['conditional_subject_bootstrap_95'],
                           lower=vals['n_first_lower'],higher=vals['n_first_higher'],n=len(ids),
                           individual_difference=diff.tolist(),absolute=absrows,sessions=sessions,session_difference=curve))
    fig,axes=plt.subplots(2,2,figsize=(14.8*CM,12.7*CM))
    fig.subplots_adjust(left=.135,right=.975,bottom=.115,top=.92,hspace=.52,wspace=.45)
    body=''; colors=[g['color'] for g in groups]
    # Original aggregate intervals, with individual direction counts beside each cohort.
    ax=axes[0,0]; ys=[2,1,0]
    for g,y in zip(groups,ys):
        ax.errorbar(g['mean'],y,xerr=np.array([[g['mean']-g['interval'][0]],[g['interval'][1]-g['mean']]]),
                    fmt='o',color=g['color'],capsize=3,markersize=4)
        ax.annotate(f"{g['mean']:+.3f}; {g['lower']}/{g['n']} lower",(g['mean'],y),xytext=(0,10),textcoords='offset points',fontsize=7)
    ax.axvline(0,color=GRAY,ls='--',lw=.7)
    ax.set(yticks=ys,yticklabels=[g['label'] for g in groups],ylim=(-.55,2.65),xlim=(-.19,.96),xlabel='True − shuffled NMSE')
    ax.tick_params(axis='y',labelsize=7)
    ax.set_title('a  Cohort contrasts · 95% CI',loc='left',fontsize=8)
    ax.grid(axis='x',alpha=.18)
    content=pgfplot([0,0],[-.55,2.65],'gray,dashed')
    for g,y in zip(groups,ys):
        content+=r'\addplot+['+g['texcolor']+',only marks,mark=*,error bars/.cd,x dir=both,x explicit] coordinates {'+pgf_coords([g],ys=[y],horizontal=True)+'};\n'
        content+=f'\\node[anchor=south west,font=\\scriptsize] at (axis cs:{g["mean"]:.12g},{y+.14}) {{{g["mean"]:+.3f}; {g["lower"]}/{g["n"]} lower}};\n'
    body+=inline_axis(0,0,r'a\quad Cohort contrasts (95\% CI)',r'xlabel={True minus shuffled NMSE},xmin=-.19,xmax=.96,ymin=-.55,ymax=2.65,ytick={2,1,0},yticklabels={Stieger 62,Stieger 41*,Yang 51},xmajorgrids=true',content)
    # Exact empirical distribution, preserving the large positive Yang observation.
    ax=axes[0,1]; ticks=[-.5,-.1,0,.1,1,15]; content=pgfplot([0,0],[0,1.02],'gray,dashed,forget plot')
    for g in groups:
        values=np.sort(g['individual_difference']); xx=asinh_values(values,.1); yy=np.arange(1,len(values)+1)/len(values)
        sx=np.repeat(xx,2); sy=np.ravel(np.column_stack((np.arange(len(values))/len(values),yy)))
        ax.plot(sx,sy,color=g['color'],lw=1,label=g['label']);ax.plot(xx,yy,'.',color=g['color'],ms=2)
        content+=pgfplot(sx,sy,g['texcolor']+',no marks')
        content+=pgfplot(xx,yy,g['texcolor']+',only marks,mark=*,mark size=.65pt,forget plot')
    ax.axvline(0,color=GRAY,ls='--',lw=.7)
    ax.set(xticks=asinh_values(ticks,.1),xticklabels=[f'{v:g}' for v in ticks],ylim=(0,1.04),
           xlim=(float(asinh_values([-.8],.1)[0]),float(asinh_values([18],.1)[0])),xlabel='Individual ΔNMSE (asinh scale)',ylabel='Cumulative fraction')
    ax.set_title('b  Every participant difference',loc='left',fontsize=8)
    ax.legend(frameon=False,fontsize=7,loc='lower right',handlelength=1.3)
    yg=groups[2]; yi=int(np.argmax(yg['individual_difference'])); extreme=yg['individual_difference'][yi]
    ax.annotate(f"Yang {yg['subjects'][yi]}: +{extreme:.3f}",
                (float(asinh_values([extreme],.1)[0]),1),xytext=(-6,-19),
                textcoords='offset points',ha='right',fontsize=7,color=yg['color'])
    content+=f'\\node[anchor=north east,font=\\scriptsize,text=violet!80!black] at (axis cs:{float(asinh_values([extreme],.1)[0]):.12g},.95) {{Yang {yg["subjects"][yi]}: +{extreme:.3f}}};\n'
    content+=r'\legend{Stieger 62,Stieger 41*,Yang 51}'+'\n'
    body+=inline_axis(8.0,0,r'b\quad Every participant difference',r'xlabel={Individual $\Delta$NMSE (asinh scale)},ylabel={Cumulative fraction},ymin=0,ymax=1.04,xmin=-2.77647,xmax=5.88688,'+tick_options(ticks,.1)+r',legend style={font=\scriptsize,at={(.98,.04)},anchor=south east,draw=none}',content)
    # Absolute mean controls and all underlying participant values, on a log scale.
    ax=axes[1,0]; content=''
    for j,g in enumerate(groups):
        for k,r in enumerate(g['absolute']):
            vals=np.array(r['individual']); jitter=((np.arange(g['n'])%7)-3)*.012+(j-1)*.13
            ax.scatter(k+jitter,vals,s=3.5,alpha=.27,color=g['color'],edgecolors='none')
            content+=pgfplot(k+jitter,vals,g['texcolor']+',only marks,mark=*,mark size=.6pt,opacity=.28,forget plot')
        means=[r['mean'] for r in g['absolute']]
        ax.plot(np.arange(4)+(j-1)*.13,means,'o-',color=g['color'],ms=3,lw=1.4)
        content+=pgfplot(np.arange(4)+(j-1)*.13,means,g['texcolor']+',mark=*,mark size=1.6pt')
    ax.set(yscale='log',xticks=range(4),xticklabels=['Frozen','Centroid','Shuffled','True pairs'],xlim=(-.4,3.4),
           ylim=(.05,1000),ylabel='Target NMSE (log scale)')
    ax.tick_params(axis='x',labelsize=7,rotation=20)
    ax.set_title('c  Absolute controls: people + mean',loc='left',fontsize=8)
    ax.grid(axis='y',alpha=.18)
    body+=inline_axis(0,-5.8,r'c\quad Absolute controls: people + mean',r'ymode=log,ymin=.05,ymax=1000,xmin=-.4,xmax=3.4,xtick={0,1,2,3},xticklabels={Frozen,Centroid,Shuffled,True pairs},x tick label style={font=\scriptsize,rotate=20,anchor=east},ylabel={Target NMSE (log scale)},ymajorgrids=true',content)
    ax=axes[1,1]; content=pgfplot([2,11],[0,0],'gray,dashed')
    for g in groups:
        ax.plot(g['sessions'],g['session_difference'],'o-',color=g['color'],ms=3,lw=1.2)
        content+=pgfplot(g['sessions'],g['session_difference'],g['texcolor']+',mark=*,mark size=1.5pt')
    ax.axhline(0,color=GRAY,ls='--',lw=.7)
    ax.set(xticks=[2,3,4,6,8,10,11],xlim=(1.8,11.2),ylim=(-.15,.31),xlabel='Relative session',ylabel='Mean true − shuffled NMSE')
    ax.set_title('d  Session-by-session contrasts',loc='left',fontsize=8)
    ax.grid(axis='y',alpha=.18)
    body+=inline_axis(8.0,-5.8,r'd\quad Session-by-session contrasts',r'xlabel={Relative session},ylabel={Mean true minus shuffled NMSE},xmin=1.8,xmax=11.2,ymin=-.15,ymax=.31,xtick={2,3,4,6,8,10,11},ymajorgrids=true',content)
    save(fig,'eeg_pairing_forest')
    caption=(r'Pairing effects across cohorts, participants, controls, and sessions. '
             r'(a) Original conditional 95\% participant-bootstrap intervals for true pairs minus the mean of five within-class shuffles; labels count participants with lower error. '
             r'(b) Every participant difference in the primary window, shown as an empirical cumulative distribution. '
             r'The horizontal transformation is $\operatorname{asinh}(\Delta\mathrm{NMSE}/0.1)$, approximately linear near zero and compressing the tails, with ticks in original NMSE units; Yang participant 24 at $+14.563$ is retained. '
             r'(c) Individual absolute NMSE values (small points) and equal-participant means (connected large points), on a logarithmic axis. '
             r'Frozen, class-centroid, shuffled, and true-pair controls use the same fixed target and initial-variance normalizer. '
             r'(d) Equal-participant contrasts at each session, without newly estimated intervals. Stieger releases pairs after sessions 3, 6, and 9 when available; Yang releases after session 2. '
             r'Panels (a--c) average future sessions 4--7 for Stieger 62, 4--11 for Stieger 41, and session 3 for Yang. '
             r'The asterisk marks the nested 41-person cohort; cohorts are not pooled. Shuffled values are within-person means over five assignments, not independent replications. No task classifier is fitted in this experiment.')
    return groups,figure_block('pairing-forest',body,caption,'after the paragraph beginning "The independent ridge pairing control".'),caption


def lee():
    src='experiments/lee2019_erp_history_v1/pilot_groups/confirmation/results/summary.json'
    hist='experiments/lee2019_erp_history_v1/results/history_summary.json'
    ids=read(src,['subjects'],'participant identifiers'); hids=read(hist,['groups','confirmation','subjects'],'participant identifiers')
    assert ids==hids and len(ids)==42
    def con(key,source=src,history=False):
        pre=(['groups','confirmation'] if history else [])+['contrasts',key]
        m=read(source,pre+['difference'],'AUC difference' if key.endswith('auc') else 'standardized target MSE difference')
        ci=read(source,pre+['interval' if history else 'ci95'],'original 97.5% interval' if history else 'original 95% interval')
        ind=read(source,pre+['individual'],'participant difference in the source subject order')
        assert len(ind)==42 and np.isclose(np.mean(ind),m,atol=1e-14)
        if history: assert read(source,pre+['coverage'],'confidence coverage probability')==.975
        return dict(mean=m,interval=ci,individual=ind)
    direct=con('future:low_labels_updated-low_frozen:auc'); mapped=con('future:mapped_true_pairs-mapped_frozen:auc')
    target=con('future:true_pairs-frozen:mse'); targetshuffle=con('future:true_pairs-shuffle_average:mse')
    history=[con('future:label_updated:ordered_timing-current_timing:auc',hist,True),
             con('future:label_updated:ordered_timing-shuffle_average:auc',hist,True)]
    auc=[]
    for label,key in [('Low: frozen','low_frozen'),('Low: labels','low_labels_updated'),('Map: frozen','mapped_frozen'),('Map: pairs','mapped_true_pairs'),('High: frozen','high_frozen_reference'),('High: labels','high_updated_reference')]:
        auc.append(dict(label=label,mean=read(src,['means','future','classification',key,'auc'],'future AUC')))
    mse=[]
    for label,key in [('Initial mean','initial_mean_target'),('Frozen','frozen'),('Centroid','class_centroid'),('True pairs','true_pairs')]:
        mse.append(dict(label=label,mean=read(src,['means','future','structure',key,'mse'],'standardized omitted-channel target MSE')))
    sh=[read(src,['means','future','structure',f'shuffle_{1701+i}','mse'],'standardized omitted-channel target MSE') for i in range(5)]
    mse.insert(3,dict(label='Shuffled',mean=float(np.mean(sh))))
    habs=[]
    for label,key in [('Past only','past_only'),('Timing only','timing_only'),('Current','current'),('Current + time','current_timing'),('Ordered + time','ordered_timing')]:
        habs.append(dict(label=label,mean=read(hist,['groups','confirmation','means','future','classification',key,'label_updated','raw','auc'],'common-history future label-updated AUC')))
    hsh=[read(hist,['groups','confirmation','means','future','classification',f'shuffled_timing_{2701+i}','label_updated','raw','auc'],'common-history future label-updated AUC') for i in range(5)]
    habs.append(dict(label='Shuffled + time',mean=float(np.mean(hsh))))
    habs.append(dict(label='High: labels',mean=read(hist,['groups','confirmation','means','future','classification','high_current_reference','label_updated','raw','auc'],'common-history future high-view label-updated AUC')))
    auc_keys=['low_frozen','low_labels_updated','mapped_frozen','mapped_true_pairs','high_frozen_reference','high_updated_reference']
    mse_keys=['initial_mean_target','frozen','class_centroid',None,'true_pairs']
    history_keys=['past_only','timing_only','current','current_timing','ordered_timing',None,'high_current_reference']
    for rows in [auc,mse,habs]:
        for row in rows: row['individual']=[]
    for person in ids:
        original=f'experiments/lee2019_erp_history_v1/results/sub-{person:02d}/summary.json'
        hperson=f'experiments/lee2019_erp_history_v1/results/history/sub-{person:02d}/summary.json'
        assert read(original,['subject'],'participant identifier')==person
        assert read(hperson,['subject'],'participant identifier')==person
        for row,key in zip(auc,auc_keys):
            row['individual'].append(read(original,['evaluation','future','classification',key,'auc'],'individual original-event future AUC'))
        for row,key in zip(mse,mse_keys):
            keys=[key] if key is not None else [f'shuffle_{1701+i}' for i in range(5)]
            vals=[read(original,['evaluation','future','structure',k,'mse'],'individual original-event target MSE') for k in keys]
            row['individual'].append(float(np.mean(vals)))
        for row,key in zip(habs,history_keys):
            keys=[key] if key is not None else [f'shuffled_timing_{2701+i}' for i in range(5)]
            vals=[read(hperson,['evaluation','future','classification',k,'label_updated','raw','auc'],'individual common-history future AUC') for k in keys]
            row['individual'].append(float(np.mean(vals)))
    for rows in [auc,mse,habs]:
        for row in rows: assert np.isclose(np.mean(row['individual']),row['mean'],atol=1e-14)
    assert all(.2 <= v <= 1.035 for row in auc for v in row['individual'])
    assert all(.05 <= v <= 40 for row in mse for v in row['individual'])
    assert all(.35 <= v <= 1.035 for row in habs for v in row['individual'])
    assert np.allclose(np.array(mse[4]['individual'])-mse[1]['individual'],target['individual'],atol=1e-14)
    assert np.allclose(np.array(auc[3]['individual'])-auc[2]['individual'],mapped['individual'],atol=1e-14)
    # Keep all 42 points; transformation is display-only and does not enter any summary.
    gain=-np.array(target['individual']); task=np.array(mapped['individual']); tx=asinh_values(gain,.01)
    fig,axes=plt.subplots(3,2,figsize=(14.8*CM,15.5*CM))
    fig.subplots_adjust(left=.17,right=.98,bottom=.075,top=.945,wspace=.62,hspace=.60)
    body=''; sizes=dict(width=5.55,height=4.2)
    # Absolute task performance uses original complete-event rows only.
    ax=axes[0,0]; ys=list(range(5,-1,-1)); av=[r['mean'] for r in auc]
    jitter=(np.arange(42)%7-3)*.035
    for row,y in zip(auc,ys):ax.scatter(row['individual'],y+jitter,s=5,color=GRAY,alpha=.40,edgecolors='none')
    ax.plot(av,ys,'D',color=BLUE,ms=3.5)
    for x,y in zip(av,ys): ax.text(x+.008,y,f'{x:.3f}',va='center',fontsize=7)
    ax.set(yticks=ys,yticklabels=[r['label'] for r in auc],xlim=(.2,1.035),ylim=(-.6,5.6),xlabel='Original-event AUC')
    ax.tick_params(axis='y',labelsize=7);ax.set_title('a  Task controls',loc='left',fontsize=8);ax.grid(axis='x',alpha=.18)
    content=''.join(pgfplot(row['individual'],y+jitter,'gray,only marks,mark=*,mark size=.65pt,opacity=.4') for row,y in zip(auc,ys))
    content+=pgfplot(av,ys,'blue!70!black,only marks,mark=diamond*,mark size=1.8pt')
    for x,y in zip(av,ys):content+=f'\\node[anchor=west,font=\\scriptsize] at (axis cs:{x+.008:.12g},{y}) {{{x:.3f}}};\n'
    body+=inline_axis(0,0,r'a\quad Task controls',r'xlabel={Original-event AUC},xmin=.2,xmax=1.035,ymin=-.6,ymax=5.6,ytick={5,4,3,2,1,0},yticklabels={Low: frozen,Low: labels,Map: frozen,Map: pairs,High: frozen,High: labels},xmajorgrids=true',content,**sizes)
    ax=axes[0,1]; ys=list(range(4,-1,-1)); mv=[r['mean'] for r in mse]
    for row,y in zip(mse,ys):ax.scatter(row['individual'],y+jitter,s=5,color=GRAY,alpha=.40,edgecolors='none')
    ax.plot(mv,ys,'D',color=BLUE,ms=3.5)
    for x,y in zip(mv,ys):ax.text(x*1.12,y+.19,f'{x:.3f}',va='center',fontsize=7)
    ax.set(xscale='log',yticks=ys,yticklabels=[r['label'] for r in mse],xlim=(.05,40),ylim=(-.6,4.6),xlabel='Original-event MSE (log scale)')
    ax.tick_params(axis='y',labelsize=7);ax.set_title('b  Mapping controls',loc='left',fontsize=8);ax.grid(axis='x',alpha=.18)
    content=''.join(pgfplot(row['individual'],y+jitter,'gray,only marks,mark=*,mark size=.65pt,opacity=.4') for row,y in zip(mse,ys))
    content+=pgfplot(mv,ys,'blue!70!black,only marks,mark=diamond*,mark size=1.8pt')
    for x,y in zip(mv,ys):content+=f'\\node[anchor=west,font=\\scriptsize] at (axis cs:{x*1.12:.12g},{y+.19}) {{{x:.3f}}};\n'
    body+=inline_axis(8.0,0,r'b\quad Mapping controls',r'xlabel={Original-event MSE (log scale)},xmode=log,xmin=.05,xmax=40,ymin=-.6,ymax=4.6,ytick={4,3,2,1,0},yticklabels={Initial mean,Frozen,Centroid,Shuffled,True pairs},xmajorgrids=true',content,**sizes)
    ax=axes[1,0];ticks=[-.01,0,.01,.1,1,7]
    ax.scatter(tx,task,s=10,color=BLUE,alpha=.75,edgecolors='none')
    ax.axhline(0,color=GRAY,lw=.7,ls='--');ax.axvline(0,color=GRAY,lw=.7,ls='--')
    xmean=-target['mean']; xc=-np.array(target['interval'])[::-1]
    ax.errorbar(asinh_values([xmean],.01)[0],mapped['mean'],
                xerr=[[asinh_values([xmean],.01)[0]-asinh_values([xc[0]],.01)[0]],[asinh_values([xc[1]],.01)[0]-asinh_values([xmean],.01)[0]]],
                yerr=[[mapped['mean']-mapped['interval'][0]],[mapped['interval'][1]-mapped['mean']]],fmt='D',color=ORANGE,ms=4,capsize=2)
    ax.set(xticks=asinh_values(ticks,.01),xticklabels=[f'{v:g}' for v in ticks],xlim=(-1.2,7.35),ylim=(-.105,.04),
           xlabel='MSE reduction (asinh scale)',ylabel='Mapped AUC change')
    ax.set_title('c  Mapping and task changes',loc='left',fontsize=8)
    ax.text(.98,.04,'42 people; diamond = mean',transform=ax.transAxes,ha='right',fontsize=7)
    content=pgfplot([-1.2,7.35],[0,0],'gray,dashed')+pgfplot([0,0],[-.105,.04],'gray,dashed')+pgfplot(tx,task,'blue!70!black,only marks,mark=*,mark size=1.1pt,opacity=.75')
    xlo,xhi=asinh_values(xc,.01);xm=float(asinh_values([xmean],.01)[0])
    content+=f'\\addplot+[orange!85!black,only marks,mark=diamond*,mark size=2pt,error bars/.cd,x dir=both,x explicit,y dir=both,y explicit] coordinates {{({xm:.12g},{mapped["mean"]:.12g}) += ({xhi-xm:.12g},{mapped["interval"][1]-mapped["mean"]:.12g}) -= ({xm-xlo:.12g},{mapped["mean"]-mapped["interval"][0]:.12g})}};\n'
    body+=inline_axis(0,-5.35,r'c\quad Mapping and task changes',r'xlabel={MSE reduction (asinh scale)},ylabel={Mapped AUC change},xmin=-1.2,xmax=7.35,ymin=-.105,ymax=.04,'+tick_options(ticks,.01),content,**sizes)
    ax=axes[1,1];ys=list(range(6,-1,-1));hv=[r['mean'] for r in habs]
    for row,y in zip(habs,ys):ax.scatter(row['individual'],y+jitter,s=5,color=GRAY,alpha=.40,edgecolors='none')
    ax.plot(hv,ys,'D',color=BLUE,ms=3.5)
    for x,y in zip(hv,ys):ax.text(x+.005,y,f'{x:.3f}',va='center',fontsize=7)
    ax.set(yticks=ys,yticklabels=[r['label'] for r in habs],xlim=(.35,1.035),ylim=(-.6,6.6),xlabel='Common-history AUC')
    ax.tick_params(axis='y',labelsize=7);ax.set_title('d  Updated history controls',loc='left',fontsize=8);ax.grid(axis='x',alpha=.18)
    content=''.join(pgfplot(row['individual'],y+jitter,'gray,only marks,mark=*,mark size=.65pt,opacity=.4') for row,y in zip(habs,ys))
    content+=pgfplot(hv,ys,'blue!70!black,only marks,mark=diamond*,mark size=1.8pt')
    for x,y in zip(hv,ys):content+=f'\\node[anchor=west,font=\\scriptsize] at (axis cs:{x+.005:.12g},{y}) {{{x:.3f}}};\n'
    body+=inline_axis(8.0,-5.35,r'd\quad Updated history controls',r'xlabel={Common-history AUC},xmin=.35,xmax=1.035,ymin=-.6,ymax=6.6,ytick={6,5,4,3,2,1,0},yticklabels={Past only,Timing only,Current,Current + time,Ordered + time,Shuffled + time,High: labels},xmajorgrids=true',content,**sizes)
    ax=axes[2,0];ys=[1,0];labels=['History added','Order preserved']
    ax.errorbar([r['mean'] for r in history],ys,xerr=error_array(history),fmt='o',color=BLUE,capsize=3,ms=4)
    for r,y in zip(history,ys):ax.annotate(f"{r['mean']:+.4f}",(r['mean'],y),xytext=(0,9),textcoords='offset points',ha='center',fontsize=7)
    ax.axvline(0,color=GRAY,lw=.7,ls='--');ax.set(yticks=ys,yticklabels=labels,xlim=(-.0105,.007),ylim=(-.5,1.6),xlabel='Common-history ΔAUC')
    ax.tick_params(axis='y',labelsize=7);ax.set_title('e  History contrasts · 97.5% CI',loc='left',fontsize=8);ax.grid(axis='x',alpha=.18)
    content=pgfplot([0,0],[-.5,1.6],'gray,dashed')+r'\addplot+[blue!70!black,only marks,mark=*,error bars/.cd,x dir=both,x explicit] coordinates {'+pgf_coords(history,ys=ys,horizontal=True)+'};\n'
    body+=inline_axis(0,-10.7,r'e\quad History contrasts (97.5\% CI)',r'xlabel={Common-history $\Delta$AUC},xmin=-.0105,xmax=.007,ymin=-.5,ymax=1.6,ytick={1,0},yticklabels={History added,Order preserved},scaled x ticks=false,xmajorgrids=true',content,**sizes)
    ax=axes[2,1]; content=pgfplot([-.03,.032],[0,0],'gray,dashed')
    for j,(r,label,color,tc) in enumerate(zip(history,labels,[BLUE,ORANGE],['blue!70!black','orange!85!black'])):
        vals=np.asarray(r['individual']); order=np.argsort(np.argsort(vals,kind='stable'),kind='stable'); jitter=(order%7-3)*.045
        ax.scatter(np.full(42,j)+jitter,vals,s=9,alpha=.8,color=color,edgecolors='none')
        ax.plot(j,r['mean'],'D',color='black',ms=4)
        content+=pgfplot(j+jitter,vals,tc+',only marks,mark=*,mark size=1pt,opacity=.8')
        content+=pgfplot([j],[r['mean']],'black,only marks,mark=diamond*,mark size=1.8pt')
        ax.text(j,.033,f'{int((vals>0).sum())}/42 positive',ha='center',fontsize=7)
    ax.axhline(0,color=GRAY,lw=.7,ls='--');ax.set(xticks=[0,1],xticklabels=labels,xlim=(-.4,1.4),ylim=(-.027,.039),ylabel='Individual ΔAUC')
    ax.tick_params(axis='x',labelsize=7);ax.set_title('f  Every history contrast',loc='left',fontsize=8)
    content=pgfplot([-.4,1.4],[0,0],'gray,dashed')+content.split('\n',1)[1]
    for j,r in enumerate(history):content+=f'\\node[font=\\scriptsize] at (axis cs:{j},.033) {{{int((np.array(r["individual"])>0).sum())}/42 positive}};\n'
    body+=inline_axis(8.0,-10.7,r'f\quad Every history contrast',r'ylabel={Individual $\Delta$AUC},xmin=-.4,xmax=1.4,ymin=-.027,ymax=.039,xtick={0,1},xticklabels={History added,Order preserved},scaled y ticks=false',content,**sizes)
    save(fig,'eeg_lee_endpoints')
    caption=(r'Controls and participant heterogeneity in Lee\textquotesingle s 42-person confirmation group. '
             r'(a,b) Original-event individuals (gray points) and equal-participant means (blue diamonds); logarithmic MSE scaling retains all extremes. High-view classifiers observe 62 channels with separate frozen and label-updated readouts. Mapped classifiers combine Cz/Pz with predicted omitted channels and keep the original high-view readout. The original aggregate contrasts are reported in the main text. '
             r'(c) Every point pairs one participant\textquotesingle s original-event MSE reduction with their mapped AUC change. The orange diamond and whiskers are aggregate means and original marginal 95\% intervals, not a joint region. Positions use $\operatorname{asinh}(\mathrm{MSE\ reduction}/0.01)$, with ticks in original units. '
             r'(d--f) Separate common-history events and label-updated classifiers. The high reference in (d) uses these same common-history events. ``Ordered + time\textquotesingle\textquotesingle\ and ``shuffled + time\textquotesingle\textquotesingle\ include current features, the indicated history, and timing. '
             r'``History added\textquotesingle\textquotesingle\ compares ordered/current/timing with current/timing; ``order preserved\textquotesingle\textquotesingle\ compares it with the five-shuffle mean. '
             r'(e) Original 97.5\% confirmation intervals; neither lower bound exceeds zero. (f) All 42 individual differences per contrast, with black mean diamonds. Dot offsets only separate points. Original-event and common-history masks differ; no new intervals or tests are calculated.')
    result=dict(subjects=ids,original_auc=auc,original_target_mse=mse,
                original_contrasts=dict(direct=direct,mapped=mapped,target=target,target_shuffle=targetshuffle),
                scatter=dict(mse_reduction=gain.tolist(),mapped_auc_change=task.tolist(),
                             same_person_quadrants=dict(mapping_gain_task_gain=int(((gain>0)&(task>0)).sum()),mapping_gain_task_loss=int(((gain>0)&(task<0)).sum()),mapping_loss_task_gain=int(((gain<0)&(task>0)).sum()),mapping_loss_task_loss=int(((gain<0)&(task<0)).sum()))),
                history_absolute=habs,history_contrasts=history)
    return result,figure_block('lee-endpoints',body,caption,'after the paragraph beginning "The two predefined history comparisons".'),caption

def main():
    OUT.mkdir(exist_ok=True)
    style()
    budget,b1,c1=budgets();pairs,b2,c2=pairing();erp,b3,c3=lee()
    tex=ROOT/'paper/figure_blocks_eeg.tex'
    tex.write_text('% Fully inline evidence-driven figure blocks; no external graphics or tables.\n\n'+b1+'\n'+b2+'\n'+b3)
    # Verify every emitted original value independently by traversing its pointer.
    for r in RECORDS:
        value=json.loads((ROOT/r['source']).read_text())
        for token in r['json_pointer'].split('/')[1:]:
            key=token.replace('~1','/').replace('~0','~')
            value=value[int(key)] if isinstance(value,list) else value[key]
        assert value==r['value']
        assert sha(ROOT/r['source'])==r['sha256']
    metadata=dict(records=RECORDS,panels=dict(budget_calibration=budget,pairing=pairs,lee=erp),
                  transformations=[
                      'Budget BA means/intervals: multiply original proportions by100.',
                      'Budget x positions: divide actual released label counts by1000; preserve unequal spacing.',
                      'Forest whiskers: mean-lower and upper-mean from original saved confidence limits.',
                      'Pairing participant differences: subtract each participant five-shuffle mean from true-pair future_primary NMSE; match subject IDs exactly.',
                      'Pairing empirical CDF: sorted participant differences plotted at rank/n with exact steps, separately by cohort; display x=asinh(difference/0.1), ticks in raw units.',
                      'Absolute control plots: all participant values and source equal-person means; averaged shuffles use the arithmetic within-person mean of five assignments. Log scaling is display-only.',
                      'Session contrast curves: saved equal-person true NMSE minus average saved equal-person shuffle NMSE for each session; no new intervals.',
                      'Lee mapping/task scatter: x=frozen-minus-true MSE, y=true-minus-frozen mapped AUC for the same 42 source subjects; display x=asinh(MSE reduction/0.01). Whiskers transform existing marginal 95% endpoints.',
                      'Individual dot offsets are deterministic display offsets independent of inference; every original participant value is preserved.'
                  ],captions=dict(budget_calibration=c1,pairing=c2,lee=c3),
                  limits=['Stieger41 is nested; its follow-up and label totals differ from Stieger62.',
                          'Cohort-mean budget intervals are not paired contrast intervals.',
                          'Direction counts use within-person future evaluation means, not individual significance tests.',
                          'Lee original-event and common-history masks differ; target MSE and AUC are separate endpoints.'],
                  independent_data_available={
                      'budget':'experiments/reliability_budget_v1/results/eeg/{cohort}/session_{SS}.json: per_subject_future contains participant/session metrics; session_{SS}_prediction.npz preserves predictions.',
                      'pairing':'The pairing source artifact contains cohorts/{cohort}/cases/{case}/future_primary/per_subject; sign counts plotted here are its saved counts.',
                      'lee':'Original-event and history participant summary JSONs supply all absolute values; source contrasts retain paired vectors and existing aggregate intervals for the same42 subject IDs.'},
                  generator='paper/figure_assets_eeg.py',generator_sha256=sha(Path(__file__)),
                  validation=dict(records=len(RECORDS),all_pointers_exact=True,no_new_statistical_estimation=True,
                                  maximum_export_width_cm=14.8,inline_tex_no_external_data=True),
                  artifacts={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size)
                             for p in list(OUT.glob('eeg_*.pdf'))+list(OUT.glob('eeg_*.png'))+[tex]})
    (OUT/'eeg_figure_data.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps(metadata['validation']))


if __name__=='__main__':
    main()
