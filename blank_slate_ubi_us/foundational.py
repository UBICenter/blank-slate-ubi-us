from typing import Tuple
from blank_slate_ubi_us.common import UBI_FUNDING, blank_slate_df
import numpy as np
from scipy.optimize import differential_evolution
from argparse import ArgumentParser

df = blank_slate_df


def get_senior_amount(
    child_amount: float,
    adult_amount: float,
) -> float:
    return (
        UBI_FUNDING
        - child_amount * (df.count_child * df.weight).sum()
        - adult_amount * (df.count_adult * df.weight).sum()
    ) / (df.count_senior * df.weight).sum()


def mean_percentage_loss(
    child_amount: float,
    adult_amount: float,
) -> float:
    senior_amount = get_senior_amount(child_amount, adult_amount)
    final_net_income = (
        df.funded_spm_unit_net_income
        + df.count_child * child_amount
        + df.count_adult * adult_amount
        + df.count_senior * senior_amount
    )
    loss = np.maximum(
        0, df.baseline_spm_unit_net_income / final_net_income - 1
    )
    return loss.mean()


def solve_foundational_model() -> Tuple[float, float, float]:
    """Solves for the child, adult and senior UBI amounts with
    the least mean percentage loss.

    Returns:
        Tuple[float, float, float]: The optimal child, adult and senior UBI amounts.
    """

    child_amount, adult_amount = differential_evolution(
        lambda x: mean_percentage_loss(*x),
        bounds=[(0, 2e4), (0, 2e4)],
    ).x
    senior_amount = get_senior_amount(child_amount, adult_amount)
    return child_amount, adult_amount, senior_amount


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Generate data and charts for the Blank Slate UBI in the United States paper."
    )

    child, adult, senior = solve_foundational_model()
    print(
        f"Foundational UBI:\n  Child: ${child:,.0f} per year\n  Adult: ${adult:,.0f} per year\n  Senior: ${senior:,.0f} per year"
    )
    print(f"Mean percentage loss: {mean_percentage_loss(child, adult):.2%}")
