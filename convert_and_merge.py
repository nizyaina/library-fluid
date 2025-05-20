import glob
import pandas as pd
import re

# 1) Explode each source to CSV … (same as before) …
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

# 2) Merge
csv_files = glob.glob("*_*.csv")
master = pd.concat((pd.read_csv(f, low_memory=False) for f in csv_files),
                   ignore_index=True)

# 3) Normalize names (lowercase, underscores, strip parens/brackets)
master.columns = [
    c.strip().lower()
      .replace(" ", "_")
      .replace("(", "").replace(")", "")
      .replace("[", "").replace("]", "")
      .replace("/", "_")
      .replace(".", "_")
    for c in master.columns
]

# 4) Rename T & P
def findcol(kw):
    for c in master.columns:
        if kw in c:
            return c
    raise KeyError(kw)

master = master.rename(columns={
    findcol("temp"): "t",
    findcol("press"):"p",
})

# 5) Strip any trailing unit‐suffix from *every* other column
def strip_unit(col):
    # matches: underscore + letters/numbers until end
    return re.sub(r'_[a-z0-9]+(?:_[a-z0-9]+)*$', '', col)

core = {"fluid","source","t","p"}
new_cols = []
for c in master.columns:
    if c in core:
        new_cols.append(c)
    else:
        new_cols.append(strip_unit(c))
master.columns = new_cols

# 6) Save
master.to_csv("master_fluid_table.csv", index=False)
print("Done! master_fluid_table.csv shape:", master.shape)

