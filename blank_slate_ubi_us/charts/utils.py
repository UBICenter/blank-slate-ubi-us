import plotly.graph_objects as go


def add_numbers(fig: go.Figure, axis="y") -> go.Figure:
    for i, trace in enumerate(fig.data):
        for bar in trace:
            fig.data[i].text = getattr(bar, axis)
    return fig
