import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import (
    CAT_BY_KEY, CAT_LABELS, CAT_ORDER, METRICS, get_combined_league_benchmarks,
    render_team_picker_and_updater, render_match_selection_sidebar,
    render_metric_category_report, render_mode_toggle,
)

st.set_page_config(page_title="Análisis Propio — LaLiga", layout="wide", page_icon="🔵")

st.title("🔵 Análisis Propio")
st.caption("Cómo va evolucionando tu equipo partido a partido, en las métricas que elijas.")

team_name, matches, has_coach_column = render_team_picker_and_updater(key_prefix="propio")
league_benchmarks = get_combined_league_benchmarks()
selected_matches, total_matches = render_match_selection_sidebar(team_name, matches, key_prefix="propio")
if not selected_matches:
    st.warning("No hay partidos seleccionados con estos filtros.")
    st.stop()

st.caption(f"**{len(selected_matches)}** partidos seleccionados de **{total_matches}** disponibles en el CSV.")

with st.expander("Ver partidos seleccionados"):
    tbl = pd.DataFrame([{
        "Fecha": m["date"].split(" ")[0] if m["date"] else "?",
        "Rival": m["opponent"], "Local/Visit.": "Local" if m["home"] else "Visitante",
        "Resultado": m["resultLabel"], "Entrenador": m.get("coach") or "—",
    } for m in selected_matches])
    st.dataframe(tbl, use_container_width=True, hide_index=True)

st.divider()

mode = render_mode_toggle(key_prefix="propio")

st.subheader("📊 Métricas por categoría (con ranking en LaLiga)")
st.caption("Ofensivas, Defensivas, Posesión y General. Muestra el valor de cada métrica "
           "en los partidos seleccionados (total o por partido, según el modo elegido "
           "arriba) y su ranking real entre los 20 equipos de LaLiga.")
render_metric_category_report(selected_matches, league_benchmarks, key_prefix="propio", mode=mode)

st.divider()

# ---------------------------------------------------------------------------
# Evolución por partido
# ---------------------------------------------------------------------------
st.subheader("📈 Evolución de nuestro rendimiento")
st.caption("Cómo van cambiando nuestras métricas partido a partido, en orden cronológico.")

evo_cat = st.selectbox("Categoría de métricas", CAT_ORDER, format_func=lambda c: CAT_LABELS[c], key="evo_cat")
evo_metric_options = {m["label"]: m["key"] for m in CAT_BY_KEY.values() if m["cat"] == evo_cat}
evo_selected_labels = st.multiselect("Métricas a graficar", list(evo_metric_options.keys()),
                                      default=list(evo_metric_options.keys())[:2], key="evo_metrics")
show_rolling = st.checkbox("Mostrar media móvil (últimos 5 partidos)", value=True)

selected_sorted = sorted(selected_matches, key=lambda m: m["date"] or "")
x_labels = [f"{m['date'].split(' ')[0]}<br>{m['opponent']}" for m in selected_sorted]
outcome_colors = {"W": "#5c9468", "D": "#c9a227", "L": "#c1443c"}

if not evo_selected_labels:
    st.info("Selecciona al menos una métrica para ver su evolución.")
else:
    fig_evo = go.Figure()
    for label in evo_selected_labels:
        key = evo_metric_options[label]
        y_vals = [m["metrics"].get(key) for m in selected_sorted]
        fig_evo.add_trace(go.Scatter(x=x_labels, y=y_vals, mode="lines+markers", name=label))
        if show_rolling and len(y_vals) >= 5:
            roll = pd.Series(y_vals).rolling(5, min_periods=1).mean()
            fig_evo.add_trace(go.Scatter(x=x_labels, y=roll, mode="lines", name=f"{label} (media móvil 5)",
                                          line=dict(dash="dot")))
    fig_evo.update_layout(height=480, hovermode="x unified",
                           title="Evolución por partido (orden cronológico)")
    st.plotly_chart(fig_evo, use_container_width=True)

    fig_res = go.Figure()
    fig_res.add_bar(x=x_labels, y=[1] * len(selected_sorted),
                     marker_color=[outcome_colors.get(m["outcome"], "#888") for m in selected_sorted],
                     text=[m["resultLabel"] for m in selected_sorted], textposition="inside",
                     hoverinfo="text")
    fig_res.update_layout(height=120, showlegend=False, yaxis=dict(visible=False),
                           margin=dict(t=10, b=10), title=None)
    st.plotly_chart(fig_res, use_container_width=True)
