# This module creates a chart showing for each flat tax rate, the mean percent loss under optimal UBI, and the mean percent loss under equal per-person UBI.

from typing import Tuple
from blank_slate_ubi_us.policy import BlankSlatePolicy
import pandas as pd
import numpy as np

def get_losses_by_flat_tax(flat_tax: float) -> Tuple[float]:
    policy = BlankSlatePolicy(flat_tax_rate=flat_tax)
    population = policy.baseline.calc("people").sum()
    ubi_funding = policy.ubi_funding
    equal_ubi = ubi_funding / population
    equal_ubi_loss = policy.mean_percentage_loss(
        young_child=equal_ubi,
        older_child=equal_ubi,
        young_adult=equal_ubi,
        adult=equal_ubi,
    )
    optimal_ubi_loss = policy.solve(return_loss=True).get("loss")
    return equal_ubi_loss, optimal_ubi_loss

if __name__ == "__main__":

    flat_taxes = []
    equal_losses = []
    optimal_losses = []

    for flat_tax in np.arange(0.0, 0.51, 0.01):
        equal_ubi_loss, optimal_ubi_loss = get_losses_by_flat_tax(flat_tax)
        flat_taxes.append(flat_tax)
        equal_losses.append(equal_ubi_loss)
        optimal_losses.append(optimal_ubi_loss)
        print(f"Flat tax: {flat_tax:.0%}, equal loss: {equal_ubi_loss:.2%}, optimal loss: {optimal_ubi_loss:.2%}")

    df = pd.DataFrame(
        dict(
            flat_tax=flat_taxes,
            equal_loss=equal_losses,
            optimal_loss=optimal_losses,
        )
    )

    df.to_csv("mean_percent_loss_by_flat_tax.csv", index=False)