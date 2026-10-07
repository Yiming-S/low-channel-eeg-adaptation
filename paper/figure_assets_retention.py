#!/usr/bin/env python3
"""Render existing retention evidence; no fitting, selection, or resampling.

Only the uniquely named retention assets are written. Numeric provenance uses
RFC6901 JSON pointers into immutable experiment artifacts. Both figure blocks
are entirely inline TikZ/pgfplots, with no external data or image dependency.
"""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'paper' / 'figures'
OUT.mkdir(exist_ok=True)
records, sources, cache = [], {}, {}

def load(source):
    if source not in cache:
        p = ROOT / source
        cache[source] = json.loads(p.read_text())
        sources[source] = {'bytes': p.stat().st_size,
                           'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    return cache[source]

def record(source, pointer, units):
    value = load(source)
    for key in pointer.split('/')[1:]:
        key = key.replace('~1', '/').replace('~0', '~')
        value = value[int(key)] if isinstance(value, list) else value[key]
    records.append({'source': source, 'json_pointer': pointer, 'value': value,
                    'units': units, 'sha256': sources[source]['sha256']})
    return value

def find(rows, **query):
    matches = [(i, row) for i, row in enumerate(rows)
               if all(row.get(k) == v for k, v in query.items())]
    assert len(matches) == 1, (query, len(matches))
    return matches[0]

V1 = 'experiments/reliability_budget_v1/results/eeg/'
summary_source, analysis_source = V1 + 'summary.json', V1 + 'analysis.json'
summary, analysis = load(summary_source), load(analysis_source)
panels = []
tol = 1e-10  # percentage-point comparisons; consistent roundoff protection
for cohort in ['stieger62', 'stieger41']:
    base = f'/cohorts/{cohort}'
    n = record(summary_source, base + '/n_subjects', 'participants')
    session = record(summary_source, base + '/n_sessions', 'relative sessions')
    qualification = record(analysis_source, base + '/qualification_counts', 'participants')
    group_ids = record(analysis_source, base + '/fixed_groups', 'participant IDs')
    joint_ids = set(group_ids['joint'])
    task_ids = set(group_ids['task'])
    structure_ids = set(group_ids['structure'])
    ids = group_ids['all']
    assert n == len(ids) and joint_ids == task_ids & structure_ids
    assert qualification == dict(task=len(task_ids), structure=len(structure_ids), joint=len(joint_ids))
    categories = [len(joint_ids), len(task_ids - structure_ids),
                  len(structure_ids - task_ids), len(set(ids) - task_ids - structure_ids)]
    initial_source = V1 + cohort + '/initial_old.json'
    final_source = V1 + cohort + '/old_metrics.json'
    initial, final = load(initial_source), load(final_source)
    people = []
    for subject in ids:
        row = {'subject': subject, 'joint_eligible': subject in joint_ids,
               'task_eligible': subject in task_ids, 'target_eligible': subject in structure_ids}
        row['category'] = (0 if subject in joint_ids else 1 if subject in task_ids
                           else 2 if subject in structure_ids else 3)
        for output, source, rows, query in [
            ('old_initial_ba', initial_source, initial, dict(subject=subject, policy='label25__early')),
            ('old_final_ba', final_source, final, dict(subject=subject, policy='label25__early', session=session))]:
            index, obj = find(rows, **query)
            row[output] = record(source, f'/{index}/balanced_accuracy', 'balanced accuracy, proportion')
            if output == 'old_initial_ba':
                row['old_class_counts'] = record(source, f'/{index}/class_counts', 'trials per class')
            record(source, f'/{index}/subject', 'participant ID')
            record(source, f'/{index}/policy', 'policy identity')
        for label in ['label0', 'label25']:
            pointer = base + f'/cases/{label}__early/groups/all/per_subject'
            rows = summary['cohorts'][cohort]['cases'][label+'__early']['groups']['all']['per_subject']
            index, obj = find(rows, subject=subject)
            row[label+'_future_ba'] = record(summary_source, pointer+f'/{index}/balanced_accuracy', 'mean session balanced accuracy, proportion')
            record(summary_source, pointer+f'/{index}/subject', 'participant ID')
            # Pairing schedules must not modify the separate task-classifier path.
            for schedule in ['none', 'uniform', 'late']:
                other = summary['cohorts'][cohort]['cases'][label+'__'+schedule]['groups']['all']['per_subject']
                _, matched = find(other, subject=subject)
                assert obj['balanced_accuracy'] == matched['balanced_accuracy']
        row['old_change_pp'] = 100*(row['old_final_ba']-row['old_initial_ba'])
        row['future_gain_pp'] = 100*(row['label25_future_ba']-row['label0_future_ba'])
        people.append(row)
    x = np.array([p['future_gain_pp'] for p in people])
    y = np.array([p['old_change_pp'] for p in people])
    actual_mean = record(analysis_source, base+'/final_old_test/label25__early/all/balanced_accuracy/change/mean', 'balanced accuracy change, proportion')
    assert abs(y.mean()/100-actual_mean) < 1e-13
    actual_gain = record(analysis_source, base+'/paired_primary_contrasts/label25__early_minus_label0__early/all/future_balanced_accuracy/mean', 'paired balanced accuracy change, proportion')
    assert abs(x.mean()/100-actual_gain) < 1e-13
    stats = dict(n=n, old_decline_n=int((y < -tol).sum()), severe_old_harm_n=int((y <= -5+tol).sum()),
                 future_gain_n=int((x > tol).sum()),
                 future_gain_and_old_decline_n=int(((x > tol)&(y < -tol)).sum()),
                 future_gain_and_severe_old_harm_n=int(((x > tol)&(y <= -5+tol)).sum()),
                 old_mean_change_pp=float(y.mean()), old_median_change_pp=float(np.median(y)),
                 future_mean_gain_pp=float(x.mean()), future_median_gain_pp=float(np.median(x)),
                 old_range_pp=[float(y.min()), float(y.max())], future_range_pp=[float(x.min()), float(x.max())])
    panels.append(dict(cohort=cohort, n=n, final_session=session, qualification=qualification,
                       exclusive_eligibility_counts=categories, people=people, statistics=stats))

stages = []
specs = [
    ('reliability_followup_v2', 'Stage 2: output penalty', 'Shared classifier; 25% labels', 'label25_lambda0',
     [('label25_lambda0p1_minus_label25_lambda0', 'lambda=0.1', 'label25_lambda0p1'),
      ('label25_lambda1_minus_label25_lambda0', 'lambda=1', 'label25_lambda1'),
      ('label25_lambda10_minus_label25_lambda0', 'lambda=10', 'label25_lambda10')]),
    ('feedback_retention_v3', 'Stage 3: feedback sources', 'Personal heads; recipient-matched labels', 'own',
     [('other_minus_own', 'Other', 'other'), ('mixed_minus_own', 'Mixed', 'mixed'),
      ('own_personal_replay_minus_own', 'Personal replay', 'own_personal_replay')]),
    ('confirmation_prior_constraints_v4', 'Stage 4: constraints', 'Personal heads; same own-feedback IDs', 'own',
     [('own_functional_minus_own', 'Line', 'own_functional'),
      ('own_constrained_minus_own', 'Full space', 'own_constrained')])]
for dirname, title, subtitle, baseline, arms in specs:
    source = f'experiments/{dirname}/results/eeg/analysis.json'
    data = load(source)
    base = '/cohorts/stieger62'
    stage = {'source': source, 'title': title, 'subtitle': subtitle, 'n': 62, 'baseline': baseline, 'arms': []}
    bm = base+f'/cases/{baseline}/groups/all/metrics'
    stage['baseline_future_ba'] = record(source, bm+'/future_ba', 'balanced accuracy, proportion')
    stage['baseline_severe_harm'] = record(source, bm+'/old_harm_ge5pp', 'participant proportion')
    stage['baseline_severe_n'] = round(stage['baseline_severe_harm']['mean']*62)
    for contrast, name, policy in arms:
        ptr = base+'/paired_contrasts/'+contrast+'/all'
        values = {}
        for metric in ['future_ba', 'old_harm_ge5pp']:
            raw = record(source, ptr+'/'+metric, 'paired difference, proportion')
            interval = raw.get('conditional_interval', raw.get('conditional95'))
            values[metric] = dict(mean_pp=100*raw['mean'], interval_pp=[100*v for v in interval],
                                  confidence=raw.get('confidence', .95))
        harm_raw = record(source, base+f'/cases/{policy}/groups/all/metrics/old_harm_ge5pp', 'participant proportion')
        item = dict(name=name, policy=policy, contrast=contrast, **values,
                    severe_harm_n=round(harm_raw['mean']*62))
        assert abs((item['severe_harm_n']-stage['baseline_severe_n'])/62*100-values['old_harm_ge5pp']['mean_pp']) < 1e-12
        if dirname == 'confirmation_prior_constraints_v4':
            item['dual_target'] = record(source, base+'/dual_targets/'+policy, 'original prespecified decision')
            assert item['dual_target']['future_pass'] == (values['future_ba']['interval_pp'][0] >= -.5)
            assert item['dual_target']['harm_pass'] == (values['old_harm_ge5pp']['interval_pp'][1] < 0)
            assert not item['dual_target']['both_pass']
        stage['arms'].append(item)
    stages.append(stage)

COLORS = ['#0072B2', '#56B4E9', '#E69F00', '#B6BBC2']
LABELS = ['Task + target', 'Task only', 'Target only', 'Neither']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'axes.titlesize':8.5,
                    'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,
                    'axes.spines.top':False,'axes.spines.right':False,
                    'pdf.fonttype':42,'ps.fonttype':42})

