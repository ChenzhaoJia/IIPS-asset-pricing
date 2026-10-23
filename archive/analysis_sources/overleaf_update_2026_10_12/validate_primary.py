"""Independent FE projection and explicit calendar-HAC numerical checks."""
import os
os.environ["OPENBLAS_NUM_THREADS"]="2"
os.environ["OMP_NUM_THREADS"]="2"
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
from scipy.stats import norm
from linearmodels.panel import PanelOLS
ROOT=Path("D:/draft")
sys.path.insert(0,str(Path(__file__).parent))
import primary_c2c_suite as main

def run():
    out=main.OUT
    p=pd.read_parquet(main.WORK/"primary_panel_with_outcomes.parquet")
    cc=[x+"_z" for x in main.CTRL]
    tt=[x+"_z" for x in main.TEXT]
    d=p.replace([np.inf,-np.inf],np.nan).dropna(subset=["C2C_1","ESI_z",*tt,*cc])
    expected=pd.read_parquet(out/"horse_race.parquet")
    comparisons=[]
    for block,terms in [(1,["ESI_z"]),(6,["ESI_z",*tt])]:
        sample=d[["Stkcd","Date","C2C_1",*terms,*cc]].sort_values(["Stkcd","Date"]).set_index(["Stkcd","Date"])
        fit=PanelOLS(sample.C2C_1,sample[terms+cc],entity_effects=True,time_effects=True).fit(
            cov_type="clustered",cluster_entity=True,cluster_time=True,low_memory=True)
        adj=1-(1-fit.rsquared_inclusive)*(fit.nobs-1)/fit.df_resid
        for term in terms:
            e=expected.loc[expected.block.eq(block)&expected.term.eq(term)].iloc[0]
            delta=dict(block=block,term=term,
                coefficient_bps=float(fit.params[term]*1e4-e.coefficient_bps),
                t=float(fit.tstats[term]-e.t),p=float(fit.pvalues[term]-e.p),
                adjusted_r2=float(adj-e.adjusted_r2))
            delta["display_matches"]=round(fit.params[term]*1e4,2)==round(e.coefficient_bps,2) and round(fit.tstats[term],2)==round(e.t,2)
            comparisons.append(delta)
        print("Independent PanelOLS",block,"completed",flush=True)
    pd.DataFrame(comparisons).to_csv(out/"independent_fe_differences.csv",index=False)
    r=pd.DataFrame(comparisons)
    fe_ok=(r.coefficient_bps.abs().max()<=1e-5 and r.t.abs().max()<=1e-5
           and r.p.abs().max()<=1e-5 and r.adjusted_r2.abs().max()<=1e-8 and r.display_matches.all())
    factors=pd.read_parquet(main.WORK/"daily_domestic_factors.parquet")
    raw=pd.read_parquet(main.old.WORK/"portfolio_daily_all.parquet")
    raw=raw.loc[raw.variant.eq("common_pool")&raw.period.eq(1)&raw.execution.eq("theoretical_close")]
    estimates=pd.read_parquet(out/"portfolios.parquet")
    checks=[]
    cal=main.old.factors().index
    for weight,part in raw.groupby("weight"):
        pivot=part.pivot(index="Date",columns="signal",values=["Long","Short_Basket","LS"]).dropna()
        pivot.columns=pivot.columns.to_flat_index()
        joined=pivot.join(factors).dropna()
        pos=cal.get_indexer(joined.index)
        assert (pos>=0).all()
        pos-=pos.min()
        for signal in main.SIG:
            for model,names in [("CH4",main.CH4),("FF3",main.FF3)]:
                x=np.column_stack([np.ones(len(joined)),joined[names].to_numpy(float)])
                y=joined[("LS",signal)].to_numpy(float)
                beta=np.linalg.lstsq(x,y,rcond=None)[0]
                u=y-x@beta
                scores=np.zeros((pos.max()+1,x.shape[1]))
                scores[pos]=x*u[:,None]
                meat=scores.T@scores
                for lag in range(1,6):
                    cross=scores[lag:].T@scores[:-lag]
                    meat+=(1-lag/6)*(cross+cross.T)
                inv=np.linalg.inv(x.T@x)
                covariance=inv@meat@inv*len(y)/(len(y)-x.shape[1])
                t=beta[0]/np.sqrt(covariance[0,0])
                row=estimates.loc[estimates.weight.eq(weight)&estimates.signal.eq(signal)&estimates.model.eq(model)&estimates.leg.eq("LS")].iloc[0]
                checks.append(dict(weight=weight,signal=signal,model=model,
                    alpha_delta_bps=float(beta[0]*1e4-row.alpha_bps),t_delta=float(t-row.t),
                    p_delta=float(2*norm.sf(abs(t))-row.p),n_matches=len(y)==row.n))
    check=pd.DataFrame(checks)
    check.to_csv(out/"independent_portfolio_differences.csv",index=False)
    port_ok=bool(check.alpha_delta_bps.abs().max()<=1e-5 and check.t_delta.abs().max()<=1e-5 and check.p_delta.abs().max()<=1e-5 and check.n_matches.all())
    report=dict(state="passed" if fe_ok and port_ok else "failed",
        FE_independent_algorithm_passed=bool(fe_ok),portfolio_calendar_HAC_passed=port_ok,
        FE_max_absolute_differences={c:float(r[c].abs().max()) for c in ["coefficient_bps","t","p","adjusted_r2"]},
        scope="Two complete horse-race columns and all twelve LS alphas. Not independent semantic validation or bytewise full workflow replication.",
        statistical_interpretation={
            "positive_alpha_not_risk_factor":True,"null_not_proof_of_zero":True,
            "nominal_multiple_horizons_not_independent_discoveries":True,
            "predictive_association_not_causality":True,"viewed_later_sample_not_untouched_holdout":True,
            "same_pool_and_dates_required":True,"theoretical_shorting_not_implementability":True,
            "assistant_labels_not_human_accuracy":True,"SUE_update_date_not_Annodt":True,
            "O2C_factor_window_mismatch_disclosed":True,"no_return_selected_calibration":True})
    (out/"validation_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2),flush=True)
    if not fe_ok or not port_ok:raise RuntimeError("Predeclared numerical validation gate failed")

if __name__=="__main__":run()
