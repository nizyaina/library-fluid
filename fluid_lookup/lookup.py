import pandas as pd
import numpy as np
from scipy.interpolate import RegularGridInterpolator

class FluidLookup:
    # Define your source priority here
    _priority = {"coolprop": 0, "thermopack": 1, "pykingas": 2}

    def __init__(self, csv_path="master_fluid_table.csv"):
        # Read in one go to suppress mixed‐type warnings
        df = pd.read_csv(csv_path, low_memory=False)
        self._interps = {}

        for fluid, grp in df.groupby("fluid"):
            # Build sorted T and P grids
            Ts = np.sort(grp["T"].astype(float).unique())
            Ps = np.sort(grp["P"].astype(float).unique())
            pts = (Ts, Ps)

            # Identify numeric properties (skip metadata columns)
            props = [
                c for c in grp.columns
                if c not in ("fluid", "source", "T", "P")
                and pd.api.types.is_numeric_dtype(grp[c])
            ]

            interp_dict = {}
            for prop in props:
                # Collapse duplicates by priority
                def pick(sub):
                    # sub is a DataFrame for one (T,P)
                    ranks = sub["source"].map(self._priority).values
                    values = sub[prop].values.astype(float)
                    return values[np.argmin(ranks)]

                # Group by T,P and pick by priority
                series = (
                    grp[["T", "P", "source", prop]]
                    .dropna(subset=[prop])
                    .groupby(["T", "P"])
                    .apply(pick)
                )

                # Turn into a 2D grid
                pivot = series.unstack(level="P").reindex(index=Ts, columns=Ps)
                arr = pivot.values.astype(float)

                # Build the interpolator
                interp_dict[prop] = RegularGridInterpolator(
                    pts, arr, bounds_error=False, fill_value=np.nan
                )

            self._interps[fluid] = interp_dict

    def list_variables(self, fluid=None):
        """Return all available property names, or for one fluid."""
        if fluid:
            return sorted(self._interps.get(fluid, {}))
        all_props = set().union(*self._interps.values())
        return sorted(all_props)

    def query(self, fluid, T, P):
        """
        Return dict {prop: value} at (T,P), using source‐priority
        to collapse duplicates and NaN where out‐of‐range.
        """
        if fluid not in self._interps:
            raise KeyError(f"Fluid '{fluid}' not found.")
        pt = np.array([float(T), float(P)])
        return {prop: float(fn(pt)) for prop, fn in self._interps[fluid].items()}