def style(ax):
    ax.grid(color='#E7E8EB', linewidth=.5)
    ax.set_axisbelow(True)
    ax.tick_params(length=2.5, width=.5)

fig = plt.figure(figsize=(15/2.54, 11/2.54))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 2.35], hspace=.67, wspace=.28,
                     left=.12, right=.985, top=.91, bottom=.12)
ax = fig.add_subplot(gs[0, :])
for pos, p in [(1, panels[0]), (0, panels[1])]:
    start = 0
    for count, color in zip(p['exclusive_eligibility_counts'], COLORS):
        ax.barh(pos, count, left=start, color=color, height=.58, edgecolor='white', linewidth=.6)
        ax.text(start+count/2, pos, str(count), ha='center', va='center', fontsize=8,
                color='white' if color==COLORS[0] else '#17232D')
        start += count
ax.set(xlim=(0, 64), ylim=(-.55,1.55), yticks=[0,1], yticklabels=['Nested 41','All 62'], xticks=[0,10,20,30,40,50,60], xlabel='Number of participants')
ax.set_title('A  Initial eligibility: all participants retained in the analysis', loc='left', pad=16)
ax.legend(handles=[Patch(facecolor=c,label=l) for c,l in zip(COLORS,LABELS)],
          loc='lower center', bbox_to_anchor=(.5,1.015), ncol=4, frameon=False,
          fontsize=7, handlelength=1.2, columnspacing=1.2)
