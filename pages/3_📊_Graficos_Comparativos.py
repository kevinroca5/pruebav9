import statistics

import plotly.graph_objects as go
import streamlit as st

from common import load_league_data

st.set_page_config(page_title="Gráficos Comparativos — LaLiga", layout="wide", page_icon="📊")

st.title("📊 Gráficos Comparativos")
st.caption("Mapa de cuadrantes: compara los 20 equipos de LaLiga 24/25 en dos métricas "
           "cualquiera, con líneas de referencia en la media de la liga — al estilo de un "
           "scouting board.")

league_data = load_league_data()
teams = league_data["teams"]
catalog = league_data["catalog"]
cat_by_key = {m["key"]: m for m in catalog}

CAT_LABELS_COLLECTIVE = {
    "general": "General", "tiros": "Tiros", "centros": "Centros", "pases": "Pases",
    "defensa": "Defensa", "creacion": "Creación", "regates": "Regates y 1v1",
    "progresion": "Progresión", "presion": "Presión", "fisico": "Físico",
    "posesion": "Posesión", "periodos": "Periodos",
}
CAT_ORDER_COLLECTIVE = list(CAT_LABELS_COLLECTIVE.keys())


def build_dataframe(mode: str):
    import pandas as pd
    rows = []
    for t in teams:
        row = {"Equipo": t["team"], "Color": t["color"], "PJ": t["gm"]}
        for m in catalog:
            v = t["metrics"].get(m["key"])
            if v is not None and mode == "p90" and not m["pct"] and not m["p90"]:
                v = v / t["gm"] if t["gm"] else v
            row[m["key"]] = v
        rows.append(row)
    return pd.DataFrame(rows)


def fmt_value(v, meta):
    if v is None:
        return "—"
    if meta["pct"]:
        return f"{v:.1f}%"
    if abs(v) < 10 and not float(v).is_integer():
        return f"{v:.2f}"
    if abs(v) < 100:
        return f"{v:.1f}"
    return f"{v:,.0f}"


mode = st.radio("Modo", ["total", "p90"], format_func=lambda x: "Total" if x == "total" else "Por 90'",
                horizontal=True, key="graf_mode")
df = build_dataframe(mode)

col_x, col_y = st.columns(2)
with col_x:
    st.markdown("**Eje X**")
    cat_x = st.selectbox("Categoría", CAT_ORDER_COLLECTIVE, format_func=lambda c: CAT_LABELS_COLLECTIVE[c], key="cat_x")
    options_x = {m["label"]: m["key"] for m in catalog if m["cat"] == cat_x}
    x_labels_list = list(options_x.keys())
    default_x_idx = x_labels_list.index("Posesión %") if "Posesión %" in x_labels_list else 0
    label_x = st.selectbox("Métrica", x_labels_list, index=default_x_idx, key="metric_x")
    key_x = options_x[label_x]
with col_y:
    st.markdown("**Eje Y**")
    cat_y = st.selectbox("Categoría", CAT_ORDER_COLLECTIVE, format_func=lambda c: CAT_LABELS_COLLECTIVE[c],
                          index=CAT_ORDER_COLLECTIVE.index("tiros") if "tiros" in CAT_ORDER_COLLECTIVE else 1,
                          key="cat_y")
    options_y = {m["label"]: m["key"] for m in catalog if m["cat"] == cat_y}
    y_labels_list = list(options_y.keys())
    default_y_idx = y_labels_list.index("xG total") if "xG total" in y_labels_list else 0
    label_y = st.selectbox("Métrica", y_labels_list, index=default_y_idx, key="metric_y")
    key_y = options_y[label_y]

ref_line = st.radio("Líneas de referencia en", ["Media de LaLiga", "Mediana de LaLiga"], horizontal=True, key="ref_line")

plot_df = df.dropna(subset=[key_x, key_y])
if plot_df.empty:
    st.warning("No hay datos suficientes para estas dos métricas.")
    st.stop()

x_vals = plot_df[key_x].tolist()
y_vals = plot_df[key_y].tolist()
if ref_line == "Media de LaLiga":
    x_ref, y_ref = statistics.mean(x_vals), statistics.mean(y_vals)
else:
    x_ref, y_ref = statistics.median(x_vals), statistics.median(y_vals)

fig = go.Figure()
fig.add_vline(x=x_ref, line_dash="dash", line_color="#2e7d32")
fig.add_hline(y=y_ref, line_dash="dash", line_color="#2e7d32")

for _, row in plot_df.iterrows():
    fig.add_trace(go.Scatter(
        x=[row[key_x]], y=[row[key_y]], mode="markers+text",
        marker=dict(size=14, color=row["Color"] or "#888", line=dict(width=1, color="white")),
        text=[row["Equipo"]], textposition="top center",
        name=row["Equipo"],
        hovertext=f"{row['Equipo']}<br>{label_x}: {fmt_value(row[key_x], cat_by_key[key_x])}"
                  f"<br>{label_y}: {fmt_value(row[key_y], cat_by_key[key_y])}",
        hoverinfo="text", showlegend=False,
    ))

fig.update_layout(
    height=680,
    xaxis_title=label_x, yaxis_title=label_y,
    title=f"{label_y} vs. {label_x} — LaLiga 24/25 ({'Total' if mode=='total' else 'Por 90'})",
    plot_bgcolor="white",
)
st.plotly_chart(fig, use_container_width=True)

st.caption(f"Líneas verdes discontinuas: {ref_line.lower()} entre los 20 equipos. "
           "Cada cuadrante agrupa equipos con un perfil similar en estas dos métricas.")

with st.expander("Ver tabla de datos"):
    show_df = plot_df[["Equipo", key_x, key_y]].rename(columns={key_x: label_x, key_y: label_y})
    st.dataframe(show_df.sort_values(label_x, ascending=False), use_container_width=True, hide_index=True)
