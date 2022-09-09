from openfisca_us.model_api import *
from openfisca_us.reforms import abolish
from openfisca_us import Microsimulation
import logging
from blank_slate_ubi_us import REPO
import yaml
from openfisca_us import CountryTaxBenefitSystem
from openfisca_us.tools.baseline_variables import baseline_variables
from policyengine.country.openfisca.reforms import Policy, PolicyReform, use_current_parameters
from policyengine.country.openfisca.parameters import build_parameters
from policyengine import PolicyEngineUS

us = PolicyEngineUS()

logging.basicConfig(level=logging.INFO)


def prepare_simulation():
    """Adjusts the microsimulation for simulation - turns off reported net income."""

    class reform(Reform):
        def apply(self):
            self.neutralize_variable("spm_unit_net_income_reported")
            self.neutralize_variable("snap_emergency_allotment")

    return reform, use_current_parameters()

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

BLANK_SLATE_PARAMETERS = dict(
    abolish_income_tax=1,
    abolish_emp_payroll_tax=1,
    abolish_self_emp_tax=1,
    abolish_housing_subsidies=1,
    abolish_tanf=1,
    abolish_ssi=1,
    abolish_snap=1,
    abolish_wic=1,
    flat_tax=0.40,
    baseline_abolish_snap_ea=1,
    ptc_flat_tax=1,
)

system = CountryTaxBenefitSystem()

def blank_slate_funding_reform(reform_dict: dict = BLANK_SLATE_PARAMETERS) -> Reform:
    return Policy(reform_dict, build_parameters(system))


blank_slate_df_path = (
    REPO / "blank_slate_ubi_us" / "data" / "blank_slate_df.csv.gz"
)

blank_slate_funding = (
    prepare_simulation(),
    blank_slate_funding_reform(),
)

BLANK_SLATE_FUNDING_SUBREFORM_NAMES = [
    "Abolish WIC",
    "Abolish SNAP",
    "Abolish SSI",
    "Abolish TANF",
    "Abolish housing subsidies",
    "50% flat tax",
]

def create_blank_slate_df(parameters: dict = {}) -> pd.DataFrame:
    params = BLANK_SLATE_PARAMETERS
    params.update(parameters)
    funding_reform = (
        prepare_simulation(),
        blank_slate_funding_reform(parameters),
    )
    baseline = Microsimulation(prepare_simulation())
    funded = Microsimulation(funding_reform)
    age = baseline.calc("age", 2022).values
    blank_slate_df = pd.DataFrame(
        dict(
            baseline_net_income=baseline.calc(
                "spm_unit_net_income", 2022
            ).values,
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
            funded_net_income=funded.calc("spm_unit_net_income", 2022).values,
            weight=baseline.calc("spm_unit_weight", 2022).values,
        )
    )
    return blank_slate_df

if not blank_slate_df_path.exists():
    logging.info(f"Did not find {blank_slate_df_path}, generating.")
    blank_slate_df_path.parent.mkdir(exist_ok=True)
    blank_slate_df = create_blank_slate_df()
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
