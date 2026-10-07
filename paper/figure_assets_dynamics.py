#!/usr/bin/env python3
"""Export four source-bound dynamics/reliability figures; no fitting or simulation.
All pgfplots data are embedded in the generated TeX, with no external inputs.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'paper/figures'
OUT.mkdir(exist_ok=True)
SOURCES = {
 'history': 'experiments/continual_information_v1/dynamics/results/SUMMARY.json',
 'schedules': 'experiments/reliability_followup_v2/analysis/dynamics/analysis.json',
 'information': 'experiments/closure_controls_v6/analysis/dynamics/analysis.json',
 'prior': 'experiments/prior_reliability_v7/analysis/dynamics/analysis.json',
 'reliability': 'experiments/prior_reliability_v7/analysis/reliability/analysis.json',
}
DOCS = {k: json.loads((ROOT/v).read_text()) for k,v in SOURCES.items()}
HASHES = {k: hashlib.sha256((ROOT/v).read_bytes()).hexdigest() for k,v in SOURCES.items()}
RECORDS, SEEN = [], set()
META = {'schema_version': 1, 'source_base': 'repository root', 'records': RECORDS,
        'figures': [], 'verification_scope': 'All plotted numbers read from formal analyses; no new fits, simulations or intervals.'}
BLUE, ORANGE, GREEN, PURPLE, GRAY = '#0072B2', '#D55E00', '#009E73', '#8E63AC', '#6D747B'
plt.rcParams.update({'font.size':8, 'axes.titlesize':8.5, 'axes.labelsize':8,
 'xtick.labelsize':7.5, 'ytick.labelsize':7.5, 'legend.fontsize':7.5,
 'font.family':'DejaVu Sans', 'axes.spines.top':False, 'axes.spines.right':False,
 'axes.linewidth':.65, 'lines.linewidth':1.15, 'pdf.fonttype':42, 'savefig.dpi':220})
TEX=[]

def read(key,pointer,units):
    d=DOCS[key]
    for token in pointer.strip('/').split('/'):
        token=token.replace('~1','/').replace('~0','~')
        d=d[int(token)] if isinstance(d,list) else d[token]
    identity=(key,pointer)
    if identity not in SEEN:
        RECORDS.append({'source':SOURCES[key], 'json_pointer':pointer,
                        'value':d, 'units':units, 'sha256':HASHES[key]})
        SEEN.add(identity)
    return d

def stat(key,prefix,ci='mc95',scale=1.,units='state-coordinate squared units'):
    y=read(key,prefix+'/mean',units)
    lim=read(key,prefix+'/'+ci,units)
    return np.array([y,lim[0],lim[1]],float)*scale

def error(ax,x,triples,color,marker='o',ls='-',label=None):
    z=np.array(triples)
    ax.errorbar(x,z[:,0],yerr=[z[:,0]-z[:,1],z[:,2]-z[:,0]],color=color,
                marker=marker,linestyle=ls,markersize=3.2,capsize=2,elinewidth=.8,label=label)

def style(ax,title,ylabel=None,log=False):
    ax.set_title(title,loc='left',pad=7)
    if ylabel:ax.set_ylabel(ylabel)
    ax.grid(axis='y',color='#DDE2E6',linewidth=.5,zorder=0)
    ax.set_axisbelow(True)
    if log:ax.set_yscale('log')

def save(fig,name,caption,anchor,transformations):
    fig.savefig(OUT/(name+'.png'))
    fig.savefig(OUT/(name+'.pdf'))
    plt.close(fig)
    META['figures'].append({'name':name, 'png':'paper/figures/'+name+'.png',
      'pdf':'paper/figures/'+name+'.pdf','width_cm':15,'caption':caption,
      'insertion_anchor':anchor,'plot_transformations':transformations})

def tc(c):return '{rgb,255:red,%d;green,%d;blue,%d}'%tuple(int(c[i:i+2],16) for i in (1,3,5))
def axis(x,y,w,h,title,extra=''):
    return (r'\begin{axis}[at={(%scm,%scm)},anchor=outer south west,width=%scm,height=%scm,'%(x,y,w,h)
      +r'font=\fontsize{8}{9.5}\selectfont,tick label style={font=\fontsize{7.5}{9}\selectfont},'
      +r'title style={align=left,font=\fontsize{8.5}{10}\selectfont},title={'+title+r'},'
      +r'axis x line=bottom,axis y line=left,ymajorgrids=true,grid style={gray!20},'
      +r'legend style={font=\fontsize{7}{8}\selectfont,draw=none,fill=none},'+extra+']\n')

def tplot(x,z,c,mark='*',ls='solid',label=None):
    coords=' '.join('(%0.12g,%0.12g) += (0,%0.12g) -= (0,%0.12g)'%(a,v[0],v[2]-v[0],v[0]-v[1]) for a,v in zip(x,z))
    s=r'\addplot+[color='+tc(c)+',mark='+mark+',mark size=1.5pt,line width=.65pt,'+ls+r',error bars/.cd,y dir=both,y explicit,error bar style={line width=.45pt}] coordinates {'+coords+'};\n'
    if label:s+=r'\addlegendentry{'+label+'}\n'
    return s

def tline(y,c,ls='dashed',label=None,x0=-.2,x1=2.2):
    s=r'\addplot[color='+tc(c)+','+ls+r',no marks,forget plot,line width=.7pt] coordinates {('+str(x0)+','+str(y)+') ('+str(x1)+','+str(y)+')};\n'
    if label:s+=r'\addlegendentry{'+label+'}\n'
    return s

def block(name,caption,anchor,body):
    TEX.append('% INSERTION: '+anchor+'\n'+r'\begin{figure}[p]'+'\n'+r'\centering'+'\n'+r'\begin{tikzpicture}'+'\n'+body+r'\end{tikzpicture}'+'\n'+r'\caption{'+caption+'}\n'+r'\label{fig:'+name.replace('dynamics_','dynamics-').replace('_','-')+'}\n'+r'\end{figure}'+'\n')

# Figure 1: information-history contrast and all 21 schedule conditions.
regimes=['unobservable','weak','observable']
mechs=['none','A_abrupt','A_gradual','C_abrupt','C_gradual','both_abrupt','both_gradual']
mticks=['None','A step','A slow','C step','C slow','Both step','Both slow']
policies=[('periodic','Periodic',BLUE),('hybrid','Hybrid',ORANGE),('exactbudget_trigger','Trigger',PURPLE)]
history=[]
for regime in regimes:
    i=next(i for i,r in enumerate(DOCS['history']['contrasts']) if r.get('family')=='known' and r.get('scenario')==regime and r.get('gap')==12 and r.get('metric')=='hidden_mse' and r.get('contrast')=='current_low_minus_low_history_high')
    history.append([read('history',f'/contrasts/{i}/'+k,'hidden-coordinate squared units')*1000 for k in ['mean','ci_low','ci_high']])
schedule={}
for regime in regimes:
    schedule[regime]={}
    for pol,label,col in policies:
        schedule[regime][pol]=[stat('schedules',f'/rows/{regime}__{m}/joint3x3__{pol}/trajectory_pre_full_mse') for m in mechs]
        for m in mechs:
            assert read('schedules',f'/rows/{regime}__{m}/joint3x3__{pol}/budget_min','high-state vectors')==12
            assert read('schedules',f'/rows/{regime}__{m}/joint3x3__{pol}/budget_max','high-state vectors')==12
fig,axs=plt.subplots(2,2,figsize=(15/2.54,12.0/2.54))
fig.subplots_adjust(left=.12,right=.985,bottom=.15,top=.935,wspace=.35,hspace=.67)
ax=axs.flat[0];error(ax,np.arange(3),history,BLUE,ls='none');ax.axhline(0,color=GRAY,lw=.7)
ax.set_xticks(range(3),['Unobs.','Weak','Observable']);style(ax,'(a) Known-model history gain','Hidden-MSE reduction\n($\\times 10^{-3}$)');ax.set_ylim(-.25,5.1)
ax.text(.5,.84,'20 high vectors; 512 paths',transform=ax.transAxes,ha='center',fontsize=7.5)
body=axis(0,6.25,7.1,5.15,'(a) Known-model history gain',r'xmin=-.3,xmax=2.3,ymin=-.25,ymax=5.1,xtick={0,1,2},xticklabels={Unobs.,Weak,Observable},ylabel={Hidden-MSE reduction ($\times10^{-3}$)}')
body+=tline(0,GRAY,'solid',x0=-.3,x1=2.3)+tplot(range(3),history,BLUE,ls='only marks')
body+=r'\node[font=\fontsize{7.5}{9}\selectfont] at (rel axis cs:.5,.87) {20 high vectors; 512 paths};'+'\n'+r'\end{axis}'+'\n'
for j,regime in enumerate(regimes):
    ax=axs.flat[j+1]
    for pol,label,col in policies:error(ax,np.arange(7),schedule[regime][pol],col,label=label)
    title=f'({chr(98+j)}) {regime.capitalize()}: 12 high vectors'
    style(ax,title,'Full-state MSE',True);ax.set_ylim(.055,5)
    ax.set_xticks(range(7),mticks,rotation=40,ha='right')
    if j==0:ax.legend(frameon=False,loc='upper left',ncol=1,handlelength=1.5)
    px,py=[(7.55,6.25),(0,0),(7.55,0)][j]
    body+=axis(px,py,7.1,5.15,title, r'ymode=log,ymin=.055,ymax=5,xmin=-.3,xmax=6.3,xtick={0,1,2,3,4,5,6},xticklabels={None,A step,A slow,C step,C slow,Both step,Both slow},x tick label style={rotate=40,anchor=east},ylabel={Full-state MSE},legend pos=north west')
    for pol,label,col in policies:body+=tplot(range(7),schedule[regime][pol],col,label=label if j==0 else None)
    body+=r'\end{axis}'+'\n'
caption=r'History and acquisition schedules answer different questions. (a) Hidden-coordinate MSE with only the current low observation minus MSE with the complete low history, conditional on the same high history, in the known-model experiment (512 trajectories; high observations every 12 steps, giving 20 follow-up vectors). (b--d) All 21 changing-system conditions with the joint $3\times3$ candidate filter from the schedule comparison, with 512 trajectories per condition and exactly 12 follow-up high vectors for each policy. Periodic releases occur at 10,30,...,230; the hybrid uses six fixed releases plus six causal or budget-forced releases; the trigger also uses forced releases to exhaust its budget. Step and slow denote abrupt and gradual changes. Bars are the stored descriptive 95\% trajectory intervals; the history interval is paired. State estimates precede the current high release. Dense initialization is separate from these follow-up budgets; panels (b--d) use logarithmic MSE axes.'
name='dynamics_history_schedules';anchor='Appendix: Simulation configuration and numerical stopping rules, after the grid/history design paragraph.'
save(fig,name,caption,anchor,{'history_axis_scale':1000,'schedule_axis':'logarithmic; no transformation of saved MSE','coverage':'3 history contrasts plus all21 schedule conditions, 3 policies each'})
block(name,caption,anchor,body)

# Figure 2: same 32 paths, finite c information, with explicitly privileged references.
cells=['observable__matched_prior__none','observable__matched_prior__periodic','observable__both_abrupt__none','observable__both_abrupt__periodic']
titles=['Matched prior, no high vectors','Matched prior, 12 high vectors','Abrupt change, no high vectors','Abrupt change, 12 high vectors']
counts=[1024,2048,4096]
info_modes=[('unknown','No c measurements',GRAY,'o'),('anchor_exact_C','12 exact c',BLUE,'s'),('anchor_noisy_C','12 noisy c',ORANGE,'^')]
fig,axs=plt.subplots(2,2,figsize=(15/2.54,11.4/2.54));fig.subplots_adjust(left=.12,right=.985,bottom=.205,top=.94,wspace=.34,hspace=.47)
body=''
for j,cell in enumerate(cells):
    ax=axs.flat[j];px,py=(j%2*7.55,5.75 if j<2 else .5)
    body+=axis(px,py,7.1,4.7,f'({chr(97+j)}) '+titles[j],r'ymode=log,ymin=.05,ymax=.8,xmin=-.2,xmax=2.2,xtick={0,1,2},xticklabels={1024,2048,4096},xlabel={Particle count},ylabel={Full-state MSE}')
    for mode,label,col,marker in info_modes:
        z=[stat('information',f'/cells/{cell}/modes/{mode}/rows/{n}/trajectory_full_mse') for n in counts]
        error(ax,range(3),z,col,marker=marker,label=label)
        body+=tplot(range(3),z,col,mark={'o':'*','s':'square*','^':'triangle*'}[marker])
    known=read('information',f'/cells/{cell}/current_known_C_1024_reference/trajectory_full_mse/mean','state-coordinate squared units')
    oracle=read('information',f'/cells/{cell}/reference_rows/oracle/trajectory_full_mse/mean','state-coordinate squared units')
    assert read('information',f'/cells/{cell}/current_known_C_1024_reference/trajectory_full_mse/n','trajectories')==32
    ax.axhline(known,color=PURPLE,ls='--',lw=1.2,label='Current c (1024)')
    ax.axhline(oracle,color='black',ls=':',lw=1.2,label='True-parameter filter')
    body+=tline(known,PURPLE)+tline(oracle,'#000000','dotted')+r'\end{axis}'+'\n'
    style(ax,f'({chr(97+j)}) '+titles[j],'Full-state MSE',True);ax.set_ylim(.05,.8)
    ax.set_xticks(range(3),[str(n) for n in counts]);ax.set_xlabel('Particle count')
handles,labels=axs.flat[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.52,.015),ncol=3,frameon=False,columnspacing=1.1,handlelength=2)
# Inline legend as text/color swatches; it is embedded, not an external legend file.
for k,(text,col,ls) in enumerate([('No c measurements',GRAY,'solid'),('12 exact c',BLUE,'solid'),('12 noisy c',ORANGE,'solid'),('Current c (1024)',PURPLE,'dashed'),('True-parameter filter','#000000','dotted')]):
    row=k//3;cl=k%3;x=.6+cl*4.8;y=-.12-row*.42
    body+=r'\draw[color='+tc(col)+','+ls+'] ('+str(x)+','+str(y)+') -- ('+str(x+.42)+','+str(y)+');\n'
    body+=r'\node[anchor=west,font=\fontsize{7.5}{9}\selectfont] at ('+str(x+.49)+','+str(y)+') {'+text+'};\n'
caption=r'Finite parameter information on the same 32 saved observable trajectories per generating mechanism, averaging four algorithm seeds within each trajectory. Points and bars show the stored mean MSE and descriptive 95\% trajectory intervals at 1,024, 2,048, and 4,096 particles. All three particle curves infer both $a$ and $c$. Exact and noisy arms receive 12 scalar measurements of $c$ at 10,30,...,230 after the current main estimate; noisy measurements have independent Gaussian standard deviation 0.1. Their scalar budget is additional to the high-state-vector budget in the panel title. The dashed reference receives the current exact $c$ before prediction at all 240 steps and uses 1,024 particles; it is not a same-information or same-computation comparator at every plotted count. The dotted true-parameter filter receives both current parameters. Both references use the identical 32 paths; lines show their means. Logarithmic axes are shared. These reused paths are not new confirmations.'
name='dynamics_parameter_information';anchor='Main text: Parameter information helps while finite inference remains sensitive, after the finite-measurement results paragraph.'
save(fig,name,caption,anchor,{'y_axis':'logarithmic','n':32,'seed_aggregation':'4 seeds averaged within path','reference_scope':'current-known c at1024 and oracle, both identical32paths','intervals':'stored normal95 trajectory mean intervals'})
block(name,caption,anchor,body)

# Figure 3: same-path fitted prior contrasts at both counts and numerical criteria.
priors=['diffusion_half','diffusion_double','reset_half','reset_double'];pticks=[r'$\sigma/2$',r'$2\sigma$',r'$q/2$',r'$2q$']
fig=plt.figure(figsize=(15/2.54,15.1/2.54));gs=fig.add_gridspec(3,2,height_ratios=[1,1,.85],left=.12,right=.985,bottom=.10,top=.96,wspace=.36,hspace=.70)
body='';passes=np.zeros(4,dtype=int);joint=0
for j,cell in enumerate(cells):
    ax=fig.add_subplot(gs[j//2,j%2]);px,py=j%2*7.55,10.3 if j<2 else 5.3
    zs={n:[stat('prior',f'/cells/{cell}/prior_contrasts/{p}_minus_baseline/{n}/trajectory_full_mse') for p in priors] for n in [2048,4096]}
    vals=np.concatenate([np.array(zs[n])[:,1:].ravel() for n in zs]);lo=min(-.008,float(vals.min())*1.14);hi=max(.008,float(vals.max())*1.14)
    for n,col,mark,ls,dx in [(2048,GRAY,'^','--',-.065),(4096,BLUE,'o','-',.065)]:error(ax,np.arange(4)+dx,zs[n],col,marker=mark,ls=ls,label=str(n)+' particles')
    ax.axhline(0,color='black',lw=.65);style(ax,f'({chr(97+j)}) '+titles[j],'MSE difference\n(altered prior − baseline)');ax.set_ylim(lo,hi);ax.set_xticks(range(4),pticks)
    if j==0:ax.legend(frameon=False,fontsize=7)
    body+=axis(px,py,7.1,4.25,f'({chr(97+j)}) '+titles[j],'xmin=-.3,xmax=3.3,ymin='+str(lo)+',ymax='+str(hi)+r',xtick={0,1,2,3},xticklabels={$\sigma/2$,$2\sigma$,$q/2$,$2q$},ylabel={MSE difference},legend pos=north west,scaled y ticks=false,y tick label style={/pgf/number format/fixed,/pgf/number format/precision=3}')
    body+=tline(0,'#000000','solid',x0=-.3,x1=3.3)
    for n,col,mark,ls,dx in [(2048,GRAY,'triangle*','dashed',-.065),(4096,BLUE,'*','solid',.065)]:body+=tplot(np.arange(4)+dx,zs[n],col,mark=mark,ls=ls,label=str(n)+' particles' if j==0 else None)
    body+=r'\end{axis}'+'\n'
    for prior,pobj in DOCS['prior']['cells'][cell]['priors'].items():
        ps=[]
        for k,(criterion,v) in enumerate(pobj['operational_numerical_criteria'].items()):
            prefix=f'/cells/{cell}/priors/{prior}/operational_numerical_criteria/{criterion}'
            read('prior',prefix+'/value','criterion-specific units; see panel metadata')
            read('prior',prefix+'/tolerance','criterion-specific units; see panel metadata')
            b=read('prior',prefix+'/passed','boolean');passes[k]+=b;ps.append(b)
        joint+=all(ps)
barvalues=list(map(int,passes))+[joint];assert barvalues==[5,4,0,7,0]
ax=fig.add_subplot(gs[2,:]);x=np.arange(5)
barticks=['Mean MSE\n≤0.01','State estimate\n≤0.01','Parameter estimate\n≤10⁻⁴','Seed variation\n≤0.01','All four\ncriteria']
ax.bar(x,barvalues,color=[BLUE]*4+[ORANGE],width=.57,zorder=3)
for i,v in enumerate(barvalues):ax.text(i,v+.45,f'{v}/20',ha='center',fontsize=8)
ax.set_xticks(x,barticks);ax.set_ylim(0,20);ax.set_yticks([0,5,10,15,20]);style(ax,'(e) Predefined numerical criteria across all 20 prior–condition cells','Cells passing')
body+=axis(0,0,14.65,4.0,'(e) Predefined numerical criteria: all 20 prior--condition cells',r'ybar,bar width=16pt,ymin=0,ymax=20,ytick={0,5,10,15,20},xmin=-.6,xmax=4.6,xtick={0,1,2,3,4},xticklabels={{Mean MSE\\$\leq.01$},{State estimate\\$\leq.01$},{Parameter estimate\\$\leq10^{-4}$},{Seed variation\\$\leq.01$},{All four\\criteria}},x tick label style={align=center},ylabel={Cells passing}')
body+=r'\addplot[fill='+tc(BLUE)+',draw=none] coordinates {'+' '.join(f'({i},{v})' for i,v in enumerate(barvalues[:4]))+'};\n'
for i,v in enumerate(barvalues):body+=r'\node[anchor=south,font=\fontsize{8}{9}\selectfont] at (axis cs:'+str(i)+','+str(v+.4)+') {'+str(v)+'/20};\n'
body+=r'\end{axis}'+'\n'
caption=r'Same-path prior sensitivity and the predefined numerical stopping rule. (a--d) Altered-prior minus baseline full-state MSE, with stored paired 95\% trajectory intervals, at 2,048 and 4,096 particles. Each cell uses the same 32 true paths and four algorithm seeds averaged within path. The baseline has reflected-diffusion standard deviation $\sigma=0.05$ and joint-reset probability $q=0.01$; one parameter is halved or doubled. Only the matched-prior mechanism has a baseline generating law that matches this prior. (e) Counts passing the four fixed criteria across five priors and four mechanism--observation cells. Mean-MSE change, state-estimate squared change, and four-seed state variance are divided by true-parameter-reference MSE, with threshold 0.01. The parameter criterion takes the larger of the two coordinate mean squared changes, with threshold $10^{-4}$. The first three compare 2,048 with 4,096; seed variance uses 4,096. No cell passes all four. Counts are descriptive numerical checks, not statistical rejection rates; particle count stops at 4,096.'
name='dynamics_prior_stability';anchor='Appendix: Simulation configuration and numerical stopping rules, after the final fitted-prior comparison table.'
save(fig,name,caption,anchor,{'primary_count':4096,'sensitivity_count':2048,'contrasts':'paired altered prior minus baseline','criterion_pass_counts':barvalues,'criterion_units':['ratio to oracle MSE','ratio to oracle MSE','parameter-coordinate squared units','ratio to oracle MSE','joint boolean'],'thresholds':[.01,.01,.0001,.01],'all_20_cells_included':True})
block(name,caption,anchor,body)

# Figure 4: four reliability arms and the two distinct controlled contrasts.
grouprows=[ [('all62','All 62',BLUE),('nested_all41','Nested 41',ORANGE)], [('original_task_eligible29','Qualified 29',BLUE),('original_task_eligible19','Qualified 19',ORANGE)] ]
arms=['I0','I1','M0','M1']
fig=plt.figure(figsize=(15/2.54,10.4/2.54));gs=fig.add_gridspec(2,3,width_ratios=[1.25,1,1],left=.105,right=.985,bottom=.13,top=.945,wspace=.54,hspace=.58)
body=''
for row,groups in enumerate(grouprows):
    ax=fig.add_subplot(gs[row,0]);title=f'({chr(97+row*3)}) '+('All participants' if row==0 else 'Qualified groups')
    body+=axis(0,5.0 if row==0 else 0,5.2,4.5,title,r'xmin=-.2,xmax=3.2,ymin=45,ymax=95,ytick={50,60,70,80,90},xtick={0,1,2,3},xticklabels={I0,I1,M0,M1},ylabel={Failure probability (\%)},legend pos=south west')
    for gi,(group,label,col) in enumerate(groups):
        z=[stat('reliability',f'/groups/{group}/arms/{a}/confirmed_failure',ci='conditional95',scale=100,units='probability') for a in arms]
        error(ax,np.arange(4)+(-.035 if gi==0 else .035),z,col,marker='o' if gi==0 else 's',label=label)
        body+=tplot(np.arange(4)+(-.035 if gi==0 else .035),z,col,mark='*' if gi==0 else 'square*',label=label)
    style(ax,title,'Failure probability (%)');ax.set_ylim(45,95);ax.set_xticks(range(4),arms);ax.legend(frameon=False,loc='lower left',handlelength=1.3)
    body+=r'\end{axis}'+'\n'
    for col,(contrast,subtitle,ylim) in enumerate([('I1-I0','p uncertainty',(-10,3)),('M1-M0','Persistence',(-.03,.65))],start=1):
        ax=fig.add_subplot(gs[row,col]);z=[]
        title=f'({chr(97+row*3+col)}) '+subtitle
        body+=axis(5.35+(col-1)*4.65,5.0 if row==0 else 0,4.5,4.5,title,r'xmin=-.4,xmax=1.4,xtick={0,1},xticklabels={'+','.join(('62','41') if row==0 else ('29','19'))+'},xlabel={Fixed group size},ylabel={Difference (pp)},ymin='+str(ylim[0])+',ymax='+str(ylim[1])+r',scaled y ticks=false,y tick label style={/pgf/number format/fixed,/pgf/number format/precision=2}')
        body+=tline(0,GRAY,'solid',x0=-.4,x1=1.4)
        for gi,(group,label,color) in enumerate(groups):
            zz=stat('reliability',f'/groups/{group}/contrasts/{contrast}/confirmed_failure',ci='conditional95',scale=100,units='probability difference')
            z.append(zz);error(ax,[gi],[zz],color,marker='o' if gi==0 else 's',ls='none')
            body+=tplot([gi],[zz],color,mark='*' if gi==0 else 'square*',ls='only marks')
        ax.axhline(0,color=GRAY,lw=.65);style(ax,title,'Difference (pp)');ax.set_ylim(*ylim);ax.set_xlim(-.4,1.4);ax.set_xticks([0,1],['62','41'] if row==0 else ['29','19']);ax.set_xlabel('Fixed group size')
        ax.text(.5,.92,contrast.replace('-',' − '),transform=ax.transAxes,ha='center',fontsize=8)
        body+=r'\node[font=\fontsize{8}{9}\selectfont] at (rel axis cs:.5,.92) {'+contrast.replace('-',r'$-$')+'};\n'+r'\end{axis}'+'\n'
caption=r'Correctness uncertainty and same-class persistence in the training-only EEG reliability reference. Rows distinguish all 62 participants and the nested 41 from the fixed initially task-qualified groups of 29 and 19. (a,d) I0 fixes the independent posterior-mean correctness probability; I1 draws it from the independent posterior; M0 uses a probability drawn from the Markov posterior but sets persistence to zero; M1 uses exactly the same probability draws and sampled persistence. (b,e) I1 minus I0 isolates the specified correctness-parameter uncertainty. (c,f) M1 minus M0 isolates the specified same-class persistence at identical probability draws. The two contrast columns intentionally use different scales. Points and bars are stored means and conditional 95\% participant-bootstrap intervals (10,000 resamples; teachers and posteriors fixed), not Monte Carlo intervals or a full shared-training uncertainty analysis. Each arm uses 32,768 repetitions per participant; probabilities include every repetition in each fixed group, without reselection by simulated diagnostic success. Nested groups are not independent confirmations. These surrogate teachers do not calibrate the deployed teacher or estimate actual EEG drift.'
name='dynamics_reliability_reference';anchor='Main text: Reliability events depend on their definition and reference model, after the qualified-group paragraph.'
save(fig,name,caption,anchor,{'probability_axis_scale':100,'contrast_axis_scale':100,'contrast_units':'percentage points','confidence':'stored conditional participant bootstrap95; no refit','columns_use_different_scales':True,'qualified_groups':'original fixed identities; not selected by synthetic diagnostic','nested_cohorts':True})
block(name,caption,anchor,body)

# Fully inline figure blocks and exact raw records.
(ROOT/'paper/figure_blocks_dynamics.tex').write_text('% Generated by figure_assets_dynamics.py; all numbers inline.\n% Requires tikz and pgfplots (already in manuscript). No external graphics or tables.\n\n'+'\n\n'.join(TEX))
for item in META['figures']:
    for ext in ['png','pdf']:
        p=ROOT/item[ext];item[ext+'_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        item[ext+'_bytes']=p.stat().st_size
META['figure_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
META['inline_tex_sha256']=hashlib.sha256((ROOT/'paper/figure_blocks_dynamics.tex').read_bytes()).hexdigest()
META['validation']={'exact_source_records':len(RECORDS),'source_files':len(SOURCES),'source_pointer_and_values':'PASS','formal_result_only':True,'visual_check':'pending'}
(OUT/'dynamics_figure_data.json').write_text(json.dumps(META,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'figures':[x['name'] for x in META['figures']],'records':len(RECORDS),'source_files':len(SOURCES)},indent=2))
