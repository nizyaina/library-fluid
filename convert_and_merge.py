import glob
import pandas as pd

# 1) Explode each source into per‐sheet CSVs
sources = {
    "coolprop":   "coolpropdata.xlsx",
    "thermopack": "thermopackdata.xlsx",
    "pykingas":   "pykingasdata.xlsx",
}
for src, xlsx in sources.items():
    xls = pd.ExcelFile(xlsx)
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        df["source"] = src
        df["fluid"]  = sheet[:31]
        df.to_csv(f"{src}_{sheet.replace(' ', '_')}.csv", index=False)

# 2) Merge all CSVs
csv_files = glob.glob("*_*.csv")
master = pd.concat((pd.read_csv(f, low_memory=False) for f in csv_files),
                   ignore_index=True)

# 3) Normalize column names
master.columns = [
    c.strip().lower()
      .replace(" ", "_")
      .replace("(", "").replace(")", "")
      .replace("[", "").replace("]", "")
      .replace("/", "_")
      .replace(".", "_")
    for c in master.columns
]

# 4) Rename temperature & pressure to `t` and `p`
def findcol(kw):
    for c in master.columns:
        if kw in c:
            return c
    raise KeyError(f"No column containing '{kw}' found")

master = master.rename(columns={
    findcol("temp"):  "t",
    findcol("press"): "p",
})

# 5) Save the unified lookup table
master.to_csv("master_fluid_table.csv", index=False)
print("Done! master_fluid_table.csv shape:", master.shape)
