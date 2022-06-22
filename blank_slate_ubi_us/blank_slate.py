from typing import Tuple
from blank_slate_ubi_us.common import UBI_FUNDING, blank_slate_df
import numpy as np
from scipy.optimize import differential_evolution
from argparse import ArgumentParser
import yaml
from blank_slate_ubi_us import REPO
from policyengine.utils.reforms import use_current_parameters

df = blank_slate_df


def get_senior_amount(
    young_child_amount: float,
    older_child_amount: float,
    young_adult_amount: float,
    adult_amount: float,
) -> float:
    return (
        UBI_FUNDING
        - young_child_amount * (df.count_young_child * df.weight).sum()
        - older_child_amount * (df.count_older_child * df.weight).sum()
        - young_adult_amount * (df.count_young_adult * df.weight).sum()
        - adult_amount * (df.count_adult * df.weight).sum()
    ) / (df.count_senior * df.weight).sum()


def mean_percentage_loss(
    young_child_amount: float,
    older_child_amount: float,
    young_adult_amount: float,
    adult_amount: float,
) -> float:
    senior_amount = get_senior_amount(
        young_child_amount,
        older_child_amount,
        young_adult_amount,
        adult_amount,
    )
    final_net_income = (
        df.funded_net_income
        + df.count_young_child * young_child_amount
        + df.count_older_child * older_child_amount
        + df.count_young_adult * young_adult_amount
        + df.count_adult * adult_amount
        + df.count_senior * senior_amount
    )
    gain = final_net_income - df.baseline_net_income
    absolute_loss = np.maximum(0, -gain)
    pct_loss = absolute_loss / np.maximum(100, df.baseline_net_income)
    average = np.average(pct_loss, weights=df.weight * df.count_person)
    return average


def solve_blank_slate_policy() -> Tuple[float, float, float]:
    """Solves for the child, adult and senior UBI amounts with
    the least mean percentage loss.

    Returns:
        Tuple[float, float, float]: The optimal child, adult and senior UBI amounts.
    """

    (
        young_child_amount,
        older_child_amount,
        young_adult_amount,
        adult_amount,
    ) = differential_evolution(
        lambda x: mean_percentage_loss(*x),
        bounds=[(0, 15e4)] * 4,
        maxiter=int(1e3),
    ).x
    senior_amount = get_senior_amount(
        young_child_amount,
        older_child_amount,
        young_adult_amount,
        adult_amount,
    )
    return (
        young_child_amount,
        older_child_amount,
        young_adult_amount,
        adult_amount,
        senior_amount,
    )


def save_optimal_policy(
    young_child_amount: float,
    older_child_amount: float,
    young_adult_amount: float,
    adult_amount: float,
    senior_amount: float,
):
    policy_file = REPO / "blank_slate_ubi_us" / "data" / "policy.yaml"
    policy = (
        young_child_amount,
        older_child_amount,
        young_adult_amount,
        adult_amount,
        senior_amount,
    )
    names = (
        "young_child_amount",
        "older_child_amount",
        "young_adult_amount",
        "adult_amount",
        "senior_amount",
    )
    with policy_file.open("w") as f:
        result = yaml.dump(
            {
                "policy": {
                    name: f"{value:_.0f}" for name, value in zip(names, policy)
                },
            },
        )
        f.write(result.replace("'", ""))


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Generate data and charts for the Blank Slate UBI in the United States paper."
    )

    (
        young_child_amount,
        older_child_amount,
        young_adult_amount,
        adult_amount,
        senior_amount,
    ) = policy = solve_blank_slate_policy()
    print(
        f"Optimal UBI levels:\n  0-5: ${young_child_amount:,.0f} per year\n  6-17: ${older_child_amount:,.0f} per year\n  18-24: ${young_adult_amount:,.0f} per year\n  25-64: ${adult_amount:,.0f} per year\n  65+: ${senior_amount:,.0f} per year"
    )
    print(
        f"Mean percentage loss: {mean_percentage_loss(young_child_amount, older_child_amount, young_adult_amount, adult_amount):.3%}"
    )
    save_optimal_policy(*policy)
