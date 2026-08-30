import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from player_common import (
    PLAYER_METRICS, PLAYER_CAT_LABELS, PLAYER_CAT_ORDER, PLAYER_MATCHES_DIR,
    list_player_match_files,
)

st.set_page_config(page_title="Comparador de Futbolistas — LaLiga", layout="wide", page_icon="🆚")

st.title("🆚 Comparador de Futbolistas")
st.caption("Compara varios jugadores (de cualquier equipo que tengas cargado) en las métricas "
           "que quieras, con percentil frente a todos los jugadores disponibles en la plataforma.")


def fmt_val(v, is_pct):
    if v is None or pd.isna(v):
        return "—"
    if is_pct:
        return f"{v:.1f}%"
    if abs(v) < 10 and not float(v).is_integer():
        return f"{v:.2f}"
    return f"{v:.1f}" if not float(v).is_integer() else f"{v:.0f}"


@st.cache_data
def build_full_player_pool():
    """One row per player: their average across ALL matches available, plus their team."""
    frames = []
    for path in PLAYER_MATCHES_DIR.glob("*.csv"):
        df = pd.read_csv(path)
        if df.empty:
            continue
        df["__team_file__"] = path.stem
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    all_df = pd.concat(frames, ignore_index=True)
    numeric_cols = [c for k, c, l, cat, p in PLAYER_METRICS if c in all_df.columns]
    agg = all_df.groupby(["PlayerClean", "__team_file__"])[numeric_cols].mean(numeric_only=True).reset_index()
    agg = agg.rename(columns={"__team_file__": "Equipo"})
    return agg


pool_df = build_full_player_pool()

if pool_df.empty:
    st.info("Todavía no hay ningún jugador cargado. Sube partidos individuales en la página "
            "'Análisis Individual' o desde el panel de actualización de datos.")
    st.stop()

pool_df["Etiqueta"] = pool_df["PlayerClean"] + " (" + pool_df["Equipo"] + ")"

st.caption(f"**{len(pool_df)}** jugadores disponibles para comparar, de **{pool_df['Equipo'].nunique()}** equipos.")

# ---------------------------------------------------------------------------
# Selección de jugadores y métricas
# ---------------------------------------------------------------------------
metric_options = {f"{PLAYER_CAT_LABELS[cat]} · {label}": col
                  for key, col, label, cat, is_pct in PLAYER_METRICS if col in pool_df.columns}
label_by_col = {v: k for k, v in metric_options.items()}
is_pct_by_col = {col: is_pct for key, col, label, cat, is_pct in PLAYER_METRICS}

default_players = pool_df["Etiqueta"].tolist()[:3]
default_metrics = [label_by_col[c] for c in ["Goal", "Ast", "Chance", "Int", "Recovery"] if c in label_by_col]

col_a, col_b = st.columns([1, 1])
with col_a:
    selected_labels = st.multiselect("Jugadores a comparar", pool_df["Etiqueta"].tolist(),
                                      default=default_players, key="cmp_players")
with col_b:
    selected_metric_labels = st.multiselect("Métricas a comparar", list(metric_options.keys()),
                                             default=default_metrics, key="cmp_metrics")

chart_type = st.radio("Tipo de gráfico", ["Radar (percentil)", "Barras (valor real)"],
                       horizontal=True, key="cmp_chart_type")

selected_cols = [metric_options[l] for l in selected_metric_labels]

if len(selected_labels) < 2 or not selected_cols:
    st.info("Selecciona al menos 2 jugadores y 1 métrica para ver la comparativa.")
    st.stop()

sub = pool_df[pool_df["Etiqueta"].isin(selected_labels)]


def percentile_of(col, value):
    vals = pool_df[col].dropna()
    if len(vals) < 2 or pd.isna(value):
        return 0, len(vals), 0
    rank = int((vals > value).sum()) + 1
    n = len(vals)
    percentile = round(100 * (n - rank) / (n - 1)) if n > 1 else 100
    return rank, n, percentile


if chart_type.startswith("Radar"):
    fig = go.Figure()
    theta = [label_by_col[c].split(" · ")[-1] for c in selected_cols]
    for _, row in sub.iterrows():
        r_vals, hover = [], []
        for col in selected_cols:
            rank, n, pct = percentile_of(col, row[col])
            r_vals.append(pct)
            hover.append(f"{label_by_col[col]}<br>Valor: {fmt_val(row[col], is_pct_by_col.get(col, False))}"
                          f"<br>{rank}º de {n}")
        fig.add_trace(go.Scatterpolar(
            r=r_vals + [r_vals[0]], theta=theta + [theta[0]],
            fill="toself", name=row["Etiqueta"],
            text=hover + [hover[0]], hoverinfo="text",
        ))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                       height=560, showlegend=True,
                       title="Percentil entre los jugadores cargados (100 = mejor)")
    st.plotly_chart(fig, use_container_width=True)
else:
    fig = go.Figure()
    for _, row in sub.iterrows():
        y_vals, hover = [], []
        for col in selected_cols:
            y_vals.append(row[col])
            rank, n, pct = percentile_of(col, row[col])
            hover.append(f"{fmt_val(row[col], is_pct_by_col.get(col, False))} · {rank}º de {n}")
        fig.add_bar(name=row["Etiqueta"], x=[label_by_col[c].split(" · ")[-1] for c in selected_cols],
                    y=y_vals, text=hover, textposition="outside")
    fig.update_layout(barmode="group", height=520, title="Valor real por métrica")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("**Tabla de ranking**")
table_rows = []
for _, row in sub.iterrows():
    r = {"Jugador": row["Etiqueta"]}
    for col in selected_cols:
        rank, n, pct = percentile_of(col, row[col])
        r[label_by_col[col].split(" · ")[-1]] = f"{fmt_val(row[col], is_pct_by_col.get(col, False))} ({rank}º/{n})"
    table_rows.append(r)
st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
