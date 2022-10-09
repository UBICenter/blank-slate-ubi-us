# This module creates a chart showing for each flat tax rate, the mean percent loss under optimal UBI, and the mean percent loss under equal per-person UBI.

from typing import Tuple
from blank_slate_ubi_us.policy import BlankSlatePolicy
from policyengine import PolicyEngineUS
import pandas as pd
import numpy as np

us = PolicyEngineUS()

def get_metrics_by_flat_tax(flat_tax: float) -> Tuple[float]:
    policy = BlankSlatePolicy(flat_tax_rate=flat_tax)
    optimal_ubi_reform = policy.solve()
    baseline = policy.baseline
    _, reformed = us.create_microsimulations(optimal_ubi_reform)

    poverty_rate_baseline = baseline.calc("spm_unit_is_in_spm_poverty", map_to="person").mean()
    poverty_rate_reformed = reformed.calc("spm_unit_is_in_spm_poverty", map_to="person").mean()
    poverty_rate_change = (poverty_rate_reformed - poverty_rate_baseline) / poverty_rate_baseline

    equiv_income = baseline.calc(
        "spm_unit_net_income", map_to="person"
    )
    reform_equiv_income = reformed.calc(
        "spm_unit_net_income", map_to="person"
    )
    baseline_gini = equiv_income.gini()
    reform_gini = reform_equiv_income.gini()
    gini_change = reform_gini / baseline_gini - 1

    return poverty_rate_change, gini_change

if __name__ == "__main__":

    flat_taxes = []
    poverty_rate_changes = []
    gini_changes = []

    for flat_tax in np.arange(0.0, 0.51, 0.01):
        poverty_change, gini_change = get_metrics_by_flat_tax(flat_tax)
        flat_taxes.append(flat_tax)
        poverty_rate_changes.append(poverty_change)
        gini_changes.append(gini_change)
        print(f"Flat tax: {flat_tax:.0%}, poverty rate change: {poverty_change:.2%}, gini change: {gini_change:.2%}")

    df = pd.DataFrame(
        dict(
            flat_tax=flat_taxes,
            poverty_rate_change=poverty_rate_changes,
            gini_change=gini_changes,
        )
    )

    df.to_csv("metrics_by_flat_tax.csv", index=False)