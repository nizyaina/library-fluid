import pandas as pd
import numpy as np
from scipy.interpolate import RegularGridInterpolator

class FluidLookup:
    # define source priority
    _priority = {"coolprop": 0, "thermopack": 1, "pykingas": 2}

    def __init__(self, csv_path="master_fluid_table.csv"):
        # read in one go
        df = pd.read_csv(csv_path, low_memory=False)
        self._interps = {}

        for fluid, grp in df.groupby("fluid"):
            # 1) Clean & sort T and P
            Ts = np.array(sorted(grp["T"].dropna().astype(float).unique()))
            Ps = np.array(sorted(grp["P"].dropna().astype(float).unique()))
            # skip fluids without a full 2D grid
            if len(Ts) < 2 or len(Ps) < 2:
                continue
            pts = (Ts, Ps)

            # 2) find numeric properties
            props = [
                c for c in grp.columns
                if c not in ("fluid", "source", "T", "P")
                and pd.api.types.is_numeric_dtype(grp[c])
            ]

            interp_dict = {}
            for prop in props:
                # prepare empty grid
                grid = np.full((len(Ts), len(Ps)), np.nan, dtype=float)

                # fill by priority
                for i, Tval in enumerate(Ts):
                    for j, Pval in enumerate(Ps):
                        sub = grp[
                            (grp["T"].astype(float) == Tval) &
                            (grp["P"].astype(float) == Pval) &
                            grp[prop].notna()
                        ]
                        if sub.empty:
                            continue
                        ranks = sub["source"].map(self._priority).values
                        best = sub.iloc[ranks.argmin()]
                        grid[i, j] = float(best[prop])

                # build interpolator
                interp_dict[prop] = RegularGridInterpolator(
                    pts, grid, bounds_error=False, fill_value=np.nan
                )

            self._interps[fluid] = interp_dict

    def list_variables(self, fluid=None):
        if fluid:
            return sorted(self._interps.get(fluid, {}).keys())
        keys = set()
        for d in self._interps.values():
            keys.update(d.keys())
        return sorted(keys)

    def query(self, fluid, T, P):
        if fluid not in self._interps:
            raise KeyError(f"Fluid '{fluid}' not found or has insufficient grid.")
        pt = np.array([float(T), float(P)])
        return {prop: float(fn(pt)) for prop, fn in self._interps[fluid].items()}
