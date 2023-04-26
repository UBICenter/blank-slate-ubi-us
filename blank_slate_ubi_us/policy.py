import pandas as pd
import numpy as np
from scipy.optimize import differential_evolution
from policyengine_us import Microsimulation
from policyengine_us.model_api import *

def create_baseline_reform() -> Type[Reform]:
    # Just the SNAP EA abolition
    def modify_parameters(parameters):
        parameters.gov.usda.snap.emergency_allotment.allowed.update(period="year:2023:1", value=False)
        return parameters
    
    class baseline_reform(Reform):
        def apply(self):
            self.modify_parameters(modify_parameters)

    return baseline_reform

def create_funding_reform(flat_tax_rate: float) -> Type[Reform]:
    def modify_parameters(parameters):
        parameters.gov.contrib.ubi_center.flat_tax.abolish_federal_income_tax.update(period="year:2023:1", value=True)
        parameters.gov.contrib.ubi_center.flat_tax.abolish_payroll_tax.update(period="year:2023:1", value=True)
        parameters.gov.contrib.ubi_center.flat_tax.abolish_self_emp_tax.update(period="year:2023:1", value=True)
        parameters.gov.hud.abolition.update(period="year:2023:1", value=True)
        parameters.gov.hhs.tanf.abolish_tanf.update(period="year:2023:1", value=True)
        parameters.gov.ssa.ssi.abolish_ssi.update(period="year:2023:1", value=True)
        parameters.gov.usda.snap.abolish_snap.update(period="year:2023:1", value=True)
        parameters.gov.usda.wic.abolish_wic.update(period="year:2023:1", value=True)
        parameters.gov.contrib.ubi_center.flat_tax.rate.update(period="year:2023:1", value=flat_tax_rate)
        parameters.gov.contrib.ubi_center.flat_tax.deduct_ptc.update(period="year:2023:1", value=True)
        parameters.gov.usda.snap.emergency_allotment.allowed.update(period="year:2023:1", value=False)
        return parameters
    
    class funding_reform(Reform):
        def apply(self):
            self.modify_parameters(modify_parameters)

    return funding_reform

class BlankSlatePolicy:
    young_child: float = 0
    older_child: float = 0
    young_adult: float = 0
    adult: float = 0
    senior: float = 0
    flat_tax_rate: float = 0.40

    def __init__(self, flat_tax_rate: float = 0.40):
        self.baseline = Microsimulation(reform=create_baseline_reform())
        self.blank_slate_funded = Microsimulation(reform=create_funding_reform(flat_tax_rate))
        self.df = self.create_dataframe()
        self.ubi_funding = self.get_ubi_funding()

    def create_dataframe(self) -> pd.DataFrame:
        age = self.baseline.calc("age").values
        return pd.DataFrame(
            dict(
                baseline_net_income=self.baseline.calc(
                    "spm_unit_net_income"
                ).values,
                count_young_child=self.baseline.map_result(
                    age < 6, "person", "spm_unit"
                ),
                count_older_child=self.baseline.map_result(
                    (age >= 6) & (age < 18), "person", "spm_unit"
                ),
                count_young_adult=self.baseline.map_result(
                    (age >= 18) & (age < 25), "person", "spm_unit"
                ),
                count_adult=self.baseline.map_result(
                    (age >= 25) & (age < 65), "person", "spm_unit"
                ),
                count_senior=self.baseline.map_result(
                    age >= 65, "person", "spm_unit"
                ),
                count_person=self.baseline.map_result(
                    age >= 0, "person", "spm_unit"
                ),
                funded_net_income=self.blank_slate_funded.calculate(
                    "spm_unit_net_income"
                ).values,
                weight=self.baseline.calculate("spm_unit_weight").values,
            )
        )

    def get_ubi_funding(self) -> float:
        return (
            (self.df.baseline_net_income - self.df.funded_net_income)
            * self.df.weight
        ).sum()

    def get_senior_amount(
        self,
        young_child: float,
        older_child: float,
        young_adult: float,
        adult: float,
    ) -> float:
        return (
            self.ubi_funding
            - young_child * (self.df.count_young_child * self.df.weight).sum()
            - older_child * (self.df.count_older_child * self.df.weight).sum()
            - young_adult * (self.df.count_young_adult * self.df.weight).sum()
            - adult * (self.df.count_adult * self.df.weight).sum()
        ) / (self.df.count_senior * self.df.weight).sum()

    def mean_percentage_loss(
        self,
        young_child: float,
        older_child: float,
        young_adult: float,
        adult: float,
    ) -> float:
        senior_amount = self.get_senior_amount(
            young_child, older_child, young_adult, adult
        )
        final_net_income = (
            self.df.funded_net_income
            + self.df.count_young_child * young_child
            + self.df.count_older_child * older_child
            + self.df.count_young_adult * young_adult
            + self.df.count_adult * adult
            + self.df.count_senior * senior_amount
        )
        gain = final_net_income - self.df.baseline_net_income
        absolute_loss = np.maximum(0, -gain)
        pct_loss = absolute_loss / np.maximum(100, self.df.baseline_net_income)
        average = np.average(
            pct_loss, weights=self.df.weight * self.df.count_person
        )
        return average

    def solve(self, return_amounts: bool = False, return_loss: bool = False) -> dict:
        (
            self.young_child,
            self.older_child,
            self.young_adult,
            self.adult,
        ) = differential_evolution(
            lambda x: self.mean_percentage_loss(*x),
            bounds=[(0, 15e4)] * 4,
            maxiter=int(1e3),
        ).x
        self.senior = self.get_senior_amount(
            self.young_child, self.older_child, self.young_adult, self.adult
        )
        self.reform = dict(
            **self.base_reform,
            young_child_bi_amount=round(self.young_child),
            older_child_bi_amount=round(self.older_child),
            young_adult_bi_amount=round(self.young_adult),
            older_adult_bi_amount=round(self.adult),
            senior_bi_amount=round(self.senior),
        )
        if not return_amounts and not return_loss:
            return self.reform
        
        data = dict(reform=self.reform)

        if return_amounts:
            data["amounts"] = dict(
                young_child=self.young_child,
                older_child=self.older_child,
                young_adult=self.young_adult,
                adult=self.adult,
                senior=self.senior,
            )
        
        if return_loss:
            data["loss"] = self.mean_percentage_loss(
                self.young_child, self.older_child, self.young_adult, self.adult
            )
        
        return data
