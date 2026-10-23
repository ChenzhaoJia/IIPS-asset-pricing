"""Approved public-availability C2C baseline. No return-selected specification."""
from pathlib import Path
import os
os.environ["OPENBLAS_NUM_THREADS"]="2"
os.environ["OMP_NUM_THREADS"]="2"
import argparse
import hashlib
import io
import json
import sys
import time
import zipfile
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import statsmodels.api as sm

ROOT=Path("D:/draft")
sys.path.insert(0,str(ROOT/"data/analysis/revision"))
import response_lag_pricing_suite as old
from fast_panel_ch4 import fit_panel
from reply_date_joint_horse_race import CONTROL_COLUMNS as CTRL, CORE_TEXT_COLUMNS as TEXT
WORK=ROOT/"data/working/c2c_ch4_primary_2026-10-12"
OUT=ROOT/"data/verification/c2c_ch4_primary_2026-10-12"
ZIP=ROOT/"data/raw_factors/CSMAR/三因子模型指标(日)155823877.zip"
CH4=old.FACT
FF3=["ff3_mktrf","ff3_SMB","ff3_HML"]
H=[1,5,10,20,40,60]
SIG=["ESI","Investor_Tone","Manager_Tone"]

def log(s):
    print(time.strftime("%H:%M:%S"),s,flush=True)
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save_json(name,d):
    (OUT/name).write_text(json.dumps(d,ensure_ascii=False,indent=2,default=str),encoding="utf-8")

def factors():
    with zipfile.ZipFile(ZIP) as z:
        assert z.testzip() is None
        desc=z.read("STK_MKT_THRFACDAY[DES][csv].txt").decode("utf-8-sig")
        assert "P9714" in desc and "创业板和科创板" in desc
        f=pd.read_csv(io.BytesIO(z.read("STK_MKT_THRFACDAY.csv")))
    f=f.loc[f.MarkettypeID.eq("P9714")].copy()
    f["Date"]=pd.to_datetime(f.TradingDate)
    assert not f.Date.duplicated().any()
    f=f.set_index("Date")[["RiskPremium1","SMB1","HML1"]]
    f.columns=FF3
    # Values are decimal daily returns, not percentages to divide again.
    recent=f.loc["2017":"2024"]
    assert recent.notna().all().all() and recent.abs().max().max()<.15
    ch=old.factors()[CH4]
    joined=ch.join(f,how="left")
    joined.to_parquet(WORK/"daily_domestic_factors.parquet")
    (OUT/"FF3_field_description.txt").write_text(desc,encoding="utf-8")
    first=next(pq.ParquetFile(old.BASE).iter_batches(batch_size=6000,
        columns=["Date","Mkt_RF","SMB","HML"])).to_pandas().drop_duplicates("Date").set_index("Date")
    comparison=first.join(f,how="inner")
    differences={a:float((comparison[a]-comparison[b]).abs().max())
                 for a,b in zip(["Mkt_RF","SMB","HML"],FF3)}
    save_json("factor_source_audit.json",dict(
        source_zip=str(ZIP),source_zip_sha256=sha(ZIP),market="P9714",
        fields=["RiskPremium1","SMB1","HML1"],source_unit="decimal daily return",
        conversion=1,source_recent_dates=len(recent),old_panel_max_abs_differences=differences,
        note="New download version used for FF3. Old panel is not overwritten.",
        CH4_source=str(old.OLD/"two_same_day_factor_returns_2026-09-22.parquet")))
    log("Domestic FF3/CH4 source and date audit passed")

def load():
    p=pd.read_parquet(old.WORK/"pricing_panel.parquet")
    assert not p.duplicated(["Stkcd","Date"]).any()
    assert p.Date.between(old.START,old.END).all()
    scales=json.loads((old.OUT/"regression_scaling.json").read_text())
    params=old.parameters()
    p["ESI_z"]=(p.ESI-scales["ESI_mean"])/scales["ESI_std"]
    p["Investor_Tone_z"]=(p.Investor_Tone-params.investor_p30)/params.investor_std
    p["Manager_Tone_z"]=(p.Manager_Tone-params.manager_mean)/params.manager_std
    for c in set(CTRL+TEXT)-set(SIG[1:]):
        p[c+"_z"]=(p[c]-p[c].mean())/p[c].std()
    return p

