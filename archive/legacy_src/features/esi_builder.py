import numpy as np
import pandas as pd

def construct_esi_factor(df: pd.DataFrame, gamma: float = 5.0) -> pd.DataFrame:
    """
    Constructs the Effective Soothing Index (ESI) based on the non-linear
    interactions of Investor Tone, Manager Tone, Attention, and Substantiveness.
    """
    # Ensure no missing values in core components to prevent alignment failures
    mask_valid = df['Investor_Tone'].notna() & df['Manager_Tone'].notna() & df['Substantiveness_ML'].notna()

    # Extract valid samples to compute robust cross-sectional statistics
    valid_inv = df.loc[mask_valid, 'Investor_Tone']
    valid_mgr = df.loc[mask_valid, 'Manager_Tone']

    # --------------------------------------------------------------------------
    # Component 1: Attention-Amplified Demand Shock
    # --------------------------------------------------------------------------
    # Attention Amplifier (Normalized 0~1 to prevent extreme tail skewness)
    log_attn = np.log1p(df['Num_Questions'].fillna(0))
    attn_norm = log_attn / log_attn.max()

    # Base Shock: Retail Sentiment * (1 + 0.5 * Attention)
    base_shock = df['Investor_Tone'] * (1 + 0.5 * attn_norm)

    # --------------------------------------------------------------------------
    # Component 2: Quality-Gated & State-Dependent Soothing
    # --------------------------------------------------------------------------
    # Z-Score Standardization for Manager Tone
    z_mgr = (df['Manager_Tone'] - valid_mgr.mean()) / valid_mgr.std()

    # Trust Window Gate: Gaussian Kernel
    # Centered at the 30th percentile of panic, bandwidth = 0.8 std
    theta = valid_inv.quantile(0.30)
    sigma = valid_inv.std() * 0.8
    ir_kernel = np.exp(- ((df['Investor_Tone'] - theta)**2) / (2 * sigma**2))

    # Calculate Raw Managerial Impact
    mgr_impact = z_mgr * df['Substantiveness_ML'] * ir_kernel

    # Asymmetric Momentum Protection
    # Protects the momentum of hype stocks (Inv > 0) from being penalized by muted management
    cond_protect = (df['Investor_Tone'] > 0) & (mgr_impact < 0)
    mgr_impact.loc[cond_protect] = 0

    # --------------------------------------------------------------------------
    # Final Assembly
    # --------------------------------------------------------------------------
    col_name = f'ESI_Gamma_{gamma}'
    df[col_name] = base_shock + gamma * mgr_impact

    print(f"    ✅ {col_name} successfully constructed and merged!")
    return df