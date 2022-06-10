import plotly.express as px
import pandas as pd
from ubicenter import format_fig


def us_state_choropleth(baseline, reformed):
    gain = reformed.calc(
        "spm_unit_net_income", map_to="household"
    ) - baseline.calc("spm_unit_net_income", map_to="household")
    people = pd.Series(
        baseline.calc("person_weight", map_to="household").values
    )
    income = baseline.calc("spm_unit_net_income", map_to="household")
    state = baseline.calc("state_code")
    gain_by_state = gain.groupby(state).sum() / income.groupby(state).sum()
    df = pd.DataFrame(
        {
            "State": gain_by_state.index,
            "Gain": gain_by_state.values,
        }
    )
    df["Label"] = [
        f"On average, people in {state} {'gain' if gain >= 0 else 'lose'} {abs(gain):.1%}"
        for state, gain in zip(df["State"], df["Gain"])
    ]
    fig = px.choropleth(
        locations=gain_by_state.index,
        color=gain_by_state.values,
        locationmode="USA-states",
        scope="usa",
        custom_data=[df.Label],
    )
    fig.update_layout(
        title="Average gain by U.S. State under Blank Slate UBI",
        coloraxis_colorbar_tickformat=".0%",
        coloraxis_colorbar_title="",
    )
    fig.update_traces(
        hovertemplate="%{customdata[0]}",
    )
    return format_fig(fig)
