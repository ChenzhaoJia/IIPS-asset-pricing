"""Format verified outputs, archive unchanged historical tables, emit scoped patch."""
from pathlib import Path
import hashlib
import json
import re
import pandas as pd
ROOT=Path("D:/draft")
MAN=ROOT/"drafts/manuscript"
OUT=ROOT/"data/verification/c2c_ch4_primary_2026-10-12"
VERIFY=ROOT/"data/verification/overleaf_update_2026-10-12"
assert json.loads((OUT/"validation_report.json").read_text())["state"]=="passed"
def stars(p):return "***" if p<.01 else "**" if p<.05 else "*" if p<.1 else ""
def coef(r):return f"{r.coefficient_bps:.2f}{stars(r.p)}"
def alpha(r):return f"{r.alpha_bps:.2f}{stars(r.p)} ({r.t:.2f})"
def row(name,cells):return name+" & "+" & ".join(map(str,cells))+r" \\"+"\n"
def top(caption,label,n=7):
    return (r"\begin{table}[H]"+"\n"+r"\centering"+"\n"+rf"\caption{{{caption}}}"+"\n"
        +(rf"\label{{{label}}}"+"\n" if label else "")+
        r"\renewcommand{\arraystretch}{1.02}"+"\n"+r"\setlength{\tabcolsep}{3pt}"+"\n"+
        r"\footnotesize"+"\n"+r"\begin{threeparttable}"+"\n"+
        rf"\begin{{tabular*}}{{\textwidth}}{{@{{\extracolsep{{\fill}}}}l{'c'*(n-1)}@{{}}}}"+"\n"+r"\toprule"+"\n")
def tail(note):
    return (r"\bottomrule"+"\n"+r"\end{tabular*}\par"+"\n"+
        r"\begin{tablenoteblock}"+"\n"+note+"\n"+r"\end{tablenoteblock}"+"\n"+
        r"\end{threeparttable}"+"\n"+r"\end{table}"+"\n")
def panel(s):return r"\multicolumn{7}{@{}l}{\textbf{"+s+r"}} \\"+"\n"+r"\midrule"+"\n"
ports=pd.read_parquet(OUT/"portfolios.parquet")
labels={"ESI":"ESI","Investor_Tone":"Investor Tone","Manager_Tone":"Manager Tone"}
text=top("Portfolio Returns after Public Reply Availability","tab:horse_race")
for w,title in [("EW","Panel A: Equal Weights"),("VW","Panel B: Value Weights")]:
    if w=="VW":text+=r"\midrule"+"\n"
    text+=panel(title)
    text+=row("Signal",[r"Long (bps)",r"Short (bps)",r"Ann. Ret (\%)","Sharpe",r"CH4 $\alpha$",r"FF3 $\alpha$"])+r"\midrule"+"\n"
    for sig in labels:
        sub=ports.loc[ports.weight.eq(w)&ports.signal.eq(sig)]
        a=sub.loc[sub.leg.eq("LS")&sub.model.eq("CH4")].iloc[0]
        b=sub.loc[sub.leg.eq("LS")&sub.model.eq("FF3")].iloc[0]
        l=sub.loc[sub.leg.eq("Long")&sub.model.eq("CH4")].iloc[0]
        s=sub.loc[sub.leg.eq("Short_Basket")&sub.model.eq("CH4")].iloc[0]
        text+=row(labels[sig],[f"{l.mean_bps:.2f}",f"{s.mean_bps:.2f}",
            f"{a.annual_return_pct:.2f}",f"{a.sharpe:.2f}",alpha(a),alpha(b)])