ax.spines[['top','right','left']].set_visible(False)
ax.tick_params(axis='y', length=0)
for j,p in enumerate(panels):
    ax = fig.add_subplot(gs[1,j]);style(ax)
    ax.axhspan(-60,-5, facecolor='#FCEFEA', alpha=.75)
    ax.axhline(0,color='#66717D',linewidth=.7)
    ax.axvline(0,color='#66717D',linewidth=.7)
    ax.axhline(-5,color='#B44D34',linestyle='--',linewidth=.8)
    for cat, color in enumerate(COLORS):
        rows=[q for q in p['people'] if q['category']==cat]
        ax.scatter([q['future_gain_pp'] for q in rows],[q['old_change_pp'] for q in rows],
                   s=17,color=color,edgecolors='white',linewidths=.35,zorder=3)
    st=p['statistics']
    ax.scatter(st['future_mean_gain_pp'],st['old_mean_change_pp'], marker='+',color='#101820',s=100,linewidths=1.4,zorder=5)
    ax.set(xlim=(-8,8),ylim=(-60,40),xticks=[-8,-4,0,4,8],yticks=[-60,-40,-20,0,20,40],
           xlabel='Future BA gain vs 0% labels (pp)', ylabel='Permanent-old BA change (pp)' if j==0 else '')
    ax.set_title(f"{'B' if j==0 else 'C'}  {'All 62' if j==0 else 'Nested 41'}: sessions 2–{p['final_session']}",loc='left',pad=8)
    ax.text(.025,.975,f"Old decline: {st['old_decline_n']}/{p['n']}\nLoss ≥5 pp: {st['severe_old_harm_n']}/{p['n']}",
            transform=ax.transAxes,ha='left',va='top',fontsize=7,
            bbox=dict(facecolor='white',edgecolor='none',alpha=.87,pad=2))
    if j==0:
        q=next(q for q in p['people'] if q['subject']==5)
        ax.annotate('ID 5: old test has\n11 / 1 trials by class',xy=(q['future_gain_pp'],q['old_change_pp']),
                    xytext=(-7.5,-45),fontsize=6.8,color='#47545E',
                    arrowprops=dict(arrowstyle='-',lw=.5,color='#777777'))
    else:
        ax.text(.97,.05,'+  Cohort mean',transform=ax.transAxes,ha='right',fontsize=7,color='#303B44')