def stat(r,v,kind="Panel OLS"):
    ci=r.conf_int().loc[v]
    return dict(estimator=kind,term=v,coefficient_bps=float(r.params[v]*1e4),
        t=float(r.tstats[v]),p=float(r.pvalues[v]),ci_low_bps=float(ci.iloc[0]*1e4),
        ci_high_bps=float(ci.iloc[1]*1e4),n=int(r.nobs),
        adjusted_r2=float(1-(1-r.rsquared_inclusive)*(r.nobs-1)/r.df_resid))

def outcomes(p):
    a=old.market_arrays()
    i=p.firm_idx.to_numpy(int);j=p.date_idx.to_numpy(int)
    for h in H:
        y=np.full(len(p),np.nan)
        ok=np.where(j+h<len(a["dates"]))[0]
        rr=np.stack([a["ret"][i[ok],j[ok]+k] for k in range(1,h+1)],axis=1).astype(float)
        rf=np.stack([a["rf"][j[ok]+k] for k in range(1,h+1)],axis=1)
        good=np.isfinite(rr).all(1)&np.isfinite(rf).all(1)&(rr>=-1).all(1)
        y[ok[good]]=np.prod(1+rr[good],axis=1)-np.prod(1+rf[good],axis=1)
        p[f"C2C_{h}"]=y
        if h in [1,5,20,60]:
            assert np.nanmax(np.abs(p[f"C2C_{h}"]-p[f"C2C_1_{h}"]))<1e-10
    return p

def regressions():
    p=outcomes(load())
    cc=[c+"_z" for c in CTRL]
    tt=[c+"_z" for c in TEXT]
    common=p.replace([np.inf,-np.inf],np.nan).dropna(subset=["C2C_1","ESI_z",*tt,*cc])
    specs=[
        ["ESI_z"],["Investor_Tone_z"],["Manager_Tone_z"],
        ["Investor_Tone_z","Manager_Tone_z","Log_Num_Questions_z","Substantiveness_ML_z"],
        tt,["ESI_z",*tt]]
    rows=[]
    for k,x in enumerate(specs,1):
        log(f"Horse race column {k}, N={len(common):,}")
        r,_=fit_panel(common,"C2C_1",x+cc)
        rows.extend(dict(block=k,horizon=1,**stat(r,v)) for v in x)
        pd.DataFrame(rows).to_parquet(OUT/"horse_race.parquet",index=False)
    horizons=[]
    for h in H:
        y=f"C2C_{h}"
        for v in ["ESI_z","Investor_Tone_z","Manager_Tone_z","Substantiveness_ML_z","Log_Num_Questions_z"]:
            d=p.replace([np.inf,-np.inf],np.nan).dropna(subset=[y,v,*cc])
            r,_=fit_panel(d,y,[v,*cc])
            horizons.append(dict(horizon=h,**stat(r,v)))
        log(f"Panel horizon {h} completed")
        pd.DataFrame(horizons).to_parquet(OUT/"horizons.parquet",index=False)
    fmb=[]
    for h in H:
        y=f"C2C_{h}"
        for v in ["ESI_z","Investor_Tone_z","Manager_Tone_z"]:
            d=p.replace([np.inf,-np.inf],np.nan).dropna(subset=[y,v,*cc])
            xx=[v,*cc];daily=[]
            for date,g in d.groupby("Date",sort=True):
                x=sm.add_constant(g[xx],has_constant="add").to_numpy(float)
                n,k=x.shape
                if n<=k+5 or np.linalg.matrix_rank(x)<k:continue
                target=g[y].to_numpy(float)
                beta=np.linalg.lstsq(x,target,rcond=None)[0]
                error=target-x@beta
                tss=np.sum((target-target.mean())**2)
                if tss<=0:continue
                daily.append(dict(Date=date,slope=beta[1],n=n,adj=1-(error@error/tss)*(n-1)/(n-k)))
            ds=pd.DataFrame(daily).set_index("Date")
            rr=old.hac(ds.slope,lag=max(5,h))
            z=old.hacrow(rr)
            z["coefficient_bps"]=z.pop("alpha_bps")
            z["adjusted_r2"]=float(ds.adj.mean())
            z["n_firm_days"]=int(ds.n.sum());z["n_dates"]=len(ds)
            fmb.append(dict(estimator="Fama-MacBeth",horizon=h,term=v,**z))
        log(f"Fama-MacBeth horizon {h} completed")
        pd.DataFrame(fmb).to_parquet(OUT/"fama_macbeth.parquet",index=False)
    p.to_parquet(WORK/"primary_panel_with_outcomes.parquet",index=False)
    save_json("regression_scope.json",dict(
        input_rows=len(p),horse_race_common_rows=len(common),horizons=H,
        ESI_parameters=params_dict(),primary_outcome="C2C excess total return from close(a) to close(a+h)",
        controls=CTRL,competing_features=TEXT,CH4_adjustment="Portfolio alphas and historical risk exposure tests, not ex post residual outcomes"))

