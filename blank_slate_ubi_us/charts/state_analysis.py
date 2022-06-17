import plotly.express as px
import pandas as pd
from blank_slate_ubi_us.charts.helpers import format_fig
from ubicenter.plotly import BLUE


def get_state_rankings(baseline, reformed):
    gain = reformed.calc(
        "spm_unit_net_income", map_to="household"
    ) - baseline.calc("spm_unit_net_income", map_to="household")
    state = baseline.calc("state_code")
    gain_by_state = gain.groupby(state).sum().sort_values()
    gain_by_state = pd.concat(
        [
            gain_by_state[:5],
            gain_by_state[-5:],
        ]
    )
    fig = px.bar(
        gain_by_state.apply(lambda x: round(x / 1e9)),
        orientation="h",
        color_discrete_sequence=[BLUE],
    )
    fig.update_layout(
        title="Top-5 winner and loser States under Blank Slate UBI",
        xaxis_title="Net gain",
        yaxis_title="State",
        xaxis_tickprefix="$",
        xaxis_ticksuffix="bn",
        showlegend=False,
    )
    return format_fig(fig)