fig.savefig(OUT/'retention_heterogeneity.png',dpi=300)
fig.savefig(OUT/'retention_heterogeneity.pdf')
plt.close(fig)

fig, axes = plt.subplots(1,3,figsize=(15/2.54,7.3/2.54), gridspec_kw={'width_ratios':[1,1.3,1]})
fig.subplots_adjust(left=.11,right=.985,bottom=.20,top=.73,wspace=.24)
limits=[(-3.5,.8),(-7.5,1.8),(-.7,1.05)]
ticks=[[-3,-2,-1,0],[-6,-4,-2,0],[-.5,0,.5,1]]
arm_colors=[['#56B4E9','#0072B2','#003F64'],['#D55E00','#E69F00','#7E8791'],['#009E73','#0072B2']]
offsets=[[(-3,8),(8,-6),(-2,-23)],[(2,14),(1,-32),(9,10)],[(3,-29),(4,22)]]
for i,(ax,stage) in enumerate(zip(axes,stages)):
    style(ax);ax.axhline(0,color='#5C6570',linewidth=.7);ax.axvline(0,color='#5C6570',linewidth=.7)
    if i==2:ax.axvline(-.5,color='#B44D34',linestyle='--',linewidth=.8)
    ax.scatter(0,0,marker='D',s=19,facecolor='white',edgecolor='#252F39',linewidth=.8,zorder=5)
    for j,item in enumerate(stage['arms']):
        x,y=item['future_ba'],item['old_harm_ge5pp'];xv,yv=x['mean_pp'],y['mean_pp']
        ax.errorbar(xv,yv,xerr=[[xv-x['interval_pp'][0]],[x['interval_pp'][1]-xv]],
                    yerr=[[yv-y['interval_pp'][0]],[y['interval_pp'][1]-yv]],fmt='o',
                    ms=4,color=arm_colors[i][j],elinewidth=.85,capsize=2,capthick=.7,zorder=4)
        name=item['name'].replace('lambda=',r'$\lambda=$')
        if item['name']=='Personal replay':name='Personal\nreplay'
        dx,dy=offsets[i][j]
        ax.annotate(name,xy=(xv,yv),xytext=(dx,dy),textcoords='offset points',fontsize=7,
                    color=arm_colors[i][j],ha='left' if dx>=0 else 'right',va='center')
    ax.set(xlim=limits[i],ylim=(-27,25),xticks=ticks[i],yticks=[-20,-10,0,10,20])
    if i!=0:ax.set_yticklabels([])
    ax.set_title(f"{'ABC'[i]}  {stage['title']}\n"+['Shared classifier','Recipient-matched heads','Own-feedback heads'][i],loc='left',pad=10,fontsize=8)
    ax.text(.5,1.015,f"Reference harm: {stage['baseline_severe_n']}/62",transform=ax.transAxes,ha='center',fontsize=6.8)
    ax.set_xlabel('Future BA difference (pp)',fontsize=7)
    if i==2:
        ax.text(.04,.98,'Line + full space:\nboth fail dual criterion',transform=ax.transAxes,
                ha='left',va='top',fontsize=6.5,bbox=dict(facecolor='white',edgecolor='none',alpha=.9,pad=2))
