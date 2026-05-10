import pandas as pd
import numpy as np
import os

# Create directories
os.makedirs("data", exist_ok=True)

print("Loading datasets...")

# Update paths to look in data folder
file_swamp = "./data/nsw-2007-2025-wq-swamp-data-qaqc-basic.xlsx"
file_coast = "./data/nsw-coast-2016-2021-wq-data-for-rci.xlsx"
file_inland = "./data/nsw-inland-2016-2021-wq-data-for-rci.xlsx"

# 🔹 Load datasets
df_swamp = pd.read_excel(file_swamp, sheet_name='2007_2025')
df_coast = pd.read_excel(file_coast, sheet_name='2016 to 2021 data')

inland_sheets = pd.read_excel(file_inland, sheet_name=None)
df_inland = pd.concat([df for name, df in inland_sheets.items() if "Station" not in name and "target" not in name], ignore_index=True)

# 🔹 Fix Swamp Timestamps and Pivot
df_swamp['timestamp'] = pd.to_datetime(df_swamp['SampleDate'].astype(str) + ' ' + df_swamp['Time'].astype(str), format='mixed', errors='coerce')

# 🔥 FIX: Drop exact duplicates before pivoting to prevent index errors
df_swamp = df_swamp.drop_duplicates(subset=['timestamp', 'StationId', 'Parameter'])

df_swamp = df_swamp.pivot_table(
    index=['timestamp', 'StationId'], 
    columns='Parameter', 
    values='ResultValue', 
    aggfunc='first'
).reset_index()

# 🔥 FIX: Ensure column names are unique and strings
df_swamp.columns = [str(col).strip() for col in df_swamp.columns]
df_swamp = df_swamp.loc[:, ~df_swamp.columns.duplicated()].copy()

# 🔹 Add Location IDs
df_swamp['location_id'] = "swamp"
df_coast['location_id'] = "coast"
df_inland['location_id'] = "inland"

def rename_water_columns(df):
    cols = df.columns.astype(str).str.lower()
    rename_dict = {}
    for original, lower_col in zip(df.columns, cols):
        if 'date time' in lower_col or 'timestamp' in lower_col: 
            rename_dict[original] = 'timestamp'
        elif 'ph' in lower_col: 
            rename_dict[original] = 'ph'
        elif 'temperature' in lower_col: 
            rename_dict[original] = 'temperature'
        elif 'oxygen' in lower_col: 
            rename_dict[original] = 'do'
        elif 'turbidity' in lower_col: 
            rename_dict[original] = 'turbidity'
        elif 'conductivity' in lower_col or 'salinity' in lower_col: 
            rename_dict[original] = 'salinity'
    
    df = df.rename(columns=rename_dict)
    return df.loc[:, ~df.columns.duplicated()].copy()

df_swamp = rename_water_columns(df_swamp)
df_coast = rename_water_columns(df_coast)
df_inland = rename_water_columns(df_inland)

# 🔹 Combine all
print("Merging datasets...")
df = pd.concat([df_swamp, df_coast, df_inland], ignore_index=True)

# 🔹 Keep only needed columns
cols_needed = ['timestamp', 'location_id', 'ph', 'temperature', 'do', 'turbidity', 'salinity']
df = df[[c for c in cols_needed if c in df.columns]].copy()

# 🔹 Clean and Sort
df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
df = df.dropna(subset=['timestamp']).sort_values(by=['location_id', 'timestamp'])

# 🔹 Numeric conversion and Interpolation
numeric_cols = ['ph','temperature','do','turbidity','salinity']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')
    df[col] = df.groupby('location_id', group_keys=False)[col].apply(
        lambda x: x.interpolate(method='linear').ffill().bfill()
    )
    df[col] = df[col].rolling(window=5, min_periods=1).mean()

# 🔹 Save to data folder
df.to_csv("data/final_water_data.csv", index=False)
print("✅ Data preparation COMPLETE. File saved as data/final_water_data.csv")