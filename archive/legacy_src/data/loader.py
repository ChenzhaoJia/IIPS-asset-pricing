import os
import glob
from pathlib import Path
import pandas as pd
import numpy as np
import warnings
from tqdm.auto import tqdm
import sys


import gc
import pandas as pd

def load_optimized_parquet(keyword, usecols=None, rename_dict=None):
    """
    极限省内存读取器：读入 -> 降维 -> 清理
    支持穿透匹配【文件夹名称】与【文件名称】
    """
    # 获取 raw 目录下所有的 parquet 文件
    all_files = list(PATHS['raw'].rglob("*.parquet"))

    # 只要文件路径（包含外层文件夹名）中含有 keyword，就选中它
    files = [f for f in all_files if keyword in str(f)]

    if not files:
        print(f"   [警告] 未在任何路径中找到包含 '{keyword}' 的文件。")
        return pd.DataFrame()

    df_list = []
    for f in files:
        try:
            # 利用 Parquet 的列裁剪特性，按需加载，极省内存
            df = pd.read_parquet(f, columns=usecols)

            if rename_dict:
                df = df.rename(columns=rename_dict)

            # 1. 内存优化：日期转 datetime
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

            # 2. 内存优化：股票代码转 int32 (消灭极占内存的 String)
            if 'Stkcd' in df.columns:
                df['Stkcd'] = pd.to_numeric(df['Stkcd'], errors='coerce')
                df = df.dropna(subset=['Stkcd'])
                df['Stkcd'] = df['Stkcd'].astype('int32') # 用 int32 关联，速度极快

            # 3. 内存优化：浮点数降维 float64 -> float32
            float_cols = df.select_dtypes(include=['float64']).columns
            df[float_cols] = df[float_cols].astype('float32')

            df_list.append(df)

        except ValueError:
            # 静默拦截 CSMAR 命名混乱导致的脏文件 (例如包含LimitStatus但名字叫TRD_Dalyr的文件)
            pass
        except Exception as e:
            print(f"   [报错] 读取 {f.name} 时出错: {e}")

    if not df_list:
        return pd.DataFrame()

    df_concat = pd.concat(df_list, ignore_index=True)
    del df_list
    gc.collect() # 回收临时列表

    return df_concat

def safe_merge(df_left, df_right, on_keys, how='left'):
    """
    🛡️ 安全合并函数：防止重复运行产生 _x, _y 后缀。
    逻辑：在合并前，剔除左表中与右表同名的非键列，实现"覆盖更新"。
    """
    if df_right.empty: return df_left
    overlap_cols = [c for c in df_right.columns if c in df_left.columns and c not in on_keys]
    if overlap_cols:
        df_left = df_left.drop(columns=overlap_cols)
    return df_left.merge(df_right, on=on_keys, how=how)


def clean_and_convert_csmar(file_path):
    """
    清洗单个 CSMAR 文件并转换为 Parquet。
    处理逻辑：
    1. 跳过冗余的表头（中文名和单位行，通常在第2和第3行）。
    2. 统一识别并格式化股票代码列为 6 位字符串。
    """
    file_ext = file_path.suffix.lower()

    try:
        # 1. 读取数据：CSMAR 标准格式跳过 index 为 1 和 2 的行 (即 Excel 的第 2、3 行)
        if file_ext == '.xlsx':
            df = pd.read_excel(file_path, header=0, skiprows=[1, 2])
        elif file_ext == '.csv':
            # 注意：部分 CSV 可能有编码问题，如果报错可尝试 encoding='gbk'
            df = pd.read_csv(file_path, header=0, skiprows=[1, 2], low_memory=False)
        else:
            return False, "不支持的格式"


        col_mapping = {
            'Symbol': 'Stkcd',
            '证券代码': 'Stkcd',
            'stkcd': 'Stkcd',
            'symbol': 'Stkcd'
        }
        df = df.rename(columns=col_mapping)


        if 'Stkcd' in df.columns:

            df['Stkcd'] = pd.to_numeric(df['Stkcd'], errors='coerce')
            df = df.dropna(subset=['Stkcd'])
            df['Stkcd'] = df['Stkcd'].astype(int).astype(str).str.zfill(6)


        parquet_path = file_path.with_suffix('.parquet')
        df.to_parquet(parquet_path, index=False)

        return True, parquet_path.name

    except Exception as e:
        return False, str(e)

