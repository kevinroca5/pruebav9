import streamlit as st

st.set_page_config(page_title="Análisis de Partidos — LaLiga", layout="wide", page_icon="⚽")

st.title("⚽ Análisis de Partidos — LaLiga")
st.markdown("""
Usa el menú de la izquierda para moverte entre páginas:

- **🔴 Análisis Rival** — informe automático de fortalezas y debilidades de un equipo
  frente a la media de LaLiga, con filtros por partido, fecha, entrenador y métricas
  ofensivas/defensivas.
- **🔵 Análisis Propio** — gráficos de evolución de tu equipo partido a partido.
- **📊 Gráficos Comparativos** — mapa de cuadrantes para comparar los 20 equipos de
  LaLiga en dos métricas cualquiera, al estilo de un scouting board.

Todas las páginas comparten la misma biblioteca de equipos (`data/matches/`) — añade o
actualiza un equipo desde el panel "🔄 Actualizar datos" en Rival o Propio, y estará
disponible en todas partes.
""")
