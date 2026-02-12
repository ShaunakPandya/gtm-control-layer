"""Shared chart helpers — static, polished Altair charts with no scroll zoom."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

CHART_HEIGHT = 320
BAR_COLOR = "#6C63FF"
GRID_COLOR = "#2A2D38"
LABEL_COLOR = "#A0A3B1"
TITLE_COLOR = "#FAFAFA"

_BASE_CONFIG = {
    "background": "transparent",
    "font": "sans-serif",
    "axis": {
        "labelColor": LABEL_COLOR,
        "titleColor": LABEL_COLOR,
        "gridColor": GRID_COLOR,
        "gridOpacity": 0.4,
        "domainColor": GRID_COLOR,
        "tickColor": GRID_COLOR,
        "labelFontSize": 11,
        "titleFontSize": 12,
        "titlePadding": 12,
    },
    "title": {
        "color": TITLE_COLOR,
        "fontSize": 14,
        "fontWeight": 600,
        "anchor": "middle",
        "offset": 12,
    },
    "view": {
        "strokeWidth": 0,
    },
}


def static_bar_chart(
    data: dict[str, int] | list[dict],
    x_label: str = "Category",
    y_label: str = "Count",
    title: str = "",
    height: int = CHART_HEIGHT,
) -> None:
    """Render a static vertical bar chart with consistent styling."""
    if isinstance(data, dict):
        df = pd.DataFrame([{x_label: k, y_label: v} for k, v in data.items()])
    else:
        df = pd.DataFrame(data)
        cols = df.columns.tolist()
        if x_label not in cols:
            df = df.rename(columns={cols[0]: x_label, cols[1]: y_label})

    if df.empty:
        st.info("No data to display.")
        return

    chart = (
        alt.Chart(df)
        .mark_bar(
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
            size=max(8, min(40, 240 // max(len(df), 1))),
        )
        .encode(
            x=alt.X(
                f"{x_label}:N",
                sort=alt.SortField(field=y_label, order="descending"),
                title=None,
                axis=alt.Axis(labelAngle=0, labelLimit=120),
            ),
            y=alt.Y(
                f"{y_label}:Q",
                title=y_label,
                axis=alt.Axis(grid=True, tickMinStep=1),
            ),
            color=alt.value(BAR_COLOR),
            tooltip=[
                alt.Tooltip(f"{x_label}:N"),
                alt.Tooltip(f"{y_label}:Q", format=","),
            ],
        )
        .properties(
            **{"height": height, "padding": {"left": 16, "right": 16, "top": 12, "bottom": 12}, **({"title": title} if title else {})},
        )
        .configure(**_BASE_CONFIG)
    )

    st.altair_chart(chart, use_container_width=True)
