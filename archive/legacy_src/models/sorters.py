import pandas as pd
import numpy as np
from tqdm.auto import tqdm

class BaseSorter:
    """Base class providing shared utilities for portfolio sorting."""
    def __init__(self, df, signal_col, signal_type, ret_cols):
        self.df = df.copy()
        self.signal_col = signal_col
        self.signal_type = signal_type  # 'tone' (directional) or 'intensity' (magnitude only)
        self.ret_cols = ret_cols

    def _calculate_turnover(self, portfolios_df, weight_col, ret_col):
        """Calculates rigorous turnover accounting for weight drift."""
        W = portfolios_df.pivot(index='Date', columns='Stkcd', values=weight_col).fillna(0)
        R = self.df.pivot(index='Date', columns='Stkcd', values=ret_col).fillna(0)
        R = R.reindex(index=W.index, columns=W.columns).fillna(0)

        port_ret = (W.shift(1) * R).sum(axis=1)
        W_drifted = W.shift(1).mul(1 + R).div(1 + port_ret, axis=0).fillna(0)
        return (W - W_drifted).abs().sum(axis=1) / 2.0

    def _calc_capped_vw_weights(self, df_leg, cap_weight=0.10):
        """Calculates Value-Weighted weights with a maximum cap per stock."""
        if df_leg.empty: return pd.Series(dtype=float)
        w = df_leg['MktCap_B'] / df_leg['MktCap_B'].sum()
        for _ in range(3):  # Iterate to distribute excess weights
            w = w.clip(upper=cap_weight)
            w = w / w.sum()
        return w

class PortfolioSorter(BaseSorter):
    """Top/Bottom N Sorter (Ke, Kelly, & Xiu, 2026)"""
    def __init__(self, df, signal_col, signal_type, ret_cols, top_n=50, q_thresh=0.70):
        super().__init__(df, signal_col, signal_type, ret_cols)
        self.top_n = top_n
        self.q_thresh = q_thresh

    def generate_portfolios(self):
        # 1. Base Tradability Filter
        base_mask = (
            self.df[self.signal_col].notna() &
            (self.df[self.signal_col] != 0) &
            self.df[self.ret_cols[0]].notna() &
            self.df['MktCap_B'].notna() &
            (self.df['Next_LimitStatus'] == 0)
        )
        df_tradable = self.df[base_mask].copy()

        # 2. Daily Sorting Logic
        def sort_daily(group):
            if len(group) < 2: return pd.DataFrame()

            q_high = group[self.signal_col].quantile(self.q_thresh)
            q_low  = group[self.signal_col].quantile(1.0 - self.q_thresh)

            if self.signal_type == 'tone':
                cond_long = (group[self.signal_col] > 0) & (group[self.signal_col] >= q_high)
                cond_short = (group[self.signal_col] < 0) & (group[self.signal_col] <= q_low)
            else:
                cond_long = (group[self.signal_col] > 0) & (group[self.signal_col] >= q_high)
                cond_short = (group[self.signal_col] > 0) & (group[self.signal_col] <= q_low)

            long_pool = group[cond_long].sort_values(self.signal_col, ascending=False)
            short_pool = group[cond_short].sort_values(self.signal_col, ascending=True)

            # Mutual Exclusivity Protection
            long_leg = long_pool.head(self.top_n).copy()
            short_pool = short_pool[~short_pool['Stkcd'].isin(long_leg['Stkcd'])]
            short_leg = short_pool.head(self.top_n).copy()

            if long_leg.empty or short_leg.empty: return pd.DataFrame()

            long_leg['Leg'], short_leg['Leg'] = 'Long', 'Short'
            return pd.concat([long_leg, short_leg])

        portfolios = df_tradable.groupby('Date', group_keys=False).apply(sort_daily)
        if portfolios.empty: raise ValueError(f"No valid data for {self.signal_col}!")

        # 3. Weight Allocation
        portfolios['W_EW'] = 1.0 / portfolios.groupby(['Date', 'Leg'])['Stkcd'].transform('count')
        vw_den = portfolios.groupby(['Date', 'Leg'])['MktCap_B'].transform('sum')
        portfolios['W_VW'] = portfolios['MktCap_B'] / vw_den

        # 4. Aggregate Returns & Turnover
        daily_returns = []
        for date, group in portfolios.groupby('Date'):
            day_res = {'Date': date}
            for leg in ['Long', 'Short']:
                leg_data = group[group['Leg'] == leg]
                if leg_data.empty: continue
                for r_col in self.ret_cols:
                    day_res[f'{leg}_EW_{r_col}'] = (leg_data['W_EW'] * leg_data[r_col]).sum()
                    day_res[f'{leg}_VW_{r_col}'] = (leg_data['W_VW'] * leg_data[r_col]).sum()
            daily_returns.append(day_res)

        df_port_ret = pd.DataFrame(daily_returns).set_index('Date').sort_index()

        # Calculate L-S Spread
        for w in ['EW', 'VW']:
            for r in self.ret_cols:
                if f'Long_{w}_{r}' in df_port_ret.columns and f'Short_{w}_{r}' in df_port_ret.columns:
                    df_port_ret[f'L_S_{w}_{r}'] = df_port_ret[f'Long_{w}_{r}'] - df_port_ret[f'Short_{w}_{r}']

        # Calculate Turnover
        for leg in ['Long', 'Short']:
            leg_df = portfolios[portfolios['Leg'] == leg]
            df_port_ret[f'{leg}_EW_Turnover'] = self._calculate_turnover(leg_df, 'W_EW', 'Next_ExRet_C2C')
            df_port_ret[f'{leg}_VW_Turnover'] = self._calculate_turnover(leg_df, 'W_VW', 'Next_ExRet_C2C')

        df_port_ret['L_S_EW_Turnover'] = (df_port_ret.get('Long_EW_Turnover', 0) + df_port_ret.get('Short_EW_Turnover', 0)) / 2.0
        df_port_ret['L_S_VW_Turnover'] = (df_port_ret.get('Long_VW_Turnover', 0) + df_port_ret.get('Short_VW_Turnover', 0)) / 2.0

        return df_port_ret
class DecileSorter(BaseSorter):
    """Decile Sorter (Top 10% vs Bottom 10%) with Capped VW"""
    def __init__(self, df, signal_col, signal_type, ret_cols, q_high=0.90, q_low=0.10, cap_weight=0.10):
        super().__init__(df, signal_col, signal_type, ret_cols)
        self.q_high = q_high
        self.q_low = q_low
        self.cap_weight = cap_weight

    def generate_portfolios(self):
        base_mask = (
            self.df[self.signal_col].notna() &
            (self.df[self.signal_col] != 0) &
            self.df[self.ret_cols[0]].notna() &
            self.df['MktCap_B'].notna() &
            (self.df['Next_LimitStatus'] == 0)
        )
        df_tradable = self.df[base_mask].copy()

        def sort_daily(group):
            if len(group) < 50: return pd.DataFrame() # Skip if active pool is too small

            thresh_high = group[self.signal_col].quantile(self.q_high)
            thresh_low  = group[self.signal_col].quantile(self.q_low)

            if self.signal_type == 'tone':
                cond_long = (group[self.signal_col] > 0) & (group[self.signal_col] >= thresh_high)
                cond_short = (group[self.signal_col] < 0) & (group[self.signal_col] <= thresh_low)
            else:
                cond_long = (group[self.signal_col] > 0) & (group[self.signal_col] >= thresh_high)
                cond_short = (group[self.signal_col] > 0) & (group[self.signal_col] <= thresh_low)

            long_leg, short_leg = group[cond_long].copy(), group[cond_short].copy()
            if long_leg.empty or short_leg.empty: return pd.DataFrame()

            long_leg['Leg'], short_leg['Leg'] = 'Long', 'Short'

            long_leg['W_EW'] = 1.0 / len(long_leg)
            short_leg['W_EW'] = 1.0 / len(short_leg)
            long_leg['W_VW'] = self._calc_capped_vw_weights(long_leg, self.cap_weight)
            short_leg['W_VW'] = self._calc_capped_vw_weights(short_leg, self.cap_weight)

            return pd.concat([long_leg, short_leg])

        portfolios = df_tradable.groupby('Date', group_keys=False).apply(sort_daily)
        if portfolios.empty: raise ValueError(f"No valid data for {self.signal_col}!")

        # Aggregate Returns & Turnover (Same logic as PortfolioSorter)
        daily_returns = []
        for date, group in portfolios.groupby('Date'):
            day_res = {'Date': date}
            for leg in ['Long', 'Short']:
                leg_data = group[group['Leg'] == leg]
                if leg_data.empty: continue
                for r_col in self.ret_cols:
                    day_res[f'{leg}_EW_{r_col}'] = (leg_data['W_EW'] * leg_data[r_col]).sum()
                    day_res[f'{leg}_VW_{r_col}'] = (leg_data['W_VW'] * leg_data[r_col]).sum()
            daily_returns.append(day_res)

        df_port_ret = pd.DataFrame(daily_returns).set_index('Date').sort_index()

        for w in ['EW', 'VW']:
            for r in self.ret_cols:
                if f'Long_{w}_{r}' in df_port_ret.columns and f'Short_{w}_{r}' in df_port_ret.columns:
                    df_port_ret[f'L_S_{w}_{r}'] = df_port_ret[f'Long_{w}_{r}'] - df_port_ret[f'Short_{w}_{r}']

        for leg in ['Long', 'Short']:
            leg_df = portfolios[portfolios['Leg'] == leg]
            df_port_ret[f'{leg}_EW_Turnover'] = self._calculate_turnover(leg_df, 'W_EW', 'Next_ExRet_C2C')
            df_port_ret[f'{leg}_VW_Turnover'] = self._calculate_turnover(leg_df, 'W_VW', 'Next_ExRet_C2C')

        df_port_ret['L_S_EW_Turnover'] = (df_port_ret.get('Long_EW_Turnover', 0) + df_port_ret.get('Short_EW_Turnover', 0)) / 2.0
        df_port_ret['L_S_VW_Turnover'] = (df_port_ret.get('Long_VW_Turnover', 0) + df_port_ret.get('Short_VW_Turnover', 0)) / 2.0

        return df_port_ret

