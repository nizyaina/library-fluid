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
        print(f"Wrote {fn}")

# 2) Merge all those CSVs into a single DataFrame
csv_files = glob.glob("*_*.csv")
master = pd.concat([pd.read_csv(f) for f in csv_files], ignore_index=True)

# 3) (Optional) Normalize column names
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

# 4) (Optional) Detect & rename your key axes
def find_col(kw):
    for c in master.columns:
        if kw in c:
            return c
    raise KeyError(kw)

rename_map = {
    find_col("temp"):     "T",
    find_col("press"):    "P",
}
master = master.rename(columns=rename_map)

# 5) **No trimming** — keep every column from the merge
master.to_csv("master_fluid_table.csv", index=False)
print("Done! Master table shape:", master.shape)