axes[0].set_ylabel('Severe-old-harm proportion difference (pp)', fontsize=7)
fig.text(.55,.04,'All panels: 62 participants; each uses its own stage reference',ha='center',fontsize=7)
fig.savefig(OUT/'retention_tradeoffs.png',dpi=300)
fig.savefig(OUT/'retention_tradeoffs.pdf')
plt.close(fig)

def num(v):return f'{v:.10g}'
def coords(rows,x,y):return ' '.join(f'({num(r[x])},{num(r[y])})' for r in rows)
tex_colors='\n'.join(r'\definecolor{ret'+str(i)+r'}{HTML}{'+c[1:]+'}' for i,c in enumerate(COLORS))
tex_colors+='\n'+r'\definecolor{retgreen}{HTML}{009E73}'+ '\n'+r'\definecolor{retred}{HTML}{D55E00}'

caption1=(r'Initial competence and individual heterogeneity in the first frozen Stieger budget experiment. '
          r'(A) Mutually exclusive diagnostic categories; task eligibility is balanced accuracy (BA) at least 0.60, '
          r'and target eligibility is prediction MSE below the actual initial-mean predictor. '
          r'Task/target/joint counts are 29/51/25 of 62 and 19/31/16 of the nested 41. '
          r'(B,C) Each point is one participant, without eligibility-based exclusion. Both compared policies receive '
          r'the same 40 early calibration pairs: the horizontal axis contrasts approximately 25\% with 0\% new labels, '
          r'averaging future sessions within participant; the vertical axis is the final updated classifier minus its '
          r'initialization on the same permanently excluded old test. Pairing schedules do not alter the separate task '
          r'classifier. Colors retain the diagnostic categories; black crosses show participant means; the dashed '
          r'line marks a five-percentage-point (pp) old-test loss. All 19 old-test declines in the 62-person group '
          r'and all 12 in the nested group coexist with a positive future gain. The largest decline is shown without '
          r'axis truncation; its old test has 11 and 1 trials in the two classes. The 41 participants are a subset, '
          r'not an independent replication.')
caption2=(r'Future-performance and permanent-old-harm trade-offs, keeping frozen experimental stages separate. '
          r'All panels use the 62-person cohort and display paired differences from their own stage reference '
          r'(open diamond). Severe harm means an individual old-test BA loss of at least five percentage points. '
          r'(A) Shared-model initial-output penalties at 25\% labels, relative to penalty weight zero. '
          r'(B) Other-source, equal-mixture, and personal-old-replay arms relative to the personal-feedback head '
          r'with global old replay; every receiving head has matched new-label counts. '
          r'(C) Line and full-space training-risk constraints relative to the unconstrained personal update, '
          r'using identical feedback IDs. Horizontal intervals for Other and Mixed are the original 97.5\% '
          r'intervals; all other horizontal and all vertical intervals are 95\%. These are marginal, conditional '
          r'participant-bootstrap intervals, not joint confidence regions. Lower harm and higher future BA are '
          r'preferred. For the constrained arms, the future lower bound must be at least $-0.5$ pp (vertical dashed '
          r'line) and the harm upper bound must be strictly below zero. Both constrained arms pass the future '
          r'tolerance and fail harm reduction; the full-space harm upper bound equals zero. No cross-panel '
          r'difference is an architecture-controlled effect. Training-risk feasibility is separate from the '
          r'permanently excluded old-test outcomes plotted here.')