text+=tail(r"All three signals use the same daily candidate stock pool and the same 1,786 complete return dates from 2017 through 2024. The information date $a$ is the first trading day strictly after the last recorded reply. Each long leg selects up to 50 stocks with positive signals from the upper 30 percent of the distribution. Each short leg selects up to 50 stocks with negative signals from the lower 30 percent. Returns run from close $a$ to close $a+1$ and include cash dividends. Long and Short are gross excess returns in basis points. Annualized return is $100[\exp(242\overline{r}^{LS})-1]$, and Sharpe uses 242 trading days. Value weights use lagged market capitalization. CH4 and the domestic FF3 factors cover the same holding day. FF3 uses CSMAR market P9714 and the circulating market capitalization series RiskPremium1, SMB1, and HML1. Alphas are in basis points, with HAC $t$ statistics using five exchange trading day lags in parentheses. Missing return dates are retained as gaps in the HAC calendar. The short leg is theoretical, and returns exclude trading and borrowing costs. ***, **, and * denote nominal significance at 1\%, 5\%, and 10\%, respectively.")
(MAN/"tables/primary_c2c_portfolios_2026-10-12.tex").write_text(text,encoding="utf-8")
hr=pd.read_parquet(OUT/"horse_race.parquet")
hz=pd.read_parquet(OUT/"horizons.parquet")
fm=pd.read_parquet(OUT/"fama_macbeth.parquet")
terms=["ESI_z","Investor_Tone_z","Manager_Tone_z","Log_Num_Questions_z",
       "Substantiveness_ML_z","Log_Question_Length_z","Log_Reply_Length_z","QA_Similarity_z"]
names=["ESI","Investor Tone","Manager Tone","Question Volume","Reply Substantiveness",
       "Question Length","Reply Length",r"Q\&A Similarity"]
text=top("Return Predictability after Public Reply Availability","tab:panel_horse_race")
text+=panel("Panel A: Horse Race Tests for Next Day C2C Excess Returns")
text+=row("Predictor",[f"({i})" for i in range(1,7)])+r"\midrule"+"\n"
for term,name in zip(terms,names):
    values=[];ts=[]
    for i in range(1,7):
        d=hr.loc[hr.block.eq(i)&hr.term.eq(term)]
        values.append(coef(d.iloc[0]) if len(d) else "")
        ts.append(f"({d.iloc[0].t:.2f})" if len(d) else "")
    text+=row(name,values)+row("",ts)
text+=r"\midrule"+"\n"
text+=row("Controls, Firm FE, Date FE",["Yes"]*6)
text+=row("Observations",[f"{int(hr.loc[hr.block.eq(i)].iloc[0].n):,}" for i in range(1,7)])
text+=row(r"Adjusted $R^2$",[f"{hr.loc[hr.block.eq(i)].iloc[0].adjusted_r2:.3f}" for i in range(1,7)])
delta=hr.loc[hr.block.eq(6)].iloc[0].adjusted_r2-hr.loc[hr.block.eq(5)].iloc[0].adjusted_r2
text+=tail(r"All columns use the same 377,721 observations from 2017 through 2024. The outcome runs from close $a$ to close $a+1$, where $a$ is the first trading day strictly after the last recorded reply. Coefficients are in basis points. Investor and managerial tone and ESI use their historical calibration scales. Other text features and controls are centered and scaled within the availability panel without using return outcomes. All columns include the baseline controls in Section \ref{sec:baseline_return_predictability}, firm effects, and date effects. Standard errors are clustered by firm and date. Adjusted $R^2$ accounts for the regressors and absorbed effects. The unrounded adjusted $R^2$ change from column (5) to column (6) is "+"$"+f"{delta:.9f}"+"$"+r". ***, **, and * denote nominal significance at 1\%, 5\%, and 10\%, respectively.")
text+=r"\clearpage"+"\n"
text+=top("Return Predictability after Public Reply Availability (continued)","")
text=text.replace(r"\caption{Return Predictability after Public Reply Availability (continued)}",
    r"\ContinuedFloat"+"\n"+r"\caption{Return Predictability after Public Reply Availability (continued)}")
H=[1,5,10,20,40,60]
for data,title in [(hz,"Panel B: Panel OLS across Horizons"),(fm,"Panel C: Fama and MacBeth Regressions")]:
    if data is fm:text+=r"\midrule"+"\n"
    text+=panel(title)+row("Predictor",[f"{h} Day"+("s" if h>1 else "") for h in H])+r"\midrule"+"\n"
    use=terms[:5] if data is hz else terms[:3]
    for term in use:
        rs=[data.loc[data.horizon.eq(h)&data.term.eq(term)].iloc[0] for h in H]
        text+=row(names[terms.index(term)],[coef(r) for r in rs])+row("",[f"({r.t:.2f})" for r in rs])
    text+=r"\midrule"+"\n"
    text+=row("Controls",["Yes"]*6)
    if data is hz:text+=row("Firm FE and Date FE",["Yes"]*6)
    rs=[data.loc[data.horizon.eq(h)&data.term.eq("ESI_z")].iloc[0] for h in H]
    text+=row("Observations",[f"{int(r.n if data is hz else r.n_firm_days):,}" for r in rs])
    if data is fm:text+=row("Daily Cross Sections",[f"{int(r.n_dates):,}" for r in rs])
    text+=row(r"Adjusted $R^2$",[f"{r.adjusted_r2:.3f}" for r in rs])
text+=tail(r"The outcome is the cumulative total stock return minus the cumulative risk free return from close $a$ to close $a+h$, with complete observations for every holding day. Each signal enters a separate regression with the baseline controls. The observations and adjusted $R^2$ in each column refer to the ESI specification. Panel B uses firm and date effects and standard errors clustered by firm and date. Panel C averages estimable daily cross-sectional slopes. Its HAC standard errors use $\max(5,h)$ exchange trading day lags, retaining missing estimation dates as calendar gaps. The reported adjusted $R^2$ is the mean across these daily regressions. Coefficients are in basis points and $t$ statistics appear in parentheses. Stars denote nominal significance and do not adjust for the correlated horizon tests.")
(MAN/"tables/primary_c2c_regressions_2026-10-12.tex").write_text(text,encoding="utf-8")
source=(MAN/"main.tex").read_text(encoding="utf-8")
table_re=re.compile(r"\\begin\{table\}\[H\].*?\\end\{table\}",re.S)
ops=[]
legacy=[]
for label,new_file in [
    ("tab:horse_race","primary_c2c_portfolios_2026-10-12.tex"),
    ("tab:conditional_double_sorts",None),
    ("tab:panel_horse_race","primary_c2c_regressions_2026-10-12.tex")]:
    matches=[m.group(0) for m in table_re.finditer(source) if rf"\label{{{label}}}" in m.group(0)]
    assert len(matches)==1,label
    old=matches[0]
    saved=old
    if label!="tab:conditional_double_sorts":
        saved=saved.replace(rf"\label{{{label}}}",rf"\label{{{label}_legacy}}")
    saved=re.sub(r"(\\caption\{)([^}]+)(\})",lambda m:m[1]+"Historical Question Date O2C Specification: "+m[2]+m[3],saved,count=1)
    legacy.append(saved)
    ops.append(dict(id="PRIMARY_TABLE_"+label,old=old,new=(rf"\input{{tables/{new_file}}}" if new_file else "% Conditional O2C table is retained in the supplementary appendix.")))
archive=(r"\subsection{Historical question date O2C comparisons}"+"\n"+
    r"These tables preserve the earlier question date specification and its original numerical results. They are supplementary diagnostics, not the current public availability C2C baseline. Their daily factor adjustments include an overnight interval absent from O2C. The q5 series is from the United States and is not a domestic risk benchmark."+"\n\n"+
    "\n\n".join(legacy)+"\n")
(MAN/"tables/historical_o2c_comparisons_2026-10-12.tex").write_text(archive,encoding="utf-8")
anchor=r"\section{Supplementary Robustness Tables}\label{app:robustness_tables}"
ops.append(dict(id="ARCHIVE_O2C",old=anchor,new=anchor+"\n\n"+r"\input{tables/historical_o2c_comparisons_2026-10-12.tex}"))
patch="*** Begin Patch\n*** Update File: D:/draft/drafts/manuscript/main.tex\n"
for op in ops:
    assert source.count(op["old"])==1
    op["old_sha256"]=hashlib.sha256(op["old"].encode()).hexdigest()
    patch+="@@\n"+"\n".join("-"+x for x in op["old"].splitlines())+"\n"+"\n".join("+"+x for x in op["new"].splitlines())+"\n"
patch+="*** End Patch\n"
(VERIFY/"primary_tables.patch").write_text(patch,encoding="utf-8")
(VERIFY/"primary_table_patch_manifest.json").write_text(json.dumps(ops,ensure_ascii=False,indent=2),encoding="utf-8")
print("Verified primary tables and historical appendix prepared",flush=True)
