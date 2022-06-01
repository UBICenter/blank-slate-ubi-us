from openfisca_us.model_api import *
from openfisca_us.tools.baseline_variables import baseline_variables
from openfisca_us.reforms import abolish
from openfisca_us import Microsimulation
import logging
from blank_slate_ubi_us import REPO

logging.basicConfig(level=logging.INFO)

def prepare_simulation():
    """Adjusts the microsimulation for simulation - turns off reported net income.
    """
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

def ubi(person_amount: float) -> Reform:
    """Create a reform adding a universal basic income.

    Args:
        person_amount (float): The yearly per-person amount.

    Returns:
        Reform: The OpenFisca reform.
    """
    class ubi(Variable):
        value_type = float
        entity = Person
        label = "UBI"
        definition_period = YEAR

        def formula(person, period, parameters):
            return person_amount
    
    class spm_unit_benefits(baseline_variables["spm_unit_benefits"]):
        def formula(spm_unit, period, parameters):
            original_benefits = baseline_variables["spm_unit_benefits"].formula(spm_unit, period, parameters)
            ubi_amount = add(spm_unit, period, ["ubi"])
            return original_benefits + ubi_amount

    class reform(Reform):
        def apply(self):
            self.add_variable(ubi)
            self.update_variable(spm_unit_benefits)

    return reform

blank_slate_df_path = REPO / "data" / "blank_slate_df.csv.gz"

blank_slate_funding = (
    prepare_simulation(),
    abolish("wic"),
    abolish("snap_normal_allotment"),
    abolish("ssi"),
    flat_tax(0.4),
)

BLANK_SLATE_FUNDING_SUBREFORM_NAMES = [
    "Abolish WIC",
    "Abolish SNAP",
    "Abolish SSI",
    "40% flat tax",
]

if not blank_slate_df_path.exists():
    logging.info(f"Did not find {blank_slate_df_path}, generating.")
    blank_slate_df_path.parent.mkdir(exist_ok=True)

    baseline = Microsimulation(prepare_simulation())
    funded = Microsimulation(blank_slate_funding)

    blank_slate_df = pd.DataFrame(dict(
        baseline_spm_unit_net_income=baseline.calc("spm_unit_net_income", 2022),
        count_child=baseline.calc("is_child", map_to="spm_unit", period=2022),
        count_adult=baseline.calc("is_wa_adult", map_to="spm_unit", period=2022),
        count_senior=baseline.calc("is_senior", map_to="spm_unit", period=2022),
        funded_spm_unit_net_income=funded.calc("spm_unit_net_income", 2022),
        weight=baseline.calc("spm_unit_weight", 2022),
    ))

    blank_slate_df.to_csv(blank_slate_df_path, compression="gzip")
    logging.info(f"Completed generation of {blank_slate_df_path}.")
else:
    blank_slate_df = pd.read_csv(blank_slate_df_path, compression="gzip")

UBI_FUNDING = ((blank_slate_df.baseline_spm_unit_net_income - blank_slate_df.funded_spm_unit_net_income) * blank_slate_df.weight).sum()