blocks=['% Fully inline pgfplots; requires tikz, pgfplots already in manuscript preamble.',
        '% Insertion anchor 1: after the paragraph ending "These mean gains do not establish individual retention."',
        r'\begin{figure}[t]',r'\centering',r'\begingroup',tex_colors,r'\begin{tikzpicture}[font=\scriptsize]']
blocks.append(r'\begin{axis}[width=14.7cm,height=3.2cm,at={(0,0)},anchor=north west,xmin=0,xmax=64,ymin=-.55,ymax=1.55,ytick={0,1},yticklabels={Nested 41,All 62},xtick={0,10,20,30,40,50,60},xlabel={Number of participants},axis lines=left,tick label style={font=\scriptsize},label style={font=\scriptsize},title={A\quad Initial eligibility: all participants retained},title style={at={(0,1.2)},anchor=south west},clip=false]')
for pos,p in [(1,panels[0]),(0,panels[1])]:
    start=0
    for j,count in enumerate(p['exclusive_eligibility_counts']):
        blocks.append(r'\path[fill=ret'+str(j)+r',draw=white,line width=.3pt] (axis cs:'+num(start)+','+num(pos-.29)+') rectangle (axis cs:'+num(start+count)+','+num(pos+.29)+');')
        blocks.append(r'\node[font=\scriptsize,text='+('white' if j==0 else 'black')+'] at (axis cs:'+num(start+count/2)+','+str(pos)+'){'+str(count)+'};')
        start+=count
for j,l in enumerate(LABELS):
    blocks.append(r'\node[anchor=west,font=\scriptsize] at (axis description cs:'+num(.03+j*.245)+r',1.07){\textcolor{ret'+str(j)+r'}{\rule{6pt}{6pt}} '+l+'};')
blocks.append(r'\end{axis}')
for j,p in enumerate(panels):
    title=('B\quad All 62' if j==0 else 'C\quad Nested 41')+': sessions 2--'+str(p['final_session'])
    opts=r'width=7.2cm,height=6.25cm,at={('+num(j*7.45)+r'cm,-3.8cm)},anchor=north west,xmin=-8,xmax=8,ymin=-60,ymax=40,xtick={-8,-4,0,4,8},ytick={-60,-40,-20,0,20,40},xlabel={Future BA gain vs 0\% labels (pp)},tick label style={font=\scriptsize},label style={font=\scriptsize},axis lines=left,grid=major,grid style={gray!15},title={'+title+r'},title style={at={(0,1.03)},anchor=south west}'
    if j==0:opts+=r',ylabel={Permanent-old BA change (pp)}'
    blocks.append(r'\begin{axis}['+opts+']')
    blocks.append(r'\path[fill=red!4] (axis cs:-8,-60) rectangle (axis cs:8,-5);')
    blocks.append(r'\addplot[gray,thin,forget plot] coordinates {(-8,0)(8,0)};')
    blocks.append(r'\addplot[gray,thin,forget plot] coordinates {(0,-60)(0,40)};')
    blocks.append(r'\addplot[retred,dashed,thin,forget plot] coordinates {(-8,-5)(8,-5)};')
    for cat in range(4):
        rows=[q for q in p['people'] if q['category']==cat]
        blocks.append(r'\addplot[only marks,mark=*,mark size=1.45pt,color=ret'+str(cat)+r',mark options={draw=white,line width=.2pt}] coordinates {'+coords(rows,'future_gain_pp','old_change_pp')+'};')
    st=p['statistics']
    blocks.append(r'\addplot[only marks,mark=+,mark size=3.7pt,black,very thick] coordinates {('+num(st['future_mean_gain_pp'])+','+num(st['old_mean_change_pp'])+')};')
    blocks.append(r'\node[anchor=north west,align=left,fill=white,inner sep=2pt,font=\scriptsize] at (rel axis cs:.025,.98){Old decline: '+str(st['old_decline_n'])+'/'+str(p['n'])+r'\\Loss $\geq5$ pp: '+str(st['severe_old_harm_n'])+'/'+str(p['n'])+'};')
    if j==0:
        q=next(q for q in p['people'] if q['subject']==5)
        blocks.append(r'\node[anchor=west,align=left,font=\tiny,text=gray!80!black] at (axis cs:-7.7,-43){ID 5: old test has\\11 / 1 trials by class};')
        blocks.append(r'\draw[gray,thin] (axis cs:-3.6,-46) -- (axis cs:'+num(q['future_gain_pp'])+','+num(q['old_change_pp'])+');')
    else:blocks.append(r'\node[anchor=south east,font=\scriptsize] at (rel axis cs:.97,.04){$+$ Cohort mean};')
    blocks.append(r'\end{axis}')
