#!/usr/bin/env python3
import os
import pandas as pd

# 1) Canonical property keys and how to detect them in raw column prefixes
PROPERTY_PREFIXES = {
    'density':                  ['density'],
    'internal_energy':          ['internal_energy', 'u'],
    'enthalpy':                 ['enthalpy', 'h'],
    'specific_heat_capacity':   ['cp', 'ideal_heat_capacity'],
    'entropy':                  ['entropy'],
    'compressibility':          ['z', 'compressibility'],
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


def normalize_and_rename(df: pd.DataFrame) -> pd.DataFrame:
    """
    1) Normalize all column names (lower, underscores, strip punctuation).
    2) Detect and rename:
       - any column containing 'temp' → 't'
       - any column containing 'press' → 'p'
    3) Map each property column to its canonical key via PROPERTY_PREFIXES.
    """
    # a) Normalize raw column names
    df.columns = [
        c.strip().lower()
         .replace(' ', '_')
         .replace('(', '').replace(')', '')
         .replace('[', '').replace(']', '')
         .replace('/', '_')
         .replace('.', '_')
        for c in df.columns
    ]

    # b) Rename temperature → 't'
    for c in df.columns:
        if c in ("t_k", "temperature") or "temp" in c:
            df = df.rename(columns={c: 't'})
            break

    # c) Rename pressure → 'p'
    for c in df.columns:
        if c in ("p_pa", "pressure") or "press" in c:'press' in c:
            df = df.rename(columns={c: 'p'})
            break

    # d) Map other properties via prefixes
    rename_map = {}
    for key, prefixes in PROPERTY_PREFIXES.items():
        for pre in prefixes:
            matches = [c for c in df.columns if c.startswith(pre)]
            if matches:
                rename_map[matches[0]] = key
                break
    return df.rename(columns=rename_map)


def process_excel_file(xlsx_path: str) -> pd.DataFrame:
    """
    Read every sheet (fluid) from the Excel file, normalize & rename columns,
    and keep only t, p, and your canonical properties.
    """
    sheets = pd.read_excel(xlsx_path, sheet_name=None)
    frames = []
    for fluid_name, df in sheets.items():
        df = normalize_and_rename(df)
        keep = ['t', 'p'] + list(PROPERTY_PREFIXES.keys())
        cols = [c for c in keep if c in df.columns]
        sub = df[cols].copy()
        sub['fluid'] = fluid_name
        frames.append(sub)
    return pd.concat(frames, ignore_index=True)


def main():
    inputs = ['coolpropdata.xlsx', 'pykingasdata.xlsx', 'thermopackdata.xlsx']
    parts = []
    for fn in inputs:
        if os.path.exists(fn):
            print(f"→ processing {fn}")
            parts.append(process_excel_file(fn))
        else:
            print(f"⚠️  '{fn}' not found, skipping")

    master = pd.concat(parts, ignore_index=True)
    # Now that 't' and 'p' columns exist, drop rows missing either
    master = master.dropna(subset=['t', 'p'])
    # Write the unified master table
    master.to_csv('master_fluid_table.csv', index=False)
    print(f"✅ Done! master_fluid_table.csv shape: {master.shape}")


if __name__ == '__main__':
    main()
