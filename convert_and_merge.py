#!/usr/bin/env python3
import os
import pandas as pd

# ───────────────────────────────────────────────────────────────────────────────
# 1) Define how raw column‐prefixes map to your canonical ALLOWED_PROPERTIES.
#    The order here doesn’t affect prioritization—that’s driven by file order.
PROPERTY_PREFIXES = {
    'density':                  ['density'],
    'internal_energy':          ['internal_energy', 'u'],
    'enthalpy':                 ['enthalpy', 'h'],
    'specific_heat_capacity':   ['cp', 'ideal_heat_capacity'],
    'entropy':                  ['entropy'],
    'compressibility':          ['z', 'compressibility', 'compressibility_factor'],
    'fugacity_coefficient':     ['fugacity'],
    'saturation_pressure':      ['saturation_pressure', 'psat'],
    'saturation_temperature':   ['saturation_temperature', 'tsat'],
    'vapor_density':            ['vapor_density'],
    'liquid_density':           ['liquid_density'],
    'viscosity':                ['viscosity'],
    'thermal_conductivity':     ['conductivity', 'thermal_conductivity'],
    'surface_tension':          ['surface_tension', 'surface'],
    'molar_mass':               ['mol', 'molar_mass'],
    'critical_temperature':     ['critical_temperature', 'crit_temp'],
    'critical_pressure':        ['critical_pressure', 'crit_press'],
    'acentric_factor':          ['acentric'],
    'triple_point_temperature': ['triple_point_temperature', 'triple'],
    'triple_point_pressure':    ['triple_point_pressure']
}

# ───────────────────────────────────────────────────────────────────────────────
def normalize_and_rename(df: pd.DataFrame) -> pd.DataFrame:
    """
    2) Normalize raw column names and rename matching prefixes to canonical keys.

       a) We lowercase, replace spaces/units punctuation with underscores
          so all columns follow a uniform naming convention.
       b) We then scan each allowed property’s list of prefixes and
          pick the first matching raw column to rename.
    """
    # a) Normalize column names to lowercase + underscores
    df = df.rename(columns=lambda c:
        c.strip().lower()
         .replace(' ', '_')
         .replace('(', '')
         .replace(')', '')
         .replace('/', '_')
         .replace('.', '_')
    )

    # b) Build a map from raw column → canonical property
    rename_map = {}
    for prop, prefixes in PROPERTY_PREFIXES.items():
        for prefix in prefixes:
            # pick the first column that begins with this prefix
            matches = [c for c in df.columns if c.startswith(prefix)]
            if matches:
                rename_map[matches[0]] = prop
                break

    # apply the renames
    return df.rename(columns=rename_map)


# ───────────────────────────────────────────────────────────────────────────────
def process_excel_file(xlsx_path: str) -> pd.DataFrame:
    """
    3) Read every sheet (fluid) from one Excel file, normalize & rename it,
       and extract only the T, P, and desired property columns.

       This lets each source contribute its own property sets in the same
       canonical schema.
    """
    # read all sheets into a dict: { fluid_name: DataFrame }
    sheets = pd.read_excel(xlsx_path, sheet_name=None)
    frames = []

    for fluid_name, df in sheets.items():
        # normalize column names & rename to canonical props
        df = normalize_and_rename(df)

        # determine which columns we actually have: T, P, plus any properties
        keep = ['t', 'p'] + list(PROPERTY_PREFIXES.keys())
        keep = [c for c in keep if c in df.columns]

        # subset, add a fluid column, and collect
        sub = df[keep].copy()
        sub['fluid'] = fluid_name
        frames.append(sub)

    # concatenate all fluids from this one source
    return pd.concat(frames, ignore_index=True)


# ───────────────────────────────────────────────────────────────────────────────
def main():
    """
    4) Orchestrate the 3 data sources in order: CoolProp → PyKingas → ThermoPack.
       Later sources simply append additional fluids or properties.
    """
    inputs = [
        'coolpropdata.xlsx',
        'pykingasdata.xlsx',
        'thermopackdata.xlsx'
    ]
    parts = []

    for fn in inputs:
        if os.path.exists(fn):
            print(f"→ processing {fn} first")
            parts.append(process_excel_file(fn))
        else:
            print(f"⚠️  Warning: '{fn}' not found, skipping")

    # combine all sources into one master table
    master = pd.concat(parts, ignore_index=True)

    # drop any rows missing T or P, since interpolation needs both
    master = master.dropna(subset=['t', 'p'])

    # write out the unified CSV for your lookup module
    master.to_csv('master_fluid_table.csv', index=False)
    print(f"✅ Done! master_fluid_table.csv shape: {master.shape}")


if __name__ == '__main__':
    main()
