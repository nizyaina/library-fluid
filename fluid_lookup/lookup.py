#!/usr/bin/env python3
import glob
import pandas as pd

# 1) Convert every sheet in each Excel workbook into per‐sheet CSV
sources = {
    "coolprop":   "coolpropdata.xlsx",
    "thermopack": "thermopackdata.xlsx",
    "pykingas":   "pykingasdata.xlsx",
}

for src, xlsx in sources.items():
    xls = pd.ExcelFile(xlsx)
    for sheet in xls.sheet_names:
        df = xls.parse(sheet_name=sheet)
        df["source"] = src
        df["fluid"]  = sheet[:31]
        fn = f"{src}_{sheet.replace(' ', '_')}.csv"
        df.to_csv(fn, index=False)

# 2) Merge all those CSVs into a single DataFrame
csv_files = glob.glob("*_*.csv")
master = pd.concat([pd.read_csv(f, low_memory=False) for f in csv_files],
                   ignore_index=True)

# 3) (Optional) normalize column names
master.columns = [
    c.strip()
     .lower()
     .replace(" ", "_")
     .replace("[", "")
     .replace("]", "")
     .replace("(", "")
     .replace(")", "")
    for c in master.columns
]

# 4) rename temperature and pressure
def find_col(kw):
    for c in master.columns:
        if kw in c:
            return c
    raise KeyError(kw)

master = master.rename(columns={
    find_col("temp"):  "t",
    find_col("press"): "p",
})

# ── NEW: detect whatever Cp column exists and rename it to "cp" ──
cp_candidates = [c for c in master.columns if "cp" in c and c not in ("cp0","cp1")]
if cp_candidates:
    master = master.rename(columns={cp_candidates[0]: "cp"})

# 5) Write your master table (complete, no trimming)
master.to_csv("master_fluid_table.csv", index=False)
print("Done! Master table shape:", master.shape)