print("========== 🔀 Step 3: Mechanism Analysis (Conditional Double Sorts) ==========")

class ConditionalDoubleSorter:
    """
    Conditional Double Sort Engine:
    Sorts into Quintiles based on Control, then Deciles (Top 10% vs Bot 10%) based on Target.
    """
    def __init__(self, df, ctrl_col, tgt_col, tgt_type='tone', q_c=5, q_high=0.90, q_low=0.10, cap_weight=0.10):
        self.df = df.copy()
        self.ctrl_col = ctrl_col
        self.tgt_col = tgt_col
        self.tgt_type = tgt_type
        self.q_c = q_c
        self.q_high = q_high
        self.q_low = q_low
        self.cap_weight = cap_weight

        # Log-transform highly skewed count/attention variables
        self.df['Control_Metric'] = np.log1p(self.df[self.ctrl_col]) if self.ctrl_col == 'Num_Questions' else self.df[self.ctrl_col]

    def _safe_qcut(self, x, q):
        """Safely computes quantiles by adding microscopic noise to prevent bin edge duplication."""
        if len(x) < q: return pd.Series(np.nan, index=x.index)
        np.random.seed(42)
        noise = np.random.uniform(0, 1e-8, size=len(x))
        return pd.qcut(x + noise, q, labels=False, duplicates='drop') + 1

    def _calc_capped_vw_ret(self, df_leg):
        """Calculates capped VW return for a specific portfolio leg."""
        if df_leg.empty: return np.nan
        w = df_leg['MktCap_B'] / df_leg['MktCap_B'].sum()
        for _ in range(3):
            w = w.clip(upper=self.cap_weight)
            w = w / w.sum()
        return (w * df_leg['Next_ExRet_Drift']).sum()

    def run(self):
        # Base Tradability Filter
        base_mask = (
            self.df[self.ctrl_col].notna() &
            self.df[self.tgt_col].notna() &
            self.df['Next_ExRet_Drift'].notna() &
            self.df['MktCap_B'].notna() &
            (self.df.get('Next_LimitStatus', 0) == 0)
        )
        df_tradable = self.df[base_mask].copy()

        daily_records = []
        for date, group in tqdm(df_tradable.groupby('Date'), leave=False, desc=f"{self.ctrl_col} -> {self.tgt_col}"):
            if len(group) < self.q_c * 10: continue # Ensure sufficient cross-sectional size

            group['Q_Ctrl'] = self._safe_qcut(group['Control_Metric'], self.q_c)
            group = group.dropna(subset=['Q_Ctrl'])

            for c_idx, sub_group in group.groupby('Q_Ctrl'):
                if len(sub_group) < 10: continue

                thresh_high = sub_group[self.tgt_col].quantile(self.q_high)
                thresh_low  = sub_group[self.tgt_col].quantile(self.q_low)

                # Strict semantic filtering
                if self.tgt_type == 'tone':
                    cond_long = (sub_group[self.tgt_col] > 0) & (sub_group[self.tgt_col] >= thresh_high)
                    cond_short = (sub_group[self.tgt_col] < 0) & (sub_group[self.tgt_col] <= thresh_low)
                else:
                    cond_long = (sub_group[self.tgt_col] > 0) & (sub_group[self.tgt_col] >= thresh_high)
                    cond_short = (sub_group[self.tgt_col] > 0) & (sub_group[self.tgt_col] <= thresh_low)

                long_leg, short_leg = sub_group[cond_long], sub_group[cond_short]

                l_ret = self._calc_capped_vw_ret(long_leg)
                s_ret = self._calc_capped_vw_ret(short_leg)

                daily_records.append({
                    'Date': date, 'Q_Ctrl': c_idx,
                    'L_Ret': l_ret, 'S_Ret': s_ret,
                    'L_S_Ret': l_ret - s_ret if pd.notna(l_ret) and pd.notna(s_ret) else np.nan,
                    'Long_N': len(long_leg), 'Short_N': len(short_leg)
                })

        ts_df = pd.DataFrame(daily_records)
        if ts_df.empty: return pd.DataFrame()

        # Aggregate and Evaluate
        results = []
        for c_idx in range(1, self.q_c + 1):
            c_data = ts_df[ts_df['Q_Ctrl'] == c_idx].set_index('Date')
            if c_data.empty: continue

            y_ls = c_data['L_S_Ret']
            ann_ret, sharpe, q5_a, q5_t = evaluate_strategy(y_ls, df_factors, q5_list)

            results.append({
                'Control Group': f"{self.ctrl_col} Q{c_idx}",
                'Long(N)': f"{c_data['Long_N'].mean():.1f}",
                'Short(N)': f"{c_data['Short_N'].mean():.1f}",
                'Long(bps)': f"{c_data['L_Ret'].mean() * 10000:.2f}",
                'Short(bps)': f"{c_data['S_Ret'].mean() * 10000:.2f}",
                'L-S (bps)': f"{y_ls.mean() * 10000:.2f}",
                'Ann. Ret (%)': f"{ann_ret:.1f}%" if pd.notna(ann_ret) else "-",
                'q5 α': format_alpha(q5_a, q5_t)
            })

        return pd.DataFrame(results)

print("✅ Conditional Double Sorter Engine Loaded.")
