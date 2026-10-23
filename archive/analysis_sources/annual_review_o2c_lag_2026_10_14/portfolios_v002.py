import os
os.environ['OPENBLAS_NUM_THREADS']='2'
os.environ['OMP_NUM_THREADS']='2'
import itertools,json
import numpy as np,pandas as pd,statsmodels.api as sm
from scipy.stats import norm
from statsmodels.stats.multitest import multipletests
from prepare import ROOT,GROUPS,CH4,Q5,save,log

def hac(y,factors=None):
    if factors is None:d=y.rename('y').to_frame().dropna()
    else:d=y.rename('y').to_frame().join(factors.fillna(0)).dropna(subset=['y'])
    assert d.index.is_unique and d.index.is_monotonic_increasing
    x=np.column_stack([np.ones(len(d)),d.drop(columns='y').to_numpy(float)])
    assert len(d)>=30 and np.linalg.matrix_rank(x)==x.shape[1]
    fit=sm.OLS(d.y.to_numpy(float),x).fit(cov_type='HAC',cov_kwds={'maxlags':5})
    return dict(alpha_bps=float(fit.params[0]*1e4),t=float(fit.tvalues[0]),p=float(fit.pvalues[0]),se_bps=float(fit.bse[0]*1e4),
                ci_low_bps=float((fit.params[0]-1.95996398454*fit.bse[0])*1e4),ci_high_bps=float((fit.params[0]+1.95996398454*fit.bse[0])*1e4),n=len(d),
                beta=np.asarray(fit.params),cov=np.asarray(fit.cov_params()),x=x,y=d.y.to_numpy(float),dates=d.index.to_numpy())

def select(d,group,signal,keep):
    useful=d.loc[d[signal].notna()&d[signal].ne(0)&d.port_next.notna()&d.MktCap_B.notna()&d.Next_LimitStatus.eq(0)].copy()
    days=[];hold=[]
    for date,pool in useful.groupby('Date',sort=True):
        if len(pool)<2:continue
        lo,hi=pool[signal].quantile([.3,.7])
        long=pool.loc[pool[signal].gt(0)&pool[signal].ge(hi)].sort_values(signal,ascending=False).head(50)
        short=pool.loc[pool[signal].lt(0)&pool[signal].le(lo)].sort_values(signal,ascending=True)
        short=short.loc[~short.Stkcd.isin(long.Stkcd)].head(50)
        if long.empty or short.empty:continue
        for weight in ['EW','VW']:
            wl=np.full(len(long),1/len(long)) if weight=='EW' else (long.MktCap_B/long.MktCap_B.sum()).to_numpy()
            ws=np.full(len(short),1/len(short)) if weight=='EW' else (short.MktCap_B/short.MktCap_B.sum()).to_numpy()
            l=float((wl*long.port_next.to_numpy()).sum());s=float((ws*short.port_next.to_numpy()).sum())
            days.append(dict(group=group,signal=signal,weight=weight,Date=date,Long=l,Short=s,LS=l-s,long_n=len(long),short_n=len(short),candidates=len(pool),long_mean_lag=float(long.calendar_max.mean()),short_mean_lag=float(short.calendar_max.mean())))
            if keep:
                for leg,frame,w in [('Long',long,wl),('Short',short,ws)]:
                    hold.extend(dict(group=group,signal=signal,weight=weight,Date=date,leg=leg,Stkcd=int(stk),allocation=float(a),Execution_Date=end) for stk,a,end in zip(frame.Stkcd,w,frame.Execution_Date))
    return pd.DataFrame(days),pd.DataFrame(hold)

def main():
    assert not (ROOT/'portfolio_models_v002').exists()
    (ROOT/'portfolio_models_v002').mkdir()
    p=pd.read_parquet(ROOT/'prepared_port.parquet')
    factors=pd.read_parquet(ROOT/'factors.parquet')
    daily=[];holdings=[];models=[];perform=[];diff=[]
    signals=['ESI_sort','Investor_Tone','Manager_Tone']
    def fit_save(y,f,meta):
        r=hac(y,f);ident=f'p{len(models)+1:03d}'
        arrays={k:r.pop(k) for k in ['beta','cov','x','y','dates']}
        np.savez_compressed(ROOT/'portfolio_models_v002'/f'{ident}.npz',**arrays)
        models.append(dict(id=ident,file='portfolio_models_v002/'+ident+'.npz',**meta,n=r['n']));return r
    def performance(z,scope,index):
        for signal in signals:
            for weight in ['EW','VW']:
                q=z.loc[z.signal.eq(signal)&z.weight.eq(weight)].set_index('Date').sort_index()
                if index is not None:q=q.reindex(index).dropna(subset=['LS'])
                meta=dict(group=str(z.group.iloc[0]),signal=signal,weight=weight,scope=scope)
                row=dict(**meta,n=len(q),mean_bps=float(q.LS.mean()*1e4),annualized_return_pct=float(q.LS.mean()*242*100),sharpe=float(q.LS.mean()/q.LS.std()*np.sqrt(242)),average_long_n=float(q.long_n.mean()),average_short_n=float(q.short_n.mean()))
                for name,f in [('raw',None),('CH4',factors[CH4]),('q5',factors[Q5])]:
                    result=fit_save(q.LS,f,dict(kind='performance',benchmark=name,**meta))
                    row.update({name+'_'+k:v for k,v in result.items()})
                perform.append(row)
    # Reproduce the exact quoted legacy baseline before grouped sorting.
    for signal in signals:
        z,h=select(p,'all_original',signal,True);assert not z.empty
        daily.append(z);holdings.append(h)
    z=pd.concat(daily,ignore_index=True);performance(z,'own_signal_dates',None)
    preflight=[]
    targets={'EW':dict(mean_bps=5.32,raw_t=5.97,q5_alpha_bps=5.43,q5_t=6.08),'VW':dict(mean_bps=5.35,raw_t=3.64,q5_alpha_bps=5.50,q5_t=3.74)}
    for weight,target in targets.items():
        got=next(row for row in perform if row['signal']=='ESI_sort' and row['weight']==weight)
        checks={key:dict(quoted=value,computed=got[key],display_matches=f'{got[key]:.2f}'==f'{value:.2f}') for key,value in target.items()}
        preflight.append(dict(weight=weight,checks=checks))
    original=json.loads((ROOT/'original_sorter_preflight_v002.json').read_text())['rows']
    for row in original:
        signal='ESI_sort' if row['signal']=='ESI_Gamma_5.0' else row['signal']
        got=next(v for v in perform if v['signal']==signal and v['weight']==row['weight'])
        for key in ['mean_bps','q5_alpha_bps','q5_t']:
            assert abs(got[key]-row[key])<1e-4,(signal,key,got[key],row[key])
    save('portfolio_preflight_resolution.json',dict(status='original_sorter_verified_publication_differences_retained',quoted_display_preflight=preflight,original_sorter=original,scientific_rules_changed=False,ESI_scales_changed=False,grouped_results_previously_estimated=False))
    log('Original sorter verified; quoted publication differences retained without changing parameters')
    for group in GROUPS:
        sub=p.loc[p.lag_clean.fillna(False)&p.lag_group.eq(group)]
        chunks=[]
        for signal in signals:
            z,h=select(sub,group,signal,True);assert not z.empty,(group,signal)
            daily.append(z);holdings.append(h);chunks.append(z)
        zz=pd.concat(chunks,ignore_index=True)
        performance(zz,'own_signal_dates',None)
        pivot=zz.loc[zz.weight.eq('EW')].pivot(index='Date',columns='signal',values='LS').dropna()
        common=pivot.index
        performance(zz,'common_signal_dates',common)
        for weight in ['EW','VW']:
            q=zz.loc[zz.weight.eq(weight)].pivot(index='Date',columns='signal',values='LS').reindex(common).dropna()
            for other in ['Investor_Tone','Manager_Tone']:
                for name,ff in [('q5',Q5),('CH4',CH4)]:
                    meta=dict(group=group,weight=weight,contrast='ESI minus '+other,benchmark=name,family='tone_differences')
                    result=fit_save(q.ESI_sort-q[other],factors[ff],dict(kind='paired_difference',**meta))
                    diff.append(dict(**meta,**result))
        log('Portfolio sorts completed '+group+' input events '+str(len(sub)))
    D=pd.concat(daily,ignore_index=True)
    H=pd.concat(holdings,ignore_index=True)
    D.to_parquet(ROOT/'daily_portfolios.parquet',index=False);H.to_parquet(ROOT/'selected_holdings.parquet',index=False)
    for weight in ['EW','VW']:
        z=D.loc[D.signal.eq('ESI_sort')&D.weight.eq(weight)&D.group.isin(GROUPS)].pivot(index='Date',columns='group',values='LS').sort_index()
        for a,b in itertools.combinations(GROUPS,2):
            q=z[[a,b]].dropna()
            for name,ff in [('q5',Q5),('CH4',CH4)]:
                meta=dict(group=a+' vs '+b,weight=weight,contrast=a+' minus '+b,benchmark=name,family='lag_differences')
                result=fit_save(q[a]-q[b],factors[ff],dict(kind='paired_difference',**meta))
                diff.append(dict(**meta,**result))
    P=pd.DataFrame(perform);P.to_csv(ROOT/'portfolio_performance.csv',index=False)
    diff=pd.DataFrame(diff);diff['p_adjusted']=np.nan;diff['adjustment']=''
    for family,method in [('lag_differences','holm'),('tone_differences','fdr_bh')]:
        ix=diff.family.eq(family);assert ix.sum()==40
        diff.loc[ix,'p_adjusted']=multipletests(diff.loc[ix,'p'],method=method)[1];diff.loc[ix,'adjustment']=method
    diff.to_csv(ROOT/'portfolio_paired_differences.csv',index=False)
    save('portfolio_model_index.json',models)
    save('portfolio_status.json',dict(status='complete',models=len(models),performance_rows=len(P),difference_rows=len(diff),holdings_rows=len(H)))
    log('Portfolio stage complete')

if __name__=='__main__':main()
