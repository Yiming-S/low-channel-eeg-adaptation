#!/usr/bin/env python3
"""Source-comparison figure from sealed results; no fitting or resampling.

Writes only the source figure PDF/PNG, its inline TeX block and provenance.
The two frozen stages are shown separately and their saved intervals reused.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'paper/figures'
OUT.mkdir(exist_ok=True)
RECORDS, SOURCES, CACHE = [], {}, {}
ARMS = ['frozen', 'own', 'other', 'mixed']
LABELS = ['Frozen', 'Own', 'Other', 'Mixed']
COLORS = {'frozen': '#565D64', 'own': '#23698D', 'other': '#B35145', 'mixed': '#B48121'}
TOL_PP = 1e-10


def load(source):
    if source not in CACHE:
        path = ROOT / source
        CACHE[source] = json.loads(path.read_text())
        SOURCES[source] = {'bytes': path.stat().st_size,
                           'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    return CACHE[source]


def raw(source, pointer, units):
    obj = load(source)
    for token in pointer.split('/')[1:]:
        token = token.replace('~1', '/').replace('~0', '~')
        obj = obj[int(token)] if isinstance(obj, list) else obj[token]
    RECORDS.append({'source': source, 'json_pointer': pointer, 'value': obj,
                    'units': units, 'sha256': SOURCES[source]['sha256']})
    return obj


def summary_interval(obj, confidence):
    assert obj['confidence'] == confidence
    interval = obj.get('conditional_interval', obj.get('interval'))
    return {'mean_percent_or_pp': 100 * obj['mean'],
            'lower_percent_or_pp': 100 * interval[0],
            'upper_percent_or_pp': 100 * interval[1],
            'confidence': obj['confidence'], 'n': obj['n']}


def direction_counts(values):
    values = np.asarray(values)
    return {'lower': int((values < -TOL_PP).sum()),
            'equal': int((np.abs(values) <= TOL_PP).sum()),
            'higher': int((values > TOL_PP).sum())}


STIEGER = 'experiments/feedback_retention_v3/results/eeg/analysis.json'
FARABBI = 'experiments/confirmation_prior_constraints_v4/results/confirmation/analysis.json'
FARABBI_BUDGET = 'experiments/confirmation_prior_constraints_v4/results/confirmation/budget.json'
FARABBI_QUALITY = 'experiments/confirmation_prior_constraints_v4/results/confirmation/features/preprocessing.json'
panels = []
for name, source, base, window in [
    ('Stieger', STIEGER, '/cohorts/stieger62', 'Sessions 2–7'),
    ('Farabbi', FARABBI, '', 'Day 3')]:
    root = load(source)
    data = root['cohorts']['stieger62'] if name == 'Stieger' else root
    ids = raw(source, base + ('/fixed_groups/all' if name == 'Stieger' else '/subjects'), 'participant IDs')
    n = len(ids)
    people = {subject: {'subject': subject, 'future_ba_percent': {}} for subject in ids}
    absolute = {}
    for arm in ARMS:
        arm_base = base + '/cases/' + arm
        absolute[arm] = summary_interval(raw(source, arm_base + (
            '/groups/all/metrics/future_ba' if name == 'Stieger' else '/future_ba'),
            'balanced accuracy, proportion; original conditional participant interval'), .95)
        assert absolute[arm]['n'] == n
        per_person = data['cases'][arm]['per_person']
        for subject in ids:
            if name == 'Stieger':
                prefix = arm_base + f'/per_person/{subject}'
            else:
                indices = [i for i, obj in enumerate(per_person) if obj['subject'] == subject]
                assert len(indices) == 1
                prefix = arm_base + f'/per_person/{indices[0]}'
                raw(source, prefix + '/subject', 'participant ID')
            people[subject]['future_ba_percent'][arm] = 100 * raw(
                source, prefix + '/future_ba', 'balanced accuracy, proportion')
        assert abs(np.mean([people[s]['future_ba_percent'][arm] for s in ids])
                   - absolute[arm]['mean_percent_or_pp']) < 1e-11
    paired = {}
    for arm in ['other', 'mixed']:
        pointer = base + (f'/paired_contrasts/{arm}_minus_own/all/future_ba'
                          if name == 'Stieger' else f'/comparisons/{arm}_minus_own/future_ba')
        interval = summary_interval(raw(source, pointer,
            'balanced accuracy paired difference, proportion; original 97.5% conditional interval'), .975)
        differences = []
        for subject in ids:
            v = people[subject]['future_ba_percent']
            difference = v[arm] - v['own']
            people[subject][arm + '_minus_own_pp'] = difference
            differences.append(difference)
        assert abs(np.mean(differences) - interval['mean_percent_or_pp']) < 1e-11
        paired[arm] = {'saved_summary': interval, 'direction_counts': direction_counts(differences),
                       'median_pp': float(np.median(differences)),
                       'minimum_pp': float(min(differences)), 'maximum_pp': float(max(differences))}
    if name == 'Stieger':
        budgets = {arm: raw(source, base + f'/cases/{arm}/budget',
                           'labels and recipient/source identities') for arm in ['own', 'other', 'mixed']}
        by_recipient = budgets['own']['by_recipient']
        assert all(budgets[a]['by_recipient'] == by_recipient for a in ['other', 'mixed'])
        assert set(map(int, by_recipient)) == set(ids)
        budget = {'matched_labels_per_recipient': by_recipient,
                  'range': [min(by_recipient.values()), max(by_recipient.values())],
                  'summed_received': sum(by_recipient.values()),
                  'centralized_available': budgets['own']['centralized_available'],
                  'initial_teacher_labels': budgets['own']['initial_teacher_labels']}
        assert raw(source, base + '/final_evaluated_session', 'session index') == 7
    else:
        budget = raw(FARABBI_BUDGET, '/per_recipient', 'released labels per recipient, source and class')
        for subject in ids:
            b = budget[str(subject)]
            assert b['k'] == 10 and all(b['by_source'][a]['n'] == 10 for a in ['own', 'other', 'mixed'])
            assert b['by_source']['mixed']['own'] == b['by_source']['mixed']['other'] == 5
        raw(FARABBI_BUDGET, '/centralized_available', 'available source labels')
        raw(FARABBI_BUDGET, '/unique_used', 'unique source labels by arm')
        raw(FARABBI_BUDGET, '/initial_teacher_labels', 'initial labels')
        counts = raw(source, '/trial_counts', 'trials per participant, partition, class')
        assert all(counts[str(subject)]['day3'] == [20, 20] for subject in ids)
        included = raw(FARABBI_QUALITY, '/included_subjects', 'participant IDs retained by fixed quality rule')
        excluded = raw(FARABBI_QUALITY, '/excluded_subjects_by_fixed_quality_rule', 'excluded participant IDs')
        exclusions = raw(FARABBI_QUALITY, '/exclusions', 'excluded windows and reasons')
        files = raw(FARABBI_QUALITY, '/files', 'file identities and retained/original cue counts')
        assert included == ids and not excluded and not exclusions
        assert sum(obj['retained'] for obj in files) == 1440
        assert all(obj['retained'] == obj['original_cues'] == 40 for obj in files)
    own_change = [people[s]['future_ba_percent']['own'] - people[s]['future_ba_percent']['frozen'] for s in ids]
    panels.append({'name': name, 'n': n, 'window': window, 'subjects': ids,
                   'people': list(people.values()), 'absolute': absolute, 'paired': paired,
                   'budget': budget, 'own_minus_frozen_direction_counts': direction_counts(own_change)})


def jitter(subject, count):
    """ID-determined display displacement, independent of every outcome."""
    return .26 * (((subject * 37) % 101) / 100.0 - .5)


plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 7.5,
                     'axes.titlesize': 8, 'axes.labelsize': 7.5,
                     'xtick.labelsize': 7.2, 'ytick.labelsize': 7.2,
                     'axes.linewidth': .55, 'pdf.fonttype': 42, 'ps.fonttype': 42})
fig, axs = plt.subplots(2, 2, figsize=(15/2.54, 11.8/2.54))
fig.subplots_adjust(left=.095, right=.985, bottom=.12, top=.91, wspace=.23, hspace=.52)
for col, panel in enumerate(panels):
    ax = axs[0, col]
    for person in panel['people']:
        values = [person['future_ba_percent'][a] for a in ARMS]
        ax.plot(range(4), values, color='#9EA6AF', lw=.45, alpha=.50,
                marker='o', ms=1.8, markeredgewidth=0, zorder=1)
    for i, arm in enumerate(ARMS):
        s = panel['absolute'][arm]
        mean, lo, hi = (s[k] for k in ['mean_percent_or_pp', 'lower_percent_or_pp', 'upper_percent_or_pp'])
        ax.errorbar(i, mean, yerr=[[mean-lo], [hi-mean]], color=COLORS[arm],
                    marker='D', ms=4, lw=1.5, capsize=3, capthick=1.1, zorder=4)
        ax.text(i, 77, f'{mean:.2f}', ha='center', va='center', fontsize=7.3, color=COLORS[arm])
    ax.axhline(50, color='#8C9399', lw=.65, ls=(0, (3, 3)), zorder=0)
    ax.set(xlim=(-.3, 3.3), ylim=(30, 80), xticks=range(4), xticklabels=LABELS,
           yticks=[30, 40, 50, 60, 70, 80])
    ax.set_title(f"{'A' if col == 0 else 'B'}  {panel['name']}: {panel['n']} participants", loc='left', weight='bold', pad=18)
    ax.text(0, 1.02, panel['window'] + '; means and 95% intervals', transform=ax.transAxes, fontsize=7.2)
    if col == 0:
        ax.set_ylabel('Future balanced accuracy (%)')
    ax.grid(axis='y', color='#E6E8EB', lw=.45)
    ax.spines[['top', 'right']].set_visible(False)

    ax = axs[1, col]
    for i, arm in enumerate(['other', 'mixed']):
        ys = [person[arm+'_minus_own_pp'] for person in panel['people']]
        xs = [i - .08 + jitter(person['subject'], panel['n']) for person in panel['people']]
        ax.scatter(xs, ys, s=12, color=COLORS[arm], alpha=.68, linewidths=.25,
                   edgecolors='white', zorder=3)
        s = panel['paired'][arm]['saved_summary']
        mean, lo, hi = (s[k] for k in ['mean_percent_or_pp', 'lower_percent_or_pp', 'upper_percent_or_pp'])
        ax.errorbar(i+.23, mean, yerr=[[mean-lo], [hi-mean]], marker='D', ms=4,
                    color='#202832', capsize=3.4, lw=1.5, capthick=1.1, zorder=5)
        ax.text(i, 11.1, f'{mean:+.2f} pp', ha='center', fontsize=7.4, va='center')
    categories = []
    for arm in ['other', 'mixed']:
        c = panel['paired'][arm]['direction_counts']
        categories.append(f"{arm.capitalize()} − Own\n{c['lower']} / {c['equal']} / {c['higher']}")
    ax.set(xlim=(-.45, 1.5), ylim=(-12, 12), xticks=[0, 1], xticklabels=categories,
           yticks=[-10, -5, 0, 5, 10])
    ax.set_xlabel('Participants: lower / equal / higher', labelpad=5)
    if col == 0:
        ax.set_ylabel('Paired difference in future BA (pp)')
    ax.set_title(f"{'C' if col == 0 else 'D'}  {panel['name']}: individual differences", loc='left', weight='bold', pad=18)
    ax.text(0, 1.02, 'Individuals and paired mean (97.5% interval)', transform=ax.transAxes, fontsize=7.05)
    ax.axhline(0, color='#6D747C', lw=.75, ls=(0, (3, 3)))
    ax.grid(axis='y', color='#E6E8EB', lw=.45)
    ax.spines[['top', 'right']].set_visible(False)
fig.savefig(OUT / 'feedback_source.pdf')
fig.savefig(OUT / 'feedback_source.png', dpi=300)
plt.close(fig)


def number(value):
    return format(float(value), '.12g')


def coords(x, y):
    return ' '.join(f'({number(a)},{number(b)})' for a, b in zip(x, y))


def tex_error(x, summary, color):
    m, lo, hi = (summary[k] for k in ['mean_percent_or_pp', 'lower_percent_or_pp', 'upper_percent_or_pp'])
    return (r'\addplot+[only marks,mark=diamond*,mark size=2pt,color=' + color
            + r',line width=1pt,error bars/.cd,y dir=both,y explicit,error bar style={line width=1pt},error mark options={rotate=90,mark size=2.5pt}] coordinates {'
            + f'({number(x)},{number(m)}) += (0,{number(hi-m)}) -= (0,{number(m-lo)})' + '};')


tex = [r'% Insert in place of the current figure labeled fig:source.',
       r'% Generated entirely from the original saved participant outcomes and intervals.',
       r'\begin{figure}[tbp]', r'\centering', r'\begingroup',
       r'\definecolor{sourceGray}{HTML}{565D64}',
       r'\definecolor{sourceOwn}{HTML}{23698D}',
       r'\definecolor{sourceOther}{HTML}{B35145}',
       r'\definecolor{sourceMixed}{HTML}{B48121}',
       r'\definecolor{sourcePerson}{HTML}{9EA6AF}',
       r'\begin{tikzpicture}',
       r'\pgfplotsset{sourceaxis/.style={scale only axis,width=6.0cm,height=3.7cm,',
       r'axis lines=left,axis line style={line width=.45pt},tick style={line width=.4pt},',
       r'font=\fontsize{7.5}{8.5}\selectfont,tick label style={font=\fontsize{7}{8}\selectfont},',
       r'label style={font=\fontsize{7.5}{8.5}\selectfont},',
       r'ymajorgrids=true,grid style={gray!18,line width=.3pt},',
       r'title style={align=left,at={(0,1.035)},anchor=south west,font=\fontsize{8}{9}\selectfont},',
       r'clip=false}}']
tex_colors = {'frozen': 'sourceGray', 'own': 'sourceOwn', 'other': 'sourceOther', 'mixed': 'sourceMixed'}
for col, panel in enumerate(panels):
    xpos = '0cm' if col == 0 else '7.25cm'
    letter = 'A' if col == 0 else 'B'
    window = 'Sessions 2--7' if col == 0 else 'Day 3'
    title = (r'\textbf{' + f'{letter}  {panel["name"]}: {panel["n"]} participants' + r'}\\'
             + r'{\fontsize{7}{8}\selectfont ' + window + r'; means and 95\% intervals}')
    opts = [f'at={{({xpos},0cm)}}', 'anchor=south west', 'xmin=-.3,xmax=3.3,ymin=30,ymax=80',
            'xtick={0,1,2,3},xticklabels={Frozen,Own,Other,Mixed}', 'ytick={30,40,50,60,70,80}',
            f'title={{{title}}}']
    if col == 0:
        opts.append(r'ylabel={Future balanced accuracy (\%)}')
    tex.append(r'\begin{axis}[sourceaxis,' + ','.join(opts) + ']')
    tex.append(r'\addplot[gray!65,dashed,line width=.5pt,forget plot] coordinates {(-.3,50) (3.3,50)};')
    for person in panel['people']:
        tex.append(r'\addplot[sourcePerson,opacity=.5,line width=.32pt,mark=*,mark size=.7pt,forget plot] coordinates {'
                   + coords(range(4), [person['future_ba_percent'][a] for a in ARMS]) + '};')
    for i, arm in enumerate(ARMS):
        tex.append(tex_error(i, panel['absolute'][arm], tex_colors[arm]))
        tex.append(r'\node[font=\fontsize{7.2}{8}\selectfont,text=' + tex_colors[arm]
                   + f'] at (axis cs:{i},77) {{{panel["absolute"][arm]["mean_percent_or_pp"]:.2f}}};')
    tex.append(r'\end{axis}')

    letter = 'C' if col == 0 else 'D'
    title = (r'\textbf{' + f'{letter}  {panel["name"]}: individual differences' + r'}\\'
             + r'{\fontsize{7}{8}\selectfont Individuals and paired mean (97.5\% interval)}')
    labels = []
    for arm in ['other', 'mixed']:
        c = panel['paired'][arm]['direction_counts']
        labels.append('{' + arm.capitalize() + r' $-$ Own\\'
                      + f'{c["lower"]} / {c["equal"]} / {c["higher"]}' + '}')
    opts = [f'at={{({xpos},-5.55cm)}}', 'anchor=south west', 'xmin=-.45,xmax=1.5,ymin=-12,ymax=12',
            'xtick={0,1}', 'xticklabels={' + ','.join(labels) + '}',
            r'xticklabel style={align=center,font=\fontsize{7}{8}\selectfont}',
            'ytick={-10,-5,0,5,10}', 'xlabel={Participants: lower / equal / higher}',
            f'title={{{title}}}']
    if col == 0:
        opts.append('ylabel={Paired difference in future BA (pp)}')
    tex.append(r'\begin{axis}[sourceaxis,' + ','.join(opts) + ']')
    tex.append(r'\addplot[gray!70,dashed,line width=.55pt,forget plot] coordinates {(-.45,0) (1.5,0)};')
    for i, arm in enumerate(['other', 'mixed']):
        xs = [i - .08 + jitter(p['subject'], panel['n']) for p in panel['people']]
        ys = [p[arm + '_minus_own_pp'] for p in panel['people']]
        tex.append(r'\addplot[only marks,mark=*,mark size=1.35pt,draw=white,line width=.2pt,fill='
                   + tex_colors[arm] + r',fill opacity=.72,forget plot] coordinates {' + coords(xs, ys) + '};')
        tex.append(tex_error(i+.23, panel['paired'][arm]['saved_summary'], 'black!85'))
        tex.append(r'\node[font=\fontsize{7.4}{8}\selectfont] at (axis cs:' + str(i) + ',11.1) {'
                   + f'{panel["paired"][arm]["saved_summary"]["mean_percent_or_pp"]:+.2f}' + r' pp};')
    tex.append(r'\end{axis}')
tex.extend([r'\end{tikzpicture}', r'\endgroup',
    r'\caption{Feedback source and absolute future performance under the two frozen source-comparison protocols. '
    r'(A,B) Each gray line links one participant across four arms; colored diamonds and numbers give cohort means with the original 95\% conditional participant-bootstrap intervals. '
    r'Stieger uses each participant\textquotesingle s mean over sessions 2--7; Farabbi uses day 3. '
    r'(C,D) Every participant\textquotesingle s other-minus-own and mixed-minus-own difference is shown, with the original paired means and 97.5\% intervals in black. '
    r'Counts under each comparison give participants with lower, equal, or higher BA; horizontal displacement only separates points. '
    r'Within each stage, the three feedback arms match the number of labels received by each personal readout: 46--210 accumulated labels in Stieger and 10 labels in Farabbi (mixed: 5 own and 5 other). '
    r'All 62 and all 12 participants are included; they are separate datasets, not pooled comparisons. '
    r'Farabbi day-3 BA has 2.5-point resolution from 40 balanced trials per person. '
    r'The Farabbi source contrasts retain intervals spanning zero; participant-level counts do not establish a reversed population effect. '
    r'BA: balanced accuracy; pp: percentage points.}', r'\label{fig:source}', r'\end{figure}'])
# Avoid a package-specific apostrophe macro in a self-contained inline block.
tex_text = '\n'.join(tex).replace(r'participant\textquotesingle s', "participant's") + '\n'
(ROOT / 'paper/figure_blocks_source.tex').write_text(tex_text)

assert tex_text.count(r'\begin{figure}') == tex_text.count(r'\end{figure}') == 1
assert not any(token in tex_text for token in [r'\input', r'\includegraphics', 'table['])
assert len(panels[0]['people']) == 62 and len(panels[1]['people']) == 12
for panel in panels:
    assert all(30 <= p['future_ba_percent'][a] <= 80 for p in panel['people'] for a in ARMS)
    assert all(-12 <= p[a+'_minus_own_pp'] <= 12 for p in panel['people'] for a in ['other', 'mixed'])
data = {'figure': 'fig:source', 'records': RECORDS, 'sources': SOURCES,
        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'transformations': {
            'absolute': '100 times saved participant future BA; cohort intervals reused without resampling',
            'paired': '100 times (same participant alternative future BA - own future BA); saved 97.5% intervals reused',
            'display_displacement': '0.26 * (((participant_ID * 37) mod 101)/100 - 0.5), outcome-independent; no inference',
            'zero_tolerance_pp': TOL_PP,
            'no_new_inference': 'No fitting, bootstrap, significance, pooled, or heterogeneity test is performed',
            'absolute_axes_percent': [30, 80], 'difference_axes_pp': [-12, 12],
            'nested_stieger41': 'Omitted to avoid repeating a nested subset',
            'budget_scope': 'Matching is per recipient; distinct source identities and centralized acquisition are not equated'},
        'panels': panels,
        'validation': {'all_record_pointers_resolved': True, 'means_match_saved': True,
                       'fresh_source_record_roundtrip_checks': len(RECORDS),
                       'all_individuals_visible_in_limits': True, 'original_interval_levels_preserved': True,
                       'new_statistical_tests': 0, 'new_bootstrap_draws': 0,
                       'visual_png_review': 'pending', 'inline_tex_no_external_dependency': True},
        'outputs': {str(path.relative_to(ROOT)): {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'bytes': path.stat().st_size} for path in [OUT/'feedback_source.pdf', OUT/'feedback_source.png', ROOT/'paper/figure_blocks_source.tex']}}
data_path = OUT / 'source_figure_data.json'
if data_path.exists():
    previous = json.loads(data_path.read_text())
    visual_keys = ['paper/figures/feedback_source.png', 'paper/figure_blocks_source.tex']
    if (previous.get('validation', {}).get('visual_png_review') == 'PASS'
            and all(previous.get('outputs', {}).get(k, {}).get('sha256')
                    == data['outputs'][k]['sha256'] for k in visual_keys)):
        data['validation']['visual_png_review'] = 'PASS'
        data['validation']['visual_review_notes'] = previous['validation'].get('visual_review_notes', [])
data_path.write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps({'records': len(RECORDS), 'sources': len(SOURCES), 'participants': [p['n'] for p in panels],
                  'paired_direction_counts': {p['name']: {a: p['paired'][a]['direction_counts'] for a in ['other', 'mixed']} for p in panels}}, indent=2))
