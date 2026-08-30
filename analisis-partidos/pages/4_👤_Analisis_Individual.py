import statistics

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import render_team_picker_and_updater, render_match_selection_sidebar
from player_common import (
    PLAYER_METRICS, PLAYER_CAT_LABELS, PLAYER_CAT_ORDER, PLAYER_CAT_BY_KEY,
    load_player_matches, render_player_data_updater,
)

st.set_page_config(page_title="Análisis Individual — LaLiga", layout="wide", page_icon="👤")

st.title("👤 Análisis Individual")
st.caption("Progresión, ficha completa y cualidades automáticas de un jugador, a partir de "
           "los partidos individuales (Opta) que hayas cargado para su equipo.")

render_player_data_updater(key_prefix="indiv")


def fmt_val(v, is_pct):
    if v is None or pd.isna(v):
        return "—"
    if is_pct:
        return f"{v:.1f}%"
    if abs(v) < 10 and not float(v).is_integer():
        return f"{v:.2f}"
    return f"{v:.1f}" if not float(v).is_integer() else f"{v:.0f}"


# ---------------------------------------------------------------------------
# Selección de equipo y partidos (mismo patrón que Rival/Propio)
# ---------------------------------------------------------------------------
team_name, matches, has_coach_column = render_team_picker_and_updater(key_prefix="indiv")
selected_matches, total_matches = render_match_selection_sidebar(team_name, matches, key_prefix="indiv")
if not selected_matches:
    st.warning("No hay partidos seleccionados con estos filtros.")
    st.stop()

dates_in_scope = {m["_game_date"] for m in selected_matches if m.get("_game_date")}

from player_common import TEAM_CODE_TO_NAME
team_display = TEAM_CODE_TO_NAME.get(team_name, team_name)
pdf_all = load_player_matches(team_display)

if pdf_all.empty:
    st.info(f"Todavía no hay datos individuales cargados para **{team_display}**. Sube un CSV de "
            f"partido (formato Opta individual) y actualiza `data/player_matches/{team_display}.csv`.")
    st.stop()

pdf = pdf_all[pdf_all["Date"].isin(dates_in_scope)] if dates_in_scope else pdf_all
if pdf.empty:
    st.warning("No hay datos individuales para los partidos seleccionados con estos filtros.")
    st.stop()

st.caption(f"**{pdf['GameKey'].nunique()}** partido(s) con datos individuales dentro de tu selección "
           f"de {len(selected_matches)} partidos filtrados.")

# ---------------------------------------------------------------------------
# Selector de jugador
# ---------------------------------------------------------------------------
players_available = sorted(pdf["PlayerClean"].unique())
selected_player = st.selectbox("Selecciona un jugador", players_available, key="indiv_player_select")
pdf_player = pdf[pdf["PlayerClean"] == selected_player].sort_values("Date")

st.divider()

# ---------------------------------------------------------------------------
# Resumen rápido
# ---------------------------------------------------------------------------
n_matches_player = pdf_player["GameKey"].nunique()
total_min = pdf_player["Min"].sum()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Partidos con datos", n_matches_player)
c2.metric("Minutos totales", f"{total_min:.0f}" if pd.notna(total_min) else "—")
c3.metric("Goles", f"{pdf_player['Goal'].sum():.0f}" if "Goal" in pdf_player else "—")
c4.metric("Asistencias", f"{pdf_player['Ast'].sum():.0f}" if "Ast" in pdf_player else "—")

st.divider()

# ---------------------------------------------------------------------------
# Ficha completa del jugador (todas las categorías, con ranking dentro del pool cargado)
# Haz clic en una fila para ver su evolución por jornada más abajo.
# ---------------------------------------------------------------------------
st.subheader("📋 Ficha completa")
st.caption("Promedio del jugador en los partidos seleccionados, con su ranking frente a todos "
           "los jugadores que tengas cargados en la plataforma. **Haz clic en una fila** para "
           "ver su evolución por jornada en la sección de abajo.")