blocks.extend([r'\end{tikzpicture}',r'\endgroup',r'\caption{'+caption1+'}',r'\label{fig:retention-heterogeneity}',r'\end{figure}','',
               '% Insertion anchor 2: after the paragraph ending "None changes the failed future--harm confirmation into a retention guarantee."',
               r'\begin{figure}[t]',r'\centering',r'\begingroup',tex_colors,r'\begin{tikzpicture}[font=\scriptsize]'])
positions=[0,4.85,10.15];widths=[4.75,5.2,4.75]
for i,stage in enumerate(stages):
    opts=(r'width='+num(widths[i])+r'cm,height=6.2cm,at={('+num(positions[i])+r'cm,0)},anchor=north west,'
          r'xmin='+num(limits[i][0])+r',xmax='+num(limits[i][1])+r',ymin=-27,ymax=25,xtick={'+','.join(num(t) for t in ticks[i])+r'},ytick={-20,-10,0,10,20},'
          r'xlabel={Future BA difference (pp)},axis lines=left,grid=major,grid style={gray!15},tick label style={font=\scriptsize},label style={font=\scriptsize},'
          r'title={'+['A\quad Output penalty','B\quad Feedback sources','C\quad Constraints'][i]+r'},title style={at={(0,1.15)},anchor=south west},clip=false')
    if i==0:opts+=r',ylabel={Severe-old-harm difference (pp)}'
    else:opts+=r',yticklabels={,, , ,}'
    blocks.append(r'\begin{axis}['+opts+']')
    blocks.append(r'\node[anchor=south,font=\tiny,align=center] at (rel axis cs:.5,1.02){'+['Stage 2: shared; 25\% labels','Stage 3: recipient-matched','Stage 4: own-feedback IDs'][i]+r'\\Reference harm: '+str(stage['baseline_severe_n'])+'/62};')
    blocks.append(r'\addplot[gray,thin] coordinates {('+num(limits[i][0])+',0)('+num(limits[i][1])+',0)};')
    blocks.append(r'\addplot[gray,thin] coordinates {(0,-27)(0,25)};')
    if i==2:blocks.append(r'\addplot[retred,dashed,thin] coordinates {(-.5,-27)(-.5,25)};')
    blocks.append(r'\addplot[only marks,mark=diamond*,mark size=2pt,mark options={fill=white,draw=black}] coordinates {(0,0)};')
    for j,item in enumerate(stage['arms']):
        x,y=item['future_ba'],item['old_harm_ge5pp'];xv,yv=x['mean_pp'],y['mean_pp']
        color='ret'+str([1,0,0][j]) if i==0 else (['retred','ret2','ret3'][j] if i==1 else ['retgreen','ret0'][j])
        blocks.append(r'\addplot[only marks,mark=*,mark size=2pt,color='+color+r',error bars/.cd,x dir=both,x explicit,y dir=both,y explicit,error bar style={line width=.55pt},error mark options={mark size=2pt,line width=.5pt}] coordinates {('+num(xv)+','+num(yv)+') += ('+num(x['interval_pp'][1]-xv)+','+num(y['interval_pp'][1]-yv)+') -= ('+num(xv-x['interval_pp'][0])+','+num(yv-y['interval_pp'][0])+')};')
        label=item['name'].replace('lambda=',r'$\lambda=' )
        if item['name'].startswith('lambda='):label+='$'
        if label=='Personal replay':label=r'Personal\\replay'
        dx,dy=offsets[i][j]
        blocks.append(r'\node[anchor='+('west' if dx>=0 else 'east')+r',align=left,font=\scriptsize,text='+color+',xshift='+num(dx)+'pt,yshift='+num(dy)+'pt] at (axis cs:'+num(xv)+','+num(yv)+'){'+label+'};')
    if i==2:blocks.append(r'\node[anchor=north west,font=\tiny,align=left,fill=white,inner sep=1pt] at (rel axis cs:.02,.98){Line + full space:\\both fail dual criterion};')
    blocks.append(r'\end{axis}')
