# fluid_lookup/lookup.py

import pandas as pd
import numpy as np
from scipy.interpolate import RegularGridInterpolator

class FluidLibrary:
    """
    FluidLibrary provides interpolation-based lookup for fluid properties.
    Uses SciPy’s RegularGridInterpolator over a T×P grid,
    supports case-insensitive names, simple synonyms, and only exposes
    a curated list of user-relevant properties.
    """

    # 1) Define exactly which properties the user should see.
    #    These must match column names (normalized) in master_fluid_table.csv.
    ALLOWED_PROPERTIES = {
        'density',                 # kg/m³
        'internal_energy',         # J/kg
        'enthalpy',                # J/kg
        'specific_heat_capacity',  # J/(kg·K)
        'entropy',                 # J/(kg·K)
        'compressibility',         # Z factor (–)
        'fugacity_coefficient',    # – 
        'saturation_pressure',     # Pa
        'saturation_temperature',  # K
        'vapor_density',           # kg/m³
        'liquid_density',          # kg/m³
        'viscosity',               # Pa·s
        'thermal_conductivity',    # W/(m·K)
        'surface_tension',         # N/m
        'molar_mass',              # kg/mol
        'critical_temperature',    # K
        'critical_pressure',       # Pa
        'acentric_factor',         # – 
        'triple_point_temperature',# K
        'triple_point_pressure'    # Pa
    }

    # 2) Simple synonyms so users can type “H2O” or “water” interchangeably
    SYNONYMS = {
        'h2o': 'water',
        'water': 'water',
        # add others as needed, e.g. 'steam':'water', 'co2':'carbon_dioxide'
    }

    def __init__(self, csv_path="master_fluid_table.csv"):
        # — Load raw table —
        df = pd.read_csv(csv_path, low_memory=False)

        # — Normalize column names once —
        df.columns = [
            c.strip().lower()
             .replace(' ', '_')
             .replace('(', '')
             .replace(')', '')
             .replace('/', '_')
             .replace('.', '_')
            for c in df.columns
        ]
        self.df = df
        self._cache = {}  # cache interpolators

        # — Build fluid name map —
        fluids = sorted(df['fluid'].unique())
        # map lowercase → canonical
        self._aliases = {f.lower(): f for f in fluids}
        # inject synonyms
        for alias, canon in self.SYNONYMS.items():
            self._aliases[alias.lower()] = canon

    def _canonical_fluid(self, fluid):
        """Map user input (case-insensitive) to canonical fluid name."""
        key = fluid.strip().lower()
        if key not in self._aliases:
            raise KeyError(f"No such fluid '{fluid}'")
        return self._aliases[key]

    def available_fluids(self):
        """Return the list of supported fluid names."""
        return sorted(set(self._aliases.values()))

    def available_properties(self, fluid):
        """
        Return the subset of ALLOWED_PROPERTIES that are present
        in the loaded dataframe for this fluid.
        """
        canon = self._canonical_fluid(fluid)
        # just filter by presence in columns
        return sorted(p for p in self.ALLOWED_PROPERTIES if p in self.df.columns)

    def _build_interp(self, fluid, prop):
        """
        Build (and cache) a RegularGridInterpolator for a given
        fluid/prop over its T,P grid. Returns None if insufficient grid.
        """
        key = (fluid, prop)
        if key in self._cache:
            return self._cache[key]

        # filter to that fluid & property, drop missing
        grp = (self.df[self.df['fluid'] == fluid]
               .dropna(subset=['t', 'p', prop]))

        Ts = np.sort(grp['t'].unique())
        Ps = np.sort(grp['p'].unique())

        # need at least 2×2 grid to interpolate
        if len(Ts) < 2 or len(Ps) < 2:
            self._cache[key] = None
            return None

        # pivot to 2D array indexed by T,P
        pivot = (grp.set_index(['t', 'p'])[prop]
                 .unstack('p')
                 .reindex(index=Ts, columns=Ps)
                 .astype(float))

        interp = RegularGridInterpolator(
            (Ts, Ps),
            pivot.values,
            bounds_error=False,   # out-of-bounds → fill_value
            fill_value=np.nan
        )
        self._cache[key] = interp
        return interp

    def query(self, fluid, T, P, props=None):
        """
        Interpolate the requested properties at (T [K], P [Pa]).
        Returns a dict: { prop_name: float_value | 'n/a' }.
        """
        canon = self._canonical_fluid(fluid)

        if props is None:
            props = self.available_properties(canon)
        else:
            # sanitize requested list
            props = [p for p in props if p in self.ALLOWED_PROPERTIES]

        pt = (float(T), float(P))
        out = {}

        for prop in props:
            fn = self._build_interp(canon, prop)
            if fn is None:
                out[prop] = 'n/a'
            else:
                val = fn(pt)
                out[prop] = (float(val) if not np.isnan(val) else 'n/a')

        return out