@st.cache_data
def build_player_pool():
    """Loads every team's player-match library and returns one row per player with
    their average across ALL their available matches (their personal season average
    within what's been uploaded so far)."""
    from player_common import PLAYER_MATCHES_DIR
    frames = []
    for path in PLAYER_MATCHES_DIR.glob("*.csv"):
        df = pd.read_csv(path)
        if df.empty:
            continue
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    all_df = pd.concat(frames, ignore_index=True)
    numeric_cols = [c for k, c, l, cat, p in PLAYER_METRICS if c in all_df.columns]
    agg = all_df.groupby("PlayerClean")[numeric_cols].mean(numeric_only=True).reset_index()
    return agg


pool_df = build_player_pool()

rows = []
for cat in PLAYER_CAT_ORDER:
    for key, col, label, c, is_pct in PLAYER_METRICS:
        if c != cat or col not in pdf_player.columns:
            continue
        vals = pdf_player[col].dropna()
        if vals.empty:
            continue
        val = vals.mean()
        row = {"Categoría": PLAYER_CAT_LABELS[cat], "Métrica": label, "Valor": fmt_val(val, is_pct),
               "_col": col}
        if not pool_df.empty and col in pool_df.columns:
            pool_vals = pool_df[col].dropna()
            if len(pool_vals) >= 2:
                rank = int((pool_vals >= val).sum())
                n = len(pool_vals)
                row["Ranking"] = f"{rank}º de {n} jugadores"
            else:
                row["Ranking"] = "muestra insuficiente"
        else:
            row["Ranking"] = "sin comparativa"
        rows.append(row)

df_ficha = pd.DataFrame(rows)
table_key = f"indiv_ficha_table_{selected_player}"
event = st.dataframe(
    df_ficha.drop(columns="_col"), use_container_width=True, hide_index=True,
    on_select="rerun", selection_mode="single-row", key=table_key,
)

selected_metric_col = None
selected_metric_label = None
sel_rows = event.selection.rows if event and event.selection else []
if sel_rows:
    picked = df_ficha.iloc[sel_rows[0]]
    selected_metric_col = picked["_col"]
    selected_metric_label = picked["Métrica"]

st.divider()

# ---------------------------------------------------------------------------
# Evolución por jornada — sigue la fila que hayas clicado en la ficha de arriba
# ---------------------------------------------------------------------------
st.subheader("📈 Progresión por jornada")

if len(pdf_player) < 2:
    st.info("Este jugador solo tiene datos de 1 partido en tu biblioteca — sube más partidos "
            "para ver la evolución por jornada.")
elif selected_metric_col:
    x_labels = [f"{d}<br>vs {opp}" for d, opp in zip(pdf_player["Date"], pdf_player["Opponent"])]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x_labels, y=pdf_player[selected_metric_col],
                              mode="lines+markers", name=selected_metric_label))
    fig.update_layout(height=420, hovermode="x unified",
                       title=f"{selected_metric_label} — evolución de {selected_player}")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("👆 Haz clic en una fila de la tabla de arriba para ver aquí su evolución partido a partido.")

st.divider()

# ---------------------------------------------------------------------------
# Informe automático de cualidades principales
# ---------------------------------------------------------------------------
st.subheader("🔎 Informe automático — Principales cualidades")
st.caption("Métricas donde este jugador destaca más frente al resto de jugadores cargados "
           "en la plataforma (z-score sobre la muestra disponible).")

standouts = []
for key, col, label, cat, is_pct in PLAYER_METRICS:
    if col not in pdf_player.columns or pool_df.empty or col not in pool_df.columns:
        continue
    vals = pdf_player[col].dropna()
    if vals.empty:
        continue
    val = vals.mean()
    pool_vals = pool_df[col].dropna()
    if len(pool_vals) < 3:
        continue
    mean = pool_vals.mean()
    std = pool_vals.std() or 1.0
    z = (val - mean) / std
    standouts.append({"label": label, "value": val, "z": z, "is_pct": is_pct})

standouts.sort(key=lambda s: -s["z"])
top_qualities = [s for s in standouts if s["z"] >= 0.3][:6]

if not top_qualities:
    st.info("Aún no hay muestra suficiente de otros jugadores para generar un informe fiable. "
            "Sube más partidos de más equipos para activar esta comparativa.")
else:
    for s in top_qualities:
        st.write(f"🟢 **{s['label']}**: {fmt_val(s['value'], s['is_pct'])} "
                 f"(z={s['z']:.1f} frente al resto de jugadores cargados)")
