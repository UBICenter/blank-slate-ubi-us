import plotly.express as px
import pandas as pd
from blank_slate_ubi_us.charts.helpers import format_fig


def us_state_poverty_choropleth(baseline, reformed):
    state = baseline.calc("state_code", map_to="person")
    baseline_poverty = (
        baseline.calc("spm_unit_is_in_spm_poverty", map_to="person")
        .groupby(state)
        .mean()
    )
    reform_poverty = (
        reformed.calc("spm_unit_is_in_spm_poverty", map_to="person")
        .groupby(state)
        .mean()
    )
    rel_change = reform_poverty / baseline_poverty - 1
    df = pd.DataFrame(
        {
            "State": rel_change.index,
            "Gain": rel_change.values,
        }
    )
    df["Label"] = [
        f"The poverty rate in {state} {'increases' if gain >= 0 else 'falls'} by {abs(gain):.1%}"
        for state, gain in zip(df["State"], df["Gain"])
    ]
    fig = px.choropleth(
        locations=rel_change.index,
        color=-rel_change.values,
        locationmode="USA-states",
        scope="usa",
        custom_data=[df.Label],
    )
    fig.update_layout(
        title="Poverty rate reduction by U.S. State under Blank Slate UBI",
        coloraxis_colorbar_tickformat=".0%",
        coloraxis_colorbar_title="",
    )
    fig.update_traces(
        hovertemplate="%{customdata[0]}",
    )
    return format_fig(fig)
