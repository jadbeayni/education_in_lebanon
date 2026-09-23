"""Plotly figures. Every chart draws from the same units table, so they always agree."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from theme import BLUE, GRID, NO_DATA, ORANGE, SEQUENTIAL, TEXT, TEXT_2, WHITE

Z_MIN, Z_MAX = 3, 10   # fixed colour range: a governorate keeps its colour whatever the filter does
TOP_N = 15             # rows shown when the chart drills down to individual towns


def _style(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=4, r=4, t=8, b=4),
        paper_bgcolor=WHITE, plot_bgcolor=WHITE,
        font=dict(size=13, color=TEXT_2), showlegend=False,
        hoverlabel=dict(bgcolor=WHITE, font=dict(color=TEXT)),
    )
    return fig


def _top(units: pd.DataFrame, level: str) -> pd.DataFrame:
    """Rows drawn as bars: everything, or the TOP_N towns; ordered so the largest sits on top."""
    rows = units.head(TOP_N) if level == "town" else units
    return rows.iloc[::-1]


def _gap(n: int) -> float:
    """Bar gap that keeps bars a sensible thickness whether there are 2 rows or 15."""
    return 0.35 if n >= 6 else 0.55 if n >= 3 else 0.75


def _names(rows: pd.DataFrame, level: str) -> list[str]:
    if level == "town":
        return [f"{a} ({b})" for a, b in zip(rows["label"], rows["context"])]
    return [f"{a} ({n} towns)" for a, n in zip(rows["label"], rows["n"])]


def map_fig(sel: pd.DataFrame, geojson: dict, shape_to_gov: dict) -> go.Figure:
    """Average illiteracy by governorate for the towns in view; governorates outside the selection stay grey."""
    stats = sel.groupby("governorate")["illiterate"].agg(["mean", "count"])
    shapes = [f["id"] for f in geojson["features"]]
    edge = dict(color=WHITE, width=1.2)

    fig = go.Figure()
    fig.add_trace(go.Choropleth(
        geojson=geojson, featureidkey="id", locations=shapes, z=[0] * len(shapes),
        colorscale=[[0, NO_DATA], [1, NO_DATA]], showscale=False, marker=dict(line=edge),
        text=["No data for Beirut" if shape_to_gov[s] == "Beirut" else "Not in selection" for s in shapes],
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
            zmin=Z_MIN, zmax=Z_MAX, marker=dict(line=edge),
            hovertemplate="<b>%{customdata[0]}</b><br>%{z:.1f}% illiterate<br>%{customdata[1]} towns<extra></extra>",
            colorbar=dict(title=dict(text="% illiterate", font=dict(size=12)), thickness=12, len=0.6,
                          outlinewidth=0, tickfont=dict(size=11), ticksuffix="%"),
        ))
    fig.update_geos(fitbounds="locations", visible=False, projection_type="mercator", bgcolor=WHITE)
    return _style(fig, 430)


def ranking_fig(units: pd.DataFrame, level: str) -> go.Figure:
    rows = _top(units, level)
    names = _names(rows, level)
    fig = go.Figure(go.Bar(
        x=rows["illiterate"], y=names, orientation="h", marker=dict(color=BLUE),
        text=[f"{v:.1f}%" for v in rows["illiterate"]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{x:.1f}% illiterate<extra></extra>",
    ))
    fig.update_xaxes(range=[0, max(rows["illiterate"].max() * 1.2, 1)], gridcolor=GRID, ticksuffix="%", zeroline=False)
    fig.update_yaxes(automargin=True, tickfont=dict(color=TEXT))
    fig.update_layout(bargap=_gap(len(rows)))
    return _style(fig, 430)


def dropout_fig(units: pd.DataFrame, level: str) -> go.Figure:
    """Illiteracy against school dropout: one dot per governorate, district or town."""
    d = units.dropna(subset=["dropout"])
    # name every dot when there are few; otherwise only the highest-illiteracy ones (labels would collide)
    named = set(d.index) if len(d) <= 7 else set(d.nlargest(3, "illiterate").index)
    labels = [name if (level != "town" and i in named) else "" for i, name in zip(d.index, d["label"])]
    fig = go.Figure(go.Scatter(
        x=d["illiterate"], y=d["dropout"], mode="markers+text",
        text=labels, textposition="top center", textfont=dict(size=12, color=TEXT),
        marker=dict(size=13 if level != "town" else 8, color=BLUE, opacity=0.85 if level != "town" else 0.55,
                    line=dict(color=WHITE, width=1)),
        customdata=np.c_[d["label"], d["n"]],
        hovertemplate="<b>%{customdata[0]}</b><br>%{x:.1f}% illiterate<br>%{y:.1f}% dropout<extra></extra>",
    ))
    # leave room either side so point labels are never cut off
    x_pad = max((d["illiterate"].max() - d["illiterate"].min()) * 0.22, 1)
    y_pad = max((d["dropout"].max() - d["dropout"].min()) * 0.15, 0.5)
    fig.update_xaxes(title="Illiterate residents (%)", gridcolor=GRID, zeroline=False, ticksuffix="%",
                     range=[max(d["illiterate"].min() - x_pad, 0), d["illiterate"].max() + x_pad])
    fig.update_yaxes(title="School dropout (%)", gridcolor=GRID, zeroline=False, ticksuffix="%",
                     range=[max(d["dropout"].min() - y_pad, 0), d["dropout"].max() + y_pad])
    return _style(fig, 400)


def schools_fig(units: pd.DataFrame, level: str) -> go.Figure:
    """Public and private schools, in the same order as the ranking chart."""
    rows = _top(units, level)
    names = _names(rows, level)
    per = "per town, on average" if level != "town" else "in the town"
    fig = go.Figure()
    fig.add_trace(go.Bar(x=rows["public"], y=names, orientation="h", name="Public", marker=dict(color=BLUE),
                         hovertemplate="<b>%{y}</b><br>%{x:.1f} public schools<extra></extra>"))
    fig.add_trace(go.Bar(x=rows["private"], y=names, orientation="h", name="Private", marker=dict(color=ORANGE),
                         hovertemplate="<b>%{y}</b><br>%{x:.1f} private schools<extra></extra>"))
    total = rows["public"] + rows["private"]
    fig.add_trace(go.Scatter(x=total, y=names, mode="text", text=[f"  {v:.1f}" for v in total],
                             textposition="middle right", textfont=dict(color=TEXT), hoverinfo="skip", showlegend=False))
    fig.update_xaxes(title=f"Schools {per}", range=[0, max(total.max() * 1.18, 1)], gridcolor=GRID, zeroline=False)
    fig.update_yaxes(automargin=True, tickfont=dict(color=TEXT))
    fig.update_layout(barmode="stack", bargap=_gap(len(rows)))
    _style(fig, 400)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.07, x=0, traceorder="normal"))
    return fig