def params_dict():
    return old.parameters().to_dict()

def portfolios():
    f=pd.read_parquet(WORK/"daily_domestic_factors.parquet")
    d=pd.read_parquet(old.WORK/"portfolio_daily_all.parquet")
    d=d.loc[d.variant.eq("common_pool")&d.period.eq(1)&d.execution.eq("theoretical_close")].copy()
    rows=[]
    for weight in ["EW","VW"]:
        subset=d.loc[d.weight.eq(weight)]
        # Same complete dates for every signal, leg and both factor models.
        complete=subset.pivot(index="Date",columns="signal",values=["Long","Short_Basket","LS"]).dropna()
        complete.columns=complete.columns.to_flat_index()
        joined=complete.join(f).dropna()
        for sig in SIG:
            for leg in ["Long","Short_Basket","LS"]:
                y=joined[(leg,sig)]
                for model,cols in [("CH4",CH4),("FF3",FF3)]:
                    r=old.hac(y,joined[cols],lag=5)
                    rows.append(dict(signal=sig,weight=weight,leg=leg,model=model,
                        mean_bps=float(y.mean()*1e4),annual_return_pct=float(np.expm1(y.mean()*242)*100),
                        sharpe=float(y.mean()/y.std()*np.sqrt(242)),**old.hacrow(r)))
        log(f"Portfolio {weight} common dates {len(joined)}")
    pd.DataFrame(rows).to_parquet(OUT/"portfolios.parquet",index=False)
    save_json("portfolio_scope.json",dict(
        input=str(old.WORK/"portfolio_daily_all.parquet"),input_sha256=sha(old.WORK/"portfolio_daily_all.parquet"),
        selection_or_weights_changed=False,variant="common_pool",period=1,execution="theoretical_close",
        factor_date="same date as ending C2C return",gross=True,
        caveat="Short legs are theoretical. Costs, availability and execution diagnostics remain separate."))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("stage",choices=["factors","regressions","portfolios"])
    stage=ap.parse_args().stage
    OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
    status=dict(stage=stage,state="running",pid=os.getpid(),started=time.strftime("%Y-%m-%dT%H:%M:%S"),
                code_sha256=sha(Path(__file__)),protocol=str(ROOT/"drafts/project_management/c2c_ch4_primary_protocol_2026-10-12.md"))
    save_json(f"status_{stage}.json",status)
    try:
        globals()[stage]()
    except Exception as error:
        status.update(state="failed",error=repr(error))
        save_json(f"status_{stage}.json",status)
        raise
    status.update(state="completed",finished=time.strftime("%Y-%m-%dT%H:%M:%S"))
    save_json(f"status_{stage}.json",status)

if __name__=="__main__":main()