blocks.extend([r'\end{tikzpicture}',r'\endgroup',r'\caption{'+caption2+'}',r'\label{fig:retention-tradeoffs}',r'\end{figure}'])
(ROOT/'paper/figure_blocks_retention.tex').write_text('\n'.join(blocks)+'\n')

payload={'records':records,'sources':sources,
         'transformations':{'probability_to_percentage_points':'multiply saved proportion differences and bounds by 100',
                            'future_gain':'per-person mean future session BA of label25__early minus label0__early',
                            'old_change':'final saved permanent-old BA minus initial BA, same rows and policy',
                            'eligibility_categories':'intersection, task-only, target-only, neither; all people kept',
                            'roundoff_tolerance_pp':tol,'new_model_fits':0,'new_bootstrap_resamples':0},
         'figures':{'retention_heterogeneity':{'width_cm':15,'panels':panels,'caption':caption1,
                                             'nested_cohorts_not_independent':True,
                                             'untruncated_scatter_bounds':{'future_gain_pp':[-8,8],'old_change_pp':[-60,40]}},
                    'retention_tradeoffs':{'width_cm':15,'stages':stages,'caption':caption2,
                                          'interpretation':'Each stage has its own reference; no cross-stage architecture effect; marginal conditional intervals are not joint regions.'}},
         'verification':{'status':'PASS_NUMERIC_SOURCE_AND_SUMMARY_CHECKS',
                         'eligibility_partition_exact':True,'task_paths_identical_across_anchor_schedules':True,
                         'old_means_match_original_analysis':True,'severe_harm_count_differences_match_original_contrasts':True,
                         'future_gain_means_match_original_analysis':True,
                         'v4_dual_decisions_match_original':True,
                         'png_visual_review':'pending'},
         'outputs':{}}
for name in ['retention_heterogeneity.pdf','retention_heterogeneity.png','retention_tradeoffs.pdf','retention_tradeoffs.png']:
    p=OUT/name;payload['outputs'][name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
payload['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
payload['inline_tex_sha256']=hashlib.sha256((ROOT/'paper/figure_blocks_retention.tex').read_bytes()).hexdigest()
(OUT/'retention_figure_data.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'numeric_status':payload['verification']['status'],
                  'records':len(records),'distributions':[p['statistics'] for p in panels],
                  'outputs':list(payload['outputs'])},indent=2))
