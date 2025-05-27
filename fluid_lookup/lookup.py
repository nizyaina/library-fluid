import pandas as pd
import numpy as np
from scipy.interpolate import RegularGridInterpolator

class FluidLibrary:
    """
    FluidLibrary provides interpolation-based lookup for fluid properties.

    Key features:
      1. Case-insensitive fluid names + simple synonyms (e.g. “H2O” → “water”).
      2. Only exposes the properties you specified; everything else returns 'n/a'.
      3. Recognizes column names with units (e.g., 'density_kg_m3') by matching
         prefixes against ALLOWED_PROPERTIES.
      4. Builds & caches a SciPy RegularGridInterpolator for each (fluid, property).
      5. Enforces that queried T/P lie within the data bounds, raising ValueError otherwise.
      6. Query API returns a Python dict of {property: value or 'n/a'}.
    """

    # 1) Define exactly which properties you want visible to users
    ALLOWED_PROPERTIES = {
        'density',
        'internal_energy',
        'enthalpy',
        'specific_heat_capacity',
        'entropy',
        'compressibility',
        'fugacity_coefficient',
        'saturation_pressure',
        'saturation_temperature',
        'vapor_density',
        'liquid_density',
        'viscosity',
        'thermal_conductivity',
        'surface_tension',
        'molar_mass',
        'critical_temperature',
        'critical_pressure',
        'acentric_factor',
        'triple_point_temperature',
        'triple_point_pressure'
    }

    # 2) Simple name‐mapping so users can type “H2O”, “water”, etc.
    SYNONYMS = {
        'h2o': 'water',
        'water': 'water',
        # add more as needed
    }

    def __init__(self, csv_path="master_fluid_table.csv"):
        # 3) Load the merged CSV and normalize its column names
        df = pd.read_csv(csv_path, low_memory=False)
        df.columns = [
            c.strip().lower()
             .replace(' ', '_')
             .replace('(', '').replace(')', '')
             .replace('/', '_')
             .replace('.', '_')
            for c in df.columns
        ]
        self.df = df
        self._cache = {}

        # 4) Map canonical column names for each allowed property
        #    Match exact prop or prop_*
        self._prop_map = {}
        for prop in self.ALLOWED_PROPERTIES:
            matches = [c for c in df.columns if c == prop or c.startswith(prop + '_')]
            if matches:
                self._prop_map[prop] = matches[0]

        # 5) Build a mapping of user‐typed name → canonical fluid name
        fluids = sorted(self.df['fluid'].unique())
        self._aliases = {f.lower(): f for f in fluids}
        for alias, canon in self.SYNONYMS.items():
            self._aliases[alias.lower()] = canon

        # 6) Precompute valid T/P bounds per fluid for range‐checking
        self._ranges = {}
        for f in self.available_fluids():
            sub = self.df[self.df['fluid'] == f]
            self._ranges[f] = {
                't_min': sub['t'].min(),
                't_max': sub['t'].max(),
                'p_min': sub['p'].min(),
                'p_max': sub['p'].max(),
            }

    def _canonical_fluid(self, fluid):
        """
        Turn user input into the standardized fluid name stored in the CSV.
        """
        key = fluid.strip().lower()
        if key not in self._aliases:
            raise KeyError(f"No such fluid '{fluid}'")
        return self._aliases[key]

    def available_fluids(self):
        """Return the list of standardized fluid names."""
        return sorted(set(self._aliases.values()))

    def available_properties(self, fluid):
        """
        Return only the subset of ALLOWED_PROPERTIES that actually
        exist as columns in the CSV (units-agnostic matching).
        """
        self._canonical_fluid(fluid)
        return sorted(self._prop_map.keys())

    def _build_interp(self, fluid, prop):
        """
        Build or retrieve a RegularGridInterpolator for the given fluid & property.
        """
        key = (fluid, prop)
        if key in self._cache:
            return self._cache[key]

        col = self._prop_map.get(prop)
        if col is None:
            self._cache[key] = None
            return None

        grp = (
            self.df[self.df['fluid'] == fluid]
               .dropna(subset=['t', 'p', col])
        )
        Ts = np.sort(grp['t'].unique())
        Ps = np.sort(grp['p'].unique())
        if len(Ts) < 2 or len(Ps) < 2:
            self._cache[key] = None
            return None

        pivot = (
            grp.set_index(['t', 'p'])[col]
               .unstack('p')
               .reindex(index=Ts, columns=Ps)
               .astype(float)
        )
        interp = RegularGridInterpolator(
            (Ts, Ps), pivot.values,
            bounds_error=False,
            fill_value=np.nan
        )
        self._cache[key] = interp
        return interp

    def query(self, fluid, T, P, props=None):
        """
        Query one or more properties at (T, P).

        Raises ValueError if (T,P) lies outside the data bounds for that fluid.
        Returns dict {property: float value or 'n/a'}.
        """
        canon = self._canonical_fluid(fluid)

        # Enforce in‐range checks
        r = self._ranges[canon]
        if not (r['t_min'] <= T <= r['t_max']):
            raise ValueError(
                f"Temperature {T} K is outside valid range "
                f"{r['t_min']}–{r['t_max']} K for {canon}"
            )
        if not (r['p_min'] <= P <= r['p_max']):
            raise ValueError(
                f"Pressure {P} Pa is outside valid range "
                f"{r['p_min']}–{r['p_max']} Pa for {canon}"
            )

        # Determine props to query
        if props is None:
            props = list(self._prop_map.keys())
        props = [p for p in props if p in self._prop_map]

        pt = (float(T), float(P))
        out = {}
        for prop in props:
            fn = self._build_interp(canon, prop)
            if fn is None:
                out[prop] = 'n/a'
            else:
                val = fn(pt)
                out[prop] = float(val) if not np.isnan(val) else 'n/a'
        return out
