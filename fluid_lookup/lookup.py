import pandas as pd
import numpy as np
from scipy.interpolate import RegularGridInterpolator

class FluidLookup:
    # Define source priority: lower = higher priority
    _priority = {"coolprop": 0, "thermopack": 1, "pykingas": 2}

    def __init__(self, csv_path="master_fluid_table.csv"):
        # Load once (low_memory to suppress warnings)
        df = pd.read_csv(csv_path, low_memory=False)
        self._interps = {}

        # Build one interpolator per fluid & per numeric property
        for fluid, grp in df.groupby("fluid"):
            # Unique sorted T & P
            Ts = np.sort(grp["T"].astype(float).unique())
            Ps = np.sort(grp["P"].astype(float).unique())
            pts = (Ts, Ps)

            # Identify numeric props
            props = [
                c for c in grp.columns
                if c not in ("fluid", "source", "T", "P")
                and pd.api.types.is_numeric_dtype(grp[c])
            ]

            interp_dict = {}
            for prop in props:
                # Allocate grid array
                grid = np.full((len(Ts), len(Ps)), np.nan, dtype=float)

                # Fill grid by priority
                for i, Tval in enumerate(Ts):
                    for j, Pval in enumerate(Ps):
                        sub = grp[
                            (grp["T"].astype(float) == Tval) &
                            (grp["P"].astype(float) == Pval) &
                            grp[prop].notna()
                        ]
                        if sub.empty:
                            continue
                        # pick row with highest priority source
                        src_ranks = sub["source"].map(self._priority)
                        best = sub.iloc[src_ranks.argmin()]
                        grid[i, j] = float(best[prop])

                # Build interpolator
                interp_dict[prop] = RegularGridInterpolator(
                    pts, grid, bounds_error=False, fill_value=np.nan
                )

            self._interps[fluid] = interp_dict

    def list_variables(self, fluid=None):
        """All props or just those for one fluid."""
        if fluid:
            return sorted(self._interps.get(fluid, {}).keys())
        keys = set()
        for d in self._interps.values():
            keys.update(d.keys())
        return sorted(keys)

    def query(self, fluid, T, P):
        """Return {prop: value} at (T,P), or np.nan if unavailable."""
        if fluid not in self._interps:
            raise KeyError(f"Fluid '{fluid}' not found.")
        pt = np.array([float(T), float(P)])
        return {prop: float(fn(pt)) for prop, fn in self._interps[fluid].items()}
