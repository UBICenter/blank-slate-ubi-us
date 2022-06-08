from typing import Tuple
from blank_slate_ubi_us.common import UBI_FUNDING, blank_slate_df
import numpy as np
from scipy.optimize import differential_evolution
from argparse import ArgumentParser

df = blank_slate_df


def get_senior_amount(
    flat_tax_rate: float,
    young_child_amount: float,
    older_child_amount: float,
    young_adult_amount: float,
    adult_amount: float,
) -> float:
    return (
        UBI_FUNDING
        + flat_tax_rate * df.agi.sum()
        - young_child_amount * (df.count_young_child * df.weight).sum()
        - older_child_amount * (df.count_older_child * df.weight).sum()
        - young_adult_amount * (df.count_young_adult * df.weight).sum()
        - adult_amount * (df.count_adult * df.weight).sum()
    ) / (df.count_senior * df.weight).sum()


def mean_percentage_loss(
    flat_tax_rate: float,
    young_child_amount: float,
    older_child_amount: float,
    young_adult_amount: float,
    adult_amount: float,
) -> float:
    senior_amount = get_senior_amount(
        flat_tax_rate,
        young_adult_amount,
        older_child_amount,
        young_adult_amount,
        adult_amount,
    )
    final_net_income = (
        df.tax_benefit_abolition_gain
        - df.agi * flat_tax_rate
        - df.count_young_child * young_child_amount
        - df.count_older_child * older_child_amount
        - df.count_young_adult * young_adult_amount
        - df.count_adult * adult_amount
        - df.count_senior * senior_amount
    )
    loss = np.minimum(0, df.baseline_net_income / final_net_income - 1)
    return loss.mean()


def solve_blank_slate_policy() -> Tuple[float, float, float]:
    """Solves for the child, adult and senior UBI amounts with
    the least mean percentage loss.

    Returns:
        Tuple[float, float, float]: The optimal child, adult and senior UBI amounts.
    """

    (
        flat_tax_rate,
        young_child_amount,
        older_child_amount,
        young_adult_amount,
        adult_amount,
    ) = differential_evolution(
        lambda x: mean_percentage_loss(*x),
        bounds=[(0, 1)] + [(0, 3e4)] * 4,
    ).x
    senior_amount = get_senior_amount(
        flat_tax_rate,
        young_child_amount,
        older_child_amount,
        young_adult_amount,
        adult_amount,
    )
    return (
        flat_tax_rate,
        young_child_amount,
        older_child_amount,
        young_adult_amount,
        adult_amount,
        senior_amount,
    )


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Generate data and charts for the Blank Slate UBI in the United States paper."
    )

    (
        flat_tax_rate,
        young_child_amount,
        older_child_amount,
        young_adult_amount,
        adult_amount,
        senior_amount,
    ) = solve_blank_slate_policy()
    print(
        f"Optimal tax rate: {flat_tax_rate:.2%}\nOptimal UBI levels:\n  0-5: ${young_child_amount:,.0f} per year\n  6-17: ${older_child_amount:,.0f} per year\n  18-24: ${young_adult_amount:,.0f} per year\n  25-64: ${adult_amount:,.0f} per year\n  65+: ${senior_amount:,.0f} per year"
    )
    print(
        f"Mean percentage loss: {mean_percentage_loss(flat_tax_rate, young_child_amount, older_child_amount, young_adult_amount, adult_amount):.3%}"
    )