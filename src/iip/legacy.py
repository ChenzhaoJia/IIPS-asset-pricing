"""Frozen historical algorithms. These are retrospective, not point-in-time strategies."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import pyhdfe
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from linearmodels.panel.covariance import ClusteredCovariance


def esi(d):
    valid=d[['Investor_Tone','Manager_Tone','Substantiveness_ML']].notna().all(axis=1)
    inv=d.loc[valid,'Investor_Tone'];mgr=d.loc[valid,'Manager_Tone']
    log_attn=np.log1p(d.Num_Questions.fillna(0));den=log_attn.max()
    theta=inv.quantile(.30);sigma=inv.std()*.8
    base=d.Investor_Tone*(1+.5*log_attn/den)
    impact=(d.Manager_Tone-mgr.mean())/mgr.std()*d.Substantiveness_ML*np.exp(-((d.Investor_Tone-theta)**2)/(2*sigma**2))
    impact.loc[(d.Investor_Tone>0)&(impact<0)]=0
    score=(base+5.*impact).astype('float32')
    return score,dict(complete_text_n=int(valid.sum()),manager_mean=float(mgr.mean()),manager_std=float(mgr.std()),investor_p30=float(theta),investor_std=float(inv.std()),sigma=float(sigma),attention_log_max=float(den),lambda_attention=.5,gamma_manager=5.,bandwidth_multiplier=.8,asymmetric_truncation=True,score_mean=float(score.mean()),score_std=float(score.std()),scope='Full original notebook pre-group pool, 2010-2024; frozen once before lag classification')


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


def within_fit(d,ycol,xcols,group=None):
    d=d.sort_values(['Stkcd','Date']).copy()
    entities=pd.factorize(d.Stkcd,sort=True)[0];dates=pd.factorize(d.Date,sort=True)[0]
    clusters=np.column_stack([entities,dates])
    if group is None:feids=clusters
    else:
        feids=np.column_stack([pd.factorize(pd.MultiIndex.from_arrays([d.Stkcd,group.loc[d.index]]),sort=True)[0],pd.factorize(pd.MultiIndex.from_arrays([d.Date,group.loc[d.index]]),sort=True)[0]])
    # Exact additive FE rank. Group blocks are disconnected, so one common intercept
    # subtraction is insufficient in a fully interacted model.
    ne=int(feids[:,0].max()+1);nt=int(feids[:,1].max()+1)
    a=feids[:,0];b=ne+feids[:,1]
    graph=coo_matrix((np.ones(2*len(d)),(np.r_[a,b],np.r_[b,a])),shape=(ne+nt,ne+nt)).tocsr()
    components=connected_components(graph,directed=False,return_labels=False)
    fe=ne+nt-components
    algo=pyhdfe.create(feids,drop_singletons=False,compute_degrees=False,residualize_method='map',options={'transform':'symmetric','acceleration':'cg','tol':1e-10})
    original=d[[ycol,*xcols]].to_numpy(float)
    z=algo.residualize(original);y=z[:,[0]];x=z[:,1:]
    assert np.linalg.matrix_rank(x)==len(xcols),'Absorbed or rank-deficient full specification'
    beta=np.linalg.lstsq(x,y,rcond=None)[0]
    cov=ClusteredCovariance(y,x,beta,entities[:,None],dates[:,None],debiased=True,extra_df=int(fe),clusters=clusters,group_debias=False).cov
    df=len(d)-fe-len(xcols)
    assert df>0
    rss=float(((y-x@beta)**2).sum());tss=float(((original[:,0]-original[:,0].mean())**2).sum())
    return dict(beta=beta.ravel(),cov=cov,df=int(df),n=len(d),firms=ne if group is None else len(np.unique(entities)),dates=nt if group is None else len(np.unique(dates)),fe_rank=int(fe),fe_components=int(components),adjusted_r2=1-(rss/tss)*(len(d)-1)/df,xcols=xcols),d,feids,clusters
