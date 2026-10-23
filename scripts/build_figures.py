"""Describe the frozen regression-pool text distribution; no outcome selection."""
from pathlib import Path
import json, sys, os
R=Path(__file__).resolve().parents[1]
# Optional task-local installation, without modifying the research environment.
extra=R/'build/plot_packages'
if extra.exists():sys.path.insert(0,str(extra))
os.environ.setdefault('MPLCONFIGDIR',str(R/'build/matplotlib'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def run():
    out=R/'data/results/descriptive';out.mkdir(exist_ok=True)
    fig=R/'drafts/manuscript/figures'
    p=json.loads((R/'data/results/annual_review_o2c/frozen_scales.json').read_text())['regression']
    d=pd.read_parquet(R/'data/processed/01_Base_Daily_Panel_Advanced.parquet',columns=['Firm_Age_Ln','Investor_Tone','Manager_Tone','Substantiveness_ML','Num_Questions'])
    d=d.loc[d.Firm_Age_Ln.ge(np.log(.5))]
    q=d.dropna(subset=['Investor_Tone','Manager_Tone','Substantiveness_ML'])
    assert len(q)==p['complete_text_n']
    assert abs(q.Investor_Tone.quantile(.30)-p['investor_p30'])<1e-7
    q[['Investor_Tone','Manager_Tone','Substantiveness_ML','Num_Questions']].describe().T.to_csv(out/'regression_pool_summary.csv')
    edges=np.linspace(-1,1,61);counts,_=np.histogram(q.Investor_Tone,bins=edges)
    pd.DataFrame({'left':edges[:-1],'right':edges[1:],'n':counts,'share':counts/len(q)}).to_csv(out/'investor_tone_histogram.csv',index=False)
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    f,ax=plt.subplots(figsize=(8,3.5),layout='constrained')
    ax.bar(edges[:-1],counts/len(q)*100,width=np.diff(edges),align='edge',color='#33658a',edgecolor='white',linewidth=.25)
    ax.axvline(p['investor_p30'],color='#b64b36',label='30th percentile')
    for sign in [-1,1]:ax.axvline(p['investor_p30']+sign*p['sigma'],ls='--',color='#b64b36',alpha=.7)
    ax.set(xlabel='Investor tone',ylabel='Share of complete text observations (%)',xlim=(-1,1))
    ax.legend(frameon=False,loc='upper left')
    f.savefig(fig/'investor_distribution.pdf');plt.close(f)
    f,axes=plt.subplots(1,2,figsize=(8,3.4),layout='constrained')
    n=np.arange(0,122);a=1+.5*np.log1p(n)/p['attention_log_max']
    axes[0].plot(n,a,color='#33658a');axes[0].set(xlabel='Number of questions',ylabel='Attention multiplier',ylim=(.98,1.52))
    x=np.linspace(-1,1,501);k=np.exp(-(x-p['investor_p30'])**2/(2*p['sigma']**2))
    axes[1].plot(x,k,color='#b64b36');axes[1].axvline(p['investor_p30'],ls=':',color='gray');axes[1].set(xlabel='Investor tone',ylabel='Managerial state weight',ylim=(0,1.05))
    f.savefig(fig/'esi_weights.pdf');plt.close(f)
    print('Saved two figures and aggregate descriptive sources.')

if __name__=='__main__':run()
