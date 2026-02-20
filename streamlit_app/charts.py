"""Shared chart helpers — static, polished Altair charts with no scroll zoom."""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

CHART_HEIGHT = 320
# Deep Ocean palette
BAR_COLOR = "#3B82F6"  # Bright blue for readability on dark background
BAR_HOVER_COLOR = "#1E3A8A"  # Darker navy on hover
ACCENT_COLOR = "#F59E0B"  # Amber accent
GRID_COLOR = "#334155"  # Dark slate grid for dark background
LABEL_COLOR = "#94A3B8"  # Light slate labels for dark background
TITLE_COLOR = "#E2E8F0"  # Light grey title for dark background

_BASE_CONFIG = {
    "background": "#0F172A",
    "font": "Fira Sans, sans-serif",
    "axis": {
        "labelColor": LABEL_COLOR,
        "titleColor": LABEL_COLOR,
        "gridColor": GRID_COLOR,
        "gridOpacity": 0.2,
        "domainColor": GRID_COLOR,
        "tickColor": GRID_COLOR,
        "labelFontSize": 11,
        "titleFontSize": 12,
        "titlePadding": 12,
    },
    "title": {
        "color": TITLE_COLOR,
        "fontSize": 16,
        "fontWeight": 600,
        "anchor": "start",
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
    label_mapping: dict[str, str] | None = None,
) -> None:
    """Render a static vertical bar chart with consistent styling and percentage tooltips.

    Args:
        label_mapping: Optional dict to map x-axis values to display labels
    """
    if isinstance(data, dict):
        df = pd.DataFrame([{x_label: k, y_label: v} for k, v in data.items()])
    else:
        df = pd.DataFrame(data)
        cols = df.columns.tolist()
        if x_label not in cols:
            df = df.rename(columns={cols[0]: x_label, cols[1]: y_label})

    # Apply label mapping for display if provided
    if label_mapping:
        df["_display_label"] = df[x_label].map(lambda x: label_mapping.get(x, x))
        display_field = "_display_label"
    else:
        display_field = x_label

    if df.empty:
        st.info("No data to display.")
        return

    # Calculate percentages for tooltips
    total = df[y_label].sum()
    if total > 0:
        df["Percentage"] = (df[y_label] / total * 100).round(1)
    else:
        df["Percentage"] = 0

    # Build chart with hover interactivity
    chart = (
        alt.Chart(df)
        .mark_bar(
            cornerRadiusTopLeft=6,
            cornerRadiusTopRight=6,
            size=max(12, min(50, 280 // max(len(df), 1))),
        )
        .encode(
            x=alt.X(
                f"{display_field}:N",
                sort=alt.SortField(field=y_label, order="descending"),
                title=None,
                axis=alt.Axis(labelAngle=0, labelLimit=150, labelFontWeight=500),
            ),
            y=alt.Y(
                f"{y_label}:Q",
                title=y_label,
                axis=alt.Axis(grid=True, tickMinStep=1),
            ),
            color=alt.value(BAR_COLOR),
            opacity=alt.value(0.9),
            tooltip=[
                alt.Tooltip(f"{display_field}:N", title=x_label),
                alt.Tooltip(f"{y_label}:Q", title="Count", format=","),
                alt.Tooltip("Percentage:Q", title="%", format=".1f"),
            ],
        )
        .properties(
            height=height,
            padding={"left": 16, "right": 16, "top": 12, "bottom": 12},
            **({"title": title} if title else {}),
        )
        .configure(**_BASE_CONFIG)
    )

    st.altair_chart(chart, use_container_width=True)