def batch_convert_raw_data(raw_dir):
    """
    遍历 raw 目录下的所有子文件夹，将所有 excel 和 csv 批量转换为 parquet。
    """
    print("========== ⚙️ 开始扫描并转换原始数据 ==========")

    # 查找所有的 .xlsx 和 .csv 文件 (递归)
    all_files = list(raw_dir.rglob("*.xlsx")) + list(raw_dir.rglob("*.csv"))

    # 过滤掉以 ~$ 开头的 Excel 临时缓存文件
    all_files = [f for f in all_files if not f.name.startswith("~$")]

    if not all_files:
        print(" -> ⚠️ 在 raw 目录下未找到任何 .xlsx 或 .csv 文件，请检查数据是否已放入。")
        return

    success_count = 0
    skip_count = 0
    fail_count = 0

    # 使用 tqdm 显示进度条
    for file_path in tqdm(all_files, desc="Converting to Parquet"):
        parquet_path = file_path.with_suffix('.parquet')

        # 智能缓存：如果 parquet 已经存在，则跳过，节省时间
        if parquet_path.exists():
            skip_count += 1
            continue

        is_success, msg = clean_and_convert_csmar(file_path)

        if is_success:
            success_count += 1
        else:
            fail_count += 1
            print(f"\n[失败] {file_path.name}: {msg}")

    print("\n========== 📊 转换任务摘要 ==========")
    print(f"总文件数: {len(all_files)}")
    print(f"✅ 成功转换: {success_count}")
    print(f"⏩ 跳过(已存在): {skip_count}")
    print(f"❌ 转换失败: {fail_count}")
    print("=======================================")
    
def safe_load_fin(keyword, col_mapping):
    """自适应列名加载器，忽略缺失列，自动转换大小写别名，强制匹配文件夹中文名"""
    all_files = list(PATHS['raw'].rglob("*.parquet"))
    files = [f for f in all_files if keyword in str(f)]

    if not files:
        print(f"      [警告] 未在任何路径中找到包含 '{keyword}' 的 Parquet 文件。")
        return pd.DataFrame()

    df_list = []
    for f in files:
        try:
            df = pd.read_parquet(f)
            df.columns = [str(c).lower() for c in df.columns]

            rename_dict = {}
            for target_col, possible_names in col_mapping.items():
                for name in possible_names:
                    if name.lower() in df.columns:
                        rename_dict[name.lower()] = target_col
                        break

            df = df[list(rename_dict.keys())].rename(columns=rename_dict)

            if 'Stkcd' in df.columns:
                df['Stkcd'] = pd.to_numeric(df['Stkcd'], errors='coerce')
                df = df.dropna(subset=['Stkcd'])
                df['Stkcd'] = df['Stkcd'].astype('int32')
                df_list.append(df)
        except Exception as e:
            print(f"      [警告] 读取 {f.name} 时出错: {e}")

    if not df_list: return pd.DataFrame()
    return pd.concat(df_list, ignore_index=True)
    
def map_time_series_factor(keyword, date_col_possible, rename_dict=None):
    files = list(PATHS['raw'].rglob(f"*{keyword}*.parquet"))
    if not files: return
    try:
        df_fac = pd.read_parquet(files[0])
        date_col = next((c for c in df_fac.columns if str(c).lower() in [dc.lower() for dc in date_col_possible]), None)
        if not date_col: return

        market_col = next((c for c in df_fac.columns if str(c).lower() in ['markettypeid', 'markettype']), None)
        if market_col:
            available_types = df_fac[market_col].astype(str).unique()
            if 'P9714' in available_types: df_fac = df_fac[df_fac[market_col].astype(str) == 'P9714']
            elif 'P9709' in available_types: df_fac = df_fac[df_fac[market_col].astype(str) == 'P9709']
            elif 'P9706' in available_types: df_fac = df_fac[df_fac[market_col].astype(str) == 'P9706']

        if rename_dict:
            cols_to_keep = [date_col] + [c for c in rename_dict.keys() if c in df_fac.columns]
            df_fac = df_fac[cols_to_keep].rename(columns=rename_dict)

        # 【防 1970 纳秒漏洞】：强制将日期列转为字符型再解析
        parsed_dates = pd.to_datetime(df_fac[date_col].astype(str), errors='coerce')
        df_fac['date_hash'] = (parsed_dates.dt.year * 10000 +
                               parsed_dates.dt.month * 100 +
                               parsed_dates.dt.day).astype('int32')
        
        df_fac = df_fac.dropna(subset=['date_hash']).drop_duplicates(subset=['date_hash']).set_index('date_hash')

        for col in df_fac.columns:
            if col != date_col and col != 'date_hash':
                df_spine[col] = spine_date_hash.map(df_fac[col]).astype('float32')
        print(f"    ✅ {keyword} 因子映射完成。")
    except Exception as e: 
        print(f"    ❌ {keyword} 映射出错: {e}")
