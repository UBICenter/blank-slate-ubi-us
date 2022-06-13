from typing import Tuple, Type
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from openfisca_tools import Microsimulation
import pandas as pd
from policyengine.utils import charts
from policyengine.utils.general import PolicyEngineResultsConfig
from ubicenter import format_fig

NAMES = (
    "Gain more than 5%",
    "Gain less than 5%",
    "No change",
    "Lose less than 5%",
    "Lose more than 5%",
)


def intra_decile_graph_data(
    baseline: Microsimulation,
    reformed: Microsimulation,
    config: Type[PolicyEngineResultsConfig],
    decile_type: str = "income",
) -> pd.DataFrame:
    """Data for the distribution of net income changes by decile and overall.

    :param baseline: Baseline simulation.
    :type baseline: Microsimulation
    :param reformed: Reform simulation.
    :type reformed: Microsimulation
    :return: DataFrame with share of each decile experiencing each outcome.
    :rtype: pd.DataFrame
    """
    l = []
    baseline_hh_net_income = baseline.calc(
        config.household_net_income_variable, map_to="person"
    )
    reformed_hh_net_income = reformed.calc(
        config.household_net_income_variable, map_to="person"
    )
    programs = [
        "ssi",
        "snap",
        "wic",
        "tanf",
        "spm_unit_capped_housing_subsidy",
    ]
    gain = reformed_hh_net_income - baseline_hh_net_income
    rel_gain = gain / np.maximum(baseline_hh_net_income, 1)
    BANDS = (None, 0.05, 1e-3, -1e-3, -0.05, None)
    for upper, lower, name in zip(BANDS[:-1], BANDS[1:], NAMES):
        fractions = []
        for program in programs:
            on_program = (
                baseline.map_to(
                    baseline.calc(program, map_to="household"),
                    "household",
                    "person",
                ).values
                > 0
            )
            subset = rel_gain[on_program]
            if lower is not None:
                subset = subset[rel_gain > lower]
            if upper is not None:
                subset = subset[rel_gain <= upper]
            fractions += [subset.count() / rel_gain[on_program].count()]
        tmp = pd.DataFrame(
            {
                "fraction": fractions,
                "program": [
                    "SSI",
                    "SNAP",
                    "WIC",
                    "TANF",
                    "Housing subsidies",
                ],
                "outcome": name,
            }
        )
        l.append(tmp)
        subset = rel_gain
        if lower is not None:
            subset = subset[rel_gain > lower]
        if upper is not None:
            subset = subset[rel_gain <= upper]
    return pd.concat(l).reset_index()


INTRA_DECILE_COLORS = (
    charts.DARK_GRAY,
    charts.GRAY,
    charts.LIGHT_GRAY,
    charts.LIGHT_GREEN,
    charts.DARK_GREEN,
)[::-1]


def intra_decile_label(fraction: float, decile: str, outcome: str) -> str:
    """Label for a data point in the intra-decile chart for hovercards.

    :param fraction: Share of the decile experiencing the outcome.
    :type fraction: float
    :param decile: Decile number as a string, or "All".
    :type decile: str
    :param outcome: Outcome, e.g. "Gain more than 5%".
    :type outcome: str
    :return: String representation of the hovercard label.
    :rtype: str
    """
    res = "{:.0%}".format(fraction) + " of "  # x% of
    if decile == "All":
        res += "all people "
    else:
        res += "people aged " + decile.lower()
    if outcome == "No change":
        return res + "experience no change"
    else:
        return res + outcome.lower() + " of their income"


def single_intra_decile_graph(df: pd.DataFrame) -> go.Figure:
    """Single intra-decile graph, for either by-decile or overall.

    :param df: DataFrame with intra-decile or intra-overall data.
    :type df: pd.DataFrame
    :return: Plotly bar chart.
    :rtype: go.Figure
    """
    fig = px.bar(
        df,
        x="fraction",
        y="program",
        color="outcome",
        custom_data=["hover"],
        color_discrete_sequence=INTRA_DECILE_COLORS,
        orientation="h",
    )
    charts.add_custom_hovercard(fig)
    return fig


def program_winner_chart(
    baseline: Microsimulation,
    reformed: Microsimulation,
    config: Type[PolicyEngineResultsConfig],
) -> dict:
    df = intra_decile_graph_data(baseline, reformed, config)
    df["hover"] = df.apply(
        lambda x: intra_decile_label(x.fraction, x.program, x.outcome),
        axis=1,
    )
    # Create the decile figure first, then the total to go above it.
    decile_fig = single_intra_decile_graph(df)
    fig = make_subplots(
        rows=1,
        cols=1,
        shared_xaxes=True,
        row_heights=[10],
        vertical_spacing=0.05,
        x_title="Population share",
        y_title="Program",
    )
    fig.update_xaxes(showgrid=False, tickformat=",.0%")
    fig.add_traces(decile_fig.data, 1, 1)
    fig.update_layout(
        barmode="stack",
        title=f"Distribution of gains and losses by program participation under Blank Slate UBI",
    )
    for i in range(5):
        fig.data[i].showlegend = False
    return format_fig(fig)
