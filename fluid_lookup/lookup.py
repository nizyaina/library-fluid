import pandas as pd
import numpy as np
from scipy.interpolate import RegularGridInterpolator

class FluidLibrary:
    def __init__(self, csv_path="master_fluid_table.csv"):
        df = pd.read_csv(csv_path, low_memory=False)
        df.columns = [
            c.strip().lower()
              .replace(" ", "_")
              .replace("(", "").replace(")", "")
              .replace("/", "_")
              .replace(".", "_")
            for c in df.columns
        ]
        self.df = df
        self._cache = {}

    def available_fluids(self):
        return sorted(self.df['fluid'].unique())

    def available_properties(self, fluid):
        if fluid not in self.available_fluids():
            raise KeyError(f"No such fluid '{fluid}'")
        return sorted(c for c in self.df.columns if c not in ('fluid','source','t','p'))

    def _build_interp(self, fluid, prop):
        key = (fluid, prop)
        if key in self._cache:
            return self._cache[key]

        grp = (self.df[self.df['fluid']==fluid]
               .dropna(subset=['t','p', prop]))
        Ts = np.sort(grp['t'].unique())
        Ps = np.sort(grp['p'].unique())
        if len(Ts)<2 or len(Ps)<2:
            self._cache[key] = None
            return None

        pivot = (grp.set_index(['t','p'])[prop]
                    .unstack('p')
                    .reindex(index=Ts, columns=Ps)
                    .astype(float))
        interp = RegularGridInterpolator((Ts, Ps), pivot.values,
                                         bounds_error=False,
                                         fill_value=np.nan)
        self._cache[key] = interp
        return interp

    def query(self, fluid, T, P, props=None):
        if fluid not in self.available_fluids():
            raise KeyError(f"No such fluid '{fluid}'")
        if props is None:
            props = self.available_properties(fluid)

        out = {}
        pt = (float(T), float(P))
        for prop in props:
            fn = self._build_interp(fluid, prop)
            if fn is None:
                out[prop] = "n/a"
            else:
                val = fn(pt)
                out[prop] = float(val) if not np.isnan(val) else "n/a"
        return out
