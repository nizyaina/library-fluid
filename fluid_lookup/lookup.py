import pandas as pd
import numpy as np
from scipy.interpolate import RegularGridInterpolator

class FluidLookup:
    def __init__(self, csv_path="master_fluid_table.csv"):
        # Load everything at once to suppress low‐memory dtype warnings
        df = pd.read_csv(csv_path, low_memory=False)
        self._interps = {}

        # Build per‐fluid interpolators
        for fluid, grp in df.groupby("fluid"):
            # Ensure T and P are floats and sorted
            Ts = np.sort(grp["T"].astype(float).unique())
            Ps = np.sort(grp["P"].astype(float).unique())
            pts = (Ts, Ps)

            # Pick only numeric props (skip fluid, source, T, P)
            props = [
                c for c in grp.columns
                if c not in ("fluid", "source", "T", "P")
                and pd.api.types.is_numeric_dtype(grp[c])
            ]

            interp_dict = {}
            for prop in props:
                # Use pivot_table with mean to collapse any duplicate (T,P)
                pivot = (
                    grp
                    .pivot_table(index="T", columns="P",
                                 values=prop, aggfunc="mean")
                    .reindex(index=Ts, columns=Ps)
                )
                arr = pivot.values.astype(float)

                interp_dict[prop] = RegularGridInterpolator(
                    pts, arr, bounds_error=False, fill_value=np.nan
                )

            self._interps[fluid] = interp_dict

    def list_variables(self, fluid=None):
        """Return sorted list of all interpolated property names,
        or only those for a given fluid."""
        if fluid:
            return sorted(self._interps.get(fluid, {}).keys())
        all_props = set()
        for d in self._interps.values():
            all_props.update(d.keys())
        return sorted(all_props)

    def query(self, fluid, T, P):
        """Interpolate all properties for `fluid` at (T,P)."""
        if fluid not in self._interps:
            raise KeyError(f"Fluid '{fluid}' not found.")
        pt = np.array([float(T), float(P)])
        return {prop: float(fn(pt))
                for prop, fn in self._interps[fluid].items()}
