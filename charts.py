"""Plotly figures. Colour comes only from theme.py; no chart invents its own."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from data import SHAPE_TO_GOV, corr
from theme import (BLUE, CARD, CONTEXT, FONT, GRID, MUTED, NO_DATA, ORANGE,
                   SEQUENTIAL, SURFACE, TEXT, TEXT_2)

# Fixed colour range so a governorate keeps its colour whatever the filter does
Z_MIN, Z_MAX = 3, 10


def _style(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=4, r=4, t=6, b=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=TEXT_2),
        hoverlabel=dict(bgcolor=CARD, bordercolor=GRID, font=dict(family=FONT, size=13, color=TEXT)),
        showlegend=False,
    )
    return fig


def map_fig(sel: pd.DataFrame, geojson: dict, shape_to_gov: dict) -> go.Figure:
    """Governorate choropleth of the *current selection*; the rest stays grey for context."""
    stats = sel.groupby("governorate")["illiterate"].agg(["mean", "count"])
    shapes = [f["id"] for f in geojson["features"]]
    line = dict(color=SURFACE, width=1.4)

    fig = go.Figure()
    fig.add_trace(go.Choropleth(
        geojson=geojson, featureidkey="id", locations=shapes, z=[0] * len(shapes),
        colorscale=[[0, NO_DATA], [1, NO_DATA]], showscale=False, marker=dict(line=line),
        text=["No town-level data (urban governorate)" if shape_to_gov[s] == "Beirut" else "Outside current selection" for s in shapes],
        customdata=[shape_to_gov[s] for s in shapes],
        hovertemplate="<b>%{customdata}</b><br>%{text}<extra></extra>",
    ))
    live = [s for s in shapes if shape_to_gov[s] in stats.index]
    if live:
        govs = [shape_to_gov[s] for s in live]
        fig.add_trace(go.Choropleth(
            geojson=geojson, featureidkey="id", locations=live,
            z=[stats.loc[g, "mean"] for g in govs],
            customdata=np.c_[govs, [int(stats.loc[g, "count"]) for g in govs]],
            colorscale=[[i / (len(SEQUENTIAL) - 1), c] for i, c in enumerate(SEQUENTIAL)],
            zmin=Z_MIN, zmax=Z_MAX, marker=dict(line=line),
            hovertemplate="<b>%{customdata[0]}</b><br>%{z:.1f}% illiterate<br>%{customdata[1]} towns<extra></extra>",
            colorbar=dict(title=dict(text="% illiterate", font=dict(size=12, color=TEXT_2)),
                          thickness=10, len=0.55, x=1.0, outlinewidth=0,
                          tickfont=dict(size=11, color=TEXT_2), ticksuffix="%"),
        ))
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor="rgba(0,0,0,0)")
    return _style(fig, 470)


def bar_fig(table: pd.DataFrame, level: str) -> go.Figure:
    """Ranked horizontal bars with standard-error whiskers and a direct value label."""
    t = table.copy()
    if level == "town":
        ylabels = [f"{a}  ·  {b}" for a, b in zip(t["label"], t["context"])]
        hover = "<b>%{y}</b><br>%{x:.1f}% illiterate<extra></extra>"
    else:
        ylabels = [f"{a}  (n={n})" for a, n in zip(t["label"], t["n"])]
        hover = "<b>%{y}</b><br>%{x:.1f}% illiterate ± %{error_x.array:.1f}<extra></extra>"

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=t["mean"], y=ylabels, orientation="h", marker=dict(color=BLUE, cornerradius=4),
        error_x=dict(type="data", array=t["se"], color=TEXT_2, thickness=1.4, width=4),
        hovertemplate=hover,
    ))
    reach = (t["mean"] + t["se"])
    fig.add_trace(go.Scatter(
        x=reach, y=ylabels, mode="text", text=[f"   {m:.1f}%" for m in t["mean"]],
        textposition="middle right", textfont=dict(color=TEXT, size=13), hoverinfo="skip",
    ))
    fig.update_xaxes(range=[0, max(reach.max() * 1.32, 1)], gridcolor=GRID, zeroline=False,
                     ticksuffix="%", tickfont=dict(color=MUTED))
    fig.update_yaxes(tickfont=dict(color=TEXT_2, size=12), automargin=True)
    fig.update_layout(bargap=0.38)
    return _style(fig, 470)


def scatter_fig(towns: pd.DataFrame, sel: pd.DataFrame) -> go.Figure:
    """Every town stays on the chart; the selection is drawn in colour, the rest recedes."""
    rng = np.random.default_rng(7)
    jitter = lambda d: d["schools"] + rng.uniform(-0.18, 0.18, len(d))  # integer counts overplot badly

    def hover(d):
        return np.c_[d["town"], d["district"], d["governorate"], d["schools"], d["illiterate"]]

    tmpl = ("<b>%{customdata[0]}</b><br>%{customdata[1]} · %{customdata[2]}"
            "<br>Schools: %{customdata[3]}<br>Illiterate: %{customdata[4]:.0f}%<extra></extra>")

    fig = go.Figure()
    rest = towns[~towns.index.isin(sel.index)]
    if len(rest):
        fig.add_trace(go.Scatter(
            x=jitter(rest), y=rest["illiterate"], mode="markers", name="Other towns",
            marker=dict(size=7, color=CONTEXT, opacity=0.4), customdata=hover(rest), hovertemplate=tmpl,
        ))
    fig.add_trace(go.Scatter(
        x=jitter(sel), y=sel["illiterate"], mode="markers", name="Selected towns",
        marker=dict(size=9, color=BLUE, opacity=0.85, line=dict(color=SURFACE, width=1.2)),
        customdata=hover(sel), hovertemplate=tmpl,
    ))
    r = corr(sel["schools"], sel["illiterate"])
    if not np.isnan(r):
        slope, intercept = np.polyfit(sel["schools"], sel["illiterate"], 1)
        xs = np.array([sel["schools"].min(), sel["schools"].max()])
        fig.add_trace(go.Scatter(
            x=xs, y=intercept + slope * xs, mode="lines", name="Trend (selected)",
            line=dict(color=ORANGE, width=2.5), hoverinfo="skip",
        ))
    fig.update_xaxes(title=dict(text="Schools in town (public + private)", font=dict(color=TEXT_2)),
                     gridcolor=GRID, zeroline=False, tickfont=dict(color=MUTED))
    fig.update_yaxes(title=dict(text="% of residents illiterate", font=dict(color=TEXT_2)),
                     gridcolor=GRID, zeroline=False, ticksuffix="%", tickfont=dict(color=MUTED))
    _style(fig, 480)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.08, x=0, font=dict(color=TEXT_2, size=12)))
    return fig
