import pandas as pd
import numpy as np
from scipy.interpolate import RegularGridInterpolator

class FluidLookup:
    def __init__(self, csv_path="master_fluid_table.csv"):
        # Read in one go to avoid low‐memory dtype warnings
        df = pd.read_csv(csv_path, low_memory=False)
        self._interps = {}

        # Build one interpolator per fluid & numeric property
        for fluid, grp in df.groupby("fluid"):
            # ensure T and P are floats, sorted
            Ts = np.sort(grp["T"].astype(float).unique())
            Ps = np.sort(grp["P"].astype(float).unique())
            pts = (Ts, Ps)

            # pick only numeric props (skip keys & strings)
            props = [
                c for c in grp.columns
                if c not in ("fluid", "source", "T", "P")
                and pd.api.types.is_numeric_dtype(grp[c])
            ]

            interp_dict = {}
            for prop in props:
                # pivot with mean to collapse duplicates
                pivot = (
                    grp
                    .pivot_table(index="T", columns="P", values=prop, aggfunc="mean")
                    .reindex(index=Ts, columns=Ps)
                )
                arr = pivot.values.astype(float)
                interp_dict[prop] = RegularGridInterpolator(
                    pts, arr, bounds_error=False, fill_value=np.nan
                )

            self._interps[fluid] = interp_dict

    def list_variables(self, fluid=None):
        """List all interpolated properties, or only for a specific fluid."""
        if fluid:
            return sorted(self._interps.get(fluid, {}).keys())
        all_props = set()
        for d in self._interps.values():
            all_props.update(d.keys())
        return sorted(all_props)

    def query(self, fluid, T, P):
        """
        Return a dict { prop: value } for the given fluid at (T,P).
        Out-of-range or missing data yields np.nan.
        """
        if fluid not in self._interps:
            raise KeyError(f"Fluid '{fluid}' not found.")
        pt = np.array([float(T), float(P)])
        return {
            prop: float(fn(pt))
            for prop, fn in self._interps[fluid].items()
        }

