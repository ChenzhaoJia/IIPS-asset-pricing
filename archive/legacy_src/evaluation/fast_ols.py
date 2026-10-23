import numpy as np
from tqdm.auto import tqdm

def calculate_residuals_fast(df, y_col, x_cols, res_col_name):
    """
    Ultra-fast OLS residual calculator using NumPy lstsq.
    Computes rolling/expanding residuals grouped by Stkcd to extract pure Alpha.
    """
    res_array = np.full(len(df), np.nan, dtype=np.float32)

    y_data = df[y_col].values
    x_data = df[x_cols].values

    # 增加截距项 (Alpha)
    x_data_with_const = np.column_stack([np.ones(len(df)), x_data])

    # 获取每个股票的索引
    grouped_indices = df.groupby('Stkcd').indices

    for stkcd, idx in tqdm(grouped_indices.items(), desc=f"Calculating {res_col_name}", leave=False):
        if len(idx) < 30:
            continue # 要求至少有 30 个交易日的数据才能跑 OLS

        y_g = y_data[idx]
        x_g = x_data_with_const[idx]

        # 过滤掉包含 NaN 的行
        valid_mask = ~np.isnan(y_g) & ~np.isnan(x_g).any(axis=1)
        if valid_mask.sum() < 30:
            continue

        y_v = y_g[valid_mask]
        x_v = x_g[valid_mask]

        try:
            # np.linalg.lstsq 极限速度求解 Beta
            beta, _, _, _ = np.linalg.lstsq(x_v, y_v, rcond=None)
            # 计算样本内残差 (即 ARet)
            resid = y_v - x_v.dot(beta)
            res_array[idx[valid_mask]] = resid.astype(np.float32)
        except Exception:
            pass

    df[res_col_name] = res_array
    return df