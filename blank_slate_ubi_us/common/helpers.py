from openfisca_us.model_api import *
from openfisca_us.tools.baseline_variables import baseline_variables
from openfisca_us.reforms import abolish
from openfisca_us import Microsimulation
import logging
from blank_slate_ubi_us import REPO
import yaml
from pathlib import Path

logging.basicConfig(level=logging.INFO)


def prepare_simulation():
    """Adjusts the microsimulation for simulation - turns off reported net income."""

    class reform(Reform):
        def apply(self):
            self.neutralize_variable("spm_unit_net_income_reported")

    return reform


def flat_tax(rate: float) -> Reform:
    """Create a reform converting federal,

    Args:
        rate (float): The flat tax rate.

    Returns:
        Reform: The OpenFisca reform.
    """

    class spm_unit_taxes(baseline_variables["spm_unit_taxes"]):
        def formula(spm_unit, period, parameters):
            flat_tax = add(spm_unit, period, ["adjusted_gross_income"]) * rate
            state_tax = spm_unit("spm_unit_state_tax", period)
            return flat_tax + state_tax

    class reform(Reform):
        def apply(self):
            self.update_variable(spm_unit_taxes)

    return reform


def ubi(
    young_child_amount: float,
    older_child_amount: float,
    young_adult_amount: float,
    adult_amount: float,
    senior_amount: float,
) -> Reform:
    """Create a reform adding a universal basic income.

    Args:
        young_child_amount (float): The yearly payment for children under 6.
        older_child_amount (float): The yearly payment for children aged 6-17.
        young_adult_amount (float): The yearly payment for adults aged 18-24.
        adult_amount (float): The yearly payment for adults aged 25-64.
        senior_amount (float): The yearly payment for seniors aged 65+.

    Returns:
        Reform: The OpenFisca reform.
    """

    class ubi(Variable):
        value_type = float
        entity = Person
        label = "UBI"
        definition_period = YEAR

        def formula(person, period, parameters):
            age = person("age", period)
            return select(
                [
                    age < 6,
                    (age >= 6) & (age < 18),
                    (age >= 18) & (age < 25),
                    (age >= 25) & (age < 65),
                    (age >= 65),
                ],
                [
                    young_child_amount,
                    older_child_amount,
                    young_adult_amount,
                    adult_amount,
                    senior_amount,
                ],
            )

    class spm_unit_benefits(baseline_variables["spm_unit_benefits"]):
        def formula(spm_unit, period, parameters):
            original_benefits = baseline_variables[
                "spm_unit_benefits"
            ].formula(spm_unit, period, parameters)
            ubi_amount = add(spm_unit, period, ["ubi"])
            return original_benefits + ubi_amount

    class reform(Reform):
        def apply(self):
            self.add_variable(ubi)
            self.update_variable(spm_unit_benefits)

    return reform


blank_slate_df_path = (
    REPO / "blank_slate_ubi_us" / "data" / "blank_slate_df.csv.gz"
)

blank_slate_funding = (
    prepare_simulation(),
    abolish("wic"),
    abolish("snap_normal_allotment"),
    abolish("ssi"),
    abolish("tanf"),
    abolish("spm_unit_capped_housing_subsidy"),
    flat_tax(0.4),
    # TODO: childcare, housing, broadband
)

BLANK_SLATE_FUNDING_SUBREFORM_NAMES = [
    "Abolish WIC",
    "Abolish SNAP",
    "Abolish SSI",
    "Abolish TANF",
    "40% flat tax",
]

if not blank_slate_df_path.exists():
    logging.info(f"Did not find {blank_slate_df_path}, generating.")
    blank_slate_df_path.parent.mkdir(exist_ok=True)

    baseline = Microsimulation(prepare_simulation())
    funded = Microsimulation(blank_slate_funding)
    age = baseline.calc("age", 2022)
    blank_slate_df = pd.DataFrame(
        dict(
            baseline_net_income=baseline.calc("spm_unit_net_income", 2022),
            count_young_child=baseline.map_to(age < 6, "person", "spm_unit"),
            count_older_child=baseline.map_to(
                (age >= 6) & (age < 18), "person", "spm_unit"
            ),
            count_young_adult=baseline.map_to(
                (age >= 18) & (age < 25), "person", "spm_unit"
            ),
            count_adult=baseline.map_to(
                (age >= 25) & (age < 65), "person", "spm_unit"
            ),
            count_senior=baseline.map_to(age >= 65, "person", "spm_unit"),
            count_person=baseline.map_to(age >= 0, "person", "spm_unit"),
            funded_net_income=funded.calc("spm_unit_net_income", 2022),
            weight=baseline.calc("spm_unit_weight", 2022),
        )
    )

    blank_slate_df = blank_slate_df[blank_slate_df.baseline_net_income >= 0]

    blank_slate_df.to_csv(blank_slate_df_path, compression="gzip")
    logging.info(f"Completed generation of {blank_slate_df_path}.")
else:
    blank_slate_df = pd.read_csv(blank_slate_df_path, compression="gzip")

UBI_FUNDING = (
    (blank_slate_df.baseline_net_income - blank_slate_df.funded_net_income)
    * blank_slate_df.weight
).sum()


def blank_slate_reform(
    young_child_amount: float,
    older_child_amount: float,
    young_adult_amount: float,
    adult_amount: float,
    senior_amount: float,
) -> Reform:
    return (
        blank_slate_funding,
        ubi(
            young_child_amount,
            older_child_amount,
            young_adult_amount,
            adult_amount,
            senior_amount,
        ),
    )


def blank_slate_ubi() -> Reform:
    policy_file = REPO / "blank_slate_ubi_us" / "data" / "policy.yaml"
    policy = yaml.load(policy_file.read_text(), Loader=yaml.SafeLoader)[
        "policy"
    ]
    return blank_slate_reform(**policy)
