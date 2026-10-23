import pandas as pd

def format_academic_table(results_dict, order_of_vars):
    formatted_rows = []
    for var in order_of_vars:
        row_coef, row_tstat = [var], [""]
        var_found = False
        for m_name, res in results_dict.items():
            if var in res['params']:
                var_found = True
                coef = res['params'][var] 
                tstat = res['tstats'][var]
                stars = '***' if abs(tstat)>2.58 else ('**' if abs(tstat)>1.96 else ('*' if abs(tstat)>1.65 else ''))
                row_coef.append(f"{coef:.2f}{stars}")
                row_tstat.append(f"({tstat:.2f})")
            else:
                row_coef.append("-")
                row_tstat.append("-")
        if var_found:
            formatted_rows.append(row_coef)
            formatted_rows.append(row_tstat)
            
    fe_firm, fe_time, r2, nobs = ['Firm FE'], ['Time FE'], ['Adj. R2_Within'], ['Observations']
    for m_name, res in results_dict.items():
        fe_firm.append("Yes" if res['fe']['entity'] else "No")
        fe_time.append("Yes" if res['fe']['time'] else "No")
        r2.append(f"{res['r2']:.4f}")
        nobs.append(f"{res['nobs']:,}")
        
    formatted_rows.extend([[], fe_time, fe_firm, [], r2, nobs])
    return pd.DataFrame(formatted_rows, columns=['Variable'] + list(results_dict.keys())).set_index('Variable')