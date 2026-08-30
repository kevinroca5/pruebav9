# Análisis de Partidos — LaLiga (multipágina, equipo + individual)

Plataforma de prueba dividida en "slides" (páginas) tipo Power BI, para analizar el
histórico de partidos de varios equipos y, ahora también, de sus jugadores.

## Páginas

1. **🔴 Análisis Rival** — informe general, fortalezas/debilidades automáticas vs. media
   de LaLiga (con percentil y ranking real), filtro por categoría de métrica (General,
   Ofensivas, Defensivas, Posesión y Estilo) con sliders, y ahora también un bloque
   **"🏅 Top 3 jugadores"** bajo cada tabla de métricas: si el equipo destaca en una
   métrica que también existe a nivel individual (ej. Centros, xG, Presiones altas),
   te dice qué 3 jugadores concretos la sostienen, en los mismos partidos seleccionados.
2. **🔵 Análisis Propio** — igual que Rival pero orientado a tu propio equipo, con
   gráficos de evolución por partido.
3. **📊 Gráficos Comparativos** — mapa de cuadrantes: cualquier métrica de equipo-temporada
   en el eje X y otra en el Y, comparando los 20 equipos de LaLiga.
4. **👤 Análisis Individual** *(nuevo)* — elige equipo y jugador: gráfico de progresión
   por jornada, ficha completa con las ~50 métricas individuales (Ofensivas/Defensivas/
   General) y su ranking frente a todos los jugadores cargados, e informe automático de
   "principales cualidades" (métricas donde el jugador más destaca, por z-score).
5. **🆚 Comparador** *(nuevo)* — compara 2 o más jugadores de cualquier equipo cargado,
   en cualquier métrica, con radar de percentil o barras de valor real.

## Dos fuentes de datos distintas

- **Equipo (por partido)**: `data/matches/{Equipo}.csv` — un archivo por equipo, un
  partido por fila (formato "KR" de TruMedia/Opta).
- **Individual (por partido)**: `data/player_matches/{Equipo}.csv` — un archivo por
  equipo, una fila por (jugador, partido) — viene de exports individuales de Opta,
  un CSV por partido con TODOS los jugadores de ambos equipos, que la plataforma separa
  automáticamente por equipo al cargarlos.

Las páginas 1, 2 y 4 cruzan ambas fuentes cuando existe una métrica con el mismo nombre
de columna en las dos (ahora mismo 13 métricas coinciden exactamente: Crosses, BgChnc,
ExpG, FwdPass, FwdPass%, %PassFwd, HighPrsrApp, LBP, LBPOwnHalf, ProgCarry,
Recuperaciones entre 5/10 segundos %, juego interior).

## Instalación

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Añadir un partido individual nuevo

1. Consigue el CSV de Opta con todos los jugadores de un partido (un archivo por partido,
   con columnas Team, Player, Min y las métricas — mismo formato que ya tienes).
2. El nombre del archivo debe seguir el patrón `YYYY-MM-DD_XXX-YYY.csv` (fecha y los
   códigos de 3 letras de ambos equipos) — de ahí saca la plataforma la fecha y el rival.
3. Colócalo procesado en `data/player_matches/` (por ahora, pide que se ingeste con
   `player_common.ingest_match_file()` o pégamelo a mí para que lo procese).

**Importante**: para que el cruce equipo↔jugador y el filtro por partido funcionen, el
equipo también necesita una entrada en `data/matches/{Equipo}.csv` con la misma fecha
— si el partido es de una temporada/fecha que el CSV de equipo aún no tiene, hay que
añadirla (se puede extraer de la fila "total del equipo" que trae el mismo CSV individual).

## Añadir o actualizar un equipo (nivel equipo)

Desde el panel **"🔄 Actualizar datos de un equipo"** (disponible en Rival y Propio):
sube el export semanal, se fusiona sin duplicar por `gameId`, y descargas el CSV
combinado para guardarlo en `data/matches/`.

## Estructura de archivos

```
app.py                              # página de bienvenida / índice
common.py                           # catálogo de métricas de equipo, carga, filtros, cruce con jugadores
player_common.py                    # catálogo de métricas individuales, ingesta de partidos
data.json                           # equipo-temporada de los 20 equipos de LaLiga (benchmarks)
data/matches/*.csv                  # biblioteca de partidos por equipo
data/player_matches/*.csv           # biblioteca de partidos por jugador, agrupada por equipo
pages/
  1_🔴_Analisis_Rival.py
  2_🔵_Analisis_Propio.py
  3_📊_Graficos_Comparativos.py
  4_👤_Analisis_Individual.py
  5_🆚_Comparador.py
requirements.txt
```

## Limitaciones conocidas

- El cruce equipo↔jugador solo funciona para las 13 métricas cuyo nombre de columna
  coincide exactamente entre ambas fuentes — el resto de métricas de equipo no tienen
  aún un desglose individual disponible.
- El ranking de jugadores en las páginas 4 y 5 se calcula sobre los jugadores que
  tengas cargados hasta ahora en la plataforma (crece según subas más partidos), no
  sobre toda LaLiga.
- Si un partido no tiene aún entrada a nivel de equipo en `data/matches/`, no aparecerá
  como filtrable ahí ni se podrá cruzar con los datos individuales de ese partido.
