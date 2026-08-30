"""
Módulo compartido por las páginas de la app: catálogo de métricas, carga de datos,
benchmarks de liga, y componentes de filtro reutilizables (fecha, partido, entrenador,
y sliders por categoría de métrica).
"""
import json
import re
import statistics
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).parent
LEAGUE_DATA_PATH = APP_DIR / "data.json"
MATCHES_DIR = APP_DIR / "data" / "matches"
MATCHES_DIR.mkdir(parents=True, exist_ok=True)
LOGOS_DIR = APP_DIR / "assets" / "logos"
LOGOS_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_BADGES_DIR = APP_DIR / "assets" / "badges_generated"
GENERATED_BADGES_DIR.mkdir(parents=True, exist_ok=True)

# Column names that might hold the coach/manager, checked case-insensitively.
COACH_COLUMN_CANDIDATES = ["TeamManager", "Team Manager", "Manager", "Entrenador", "Coach", "teamManager"]

CAT_LABELS = {
    "general": "General",
    "ofensivas": "Ofensivas",
    "defensivas": "Defensivas",
    "posesion": "Posesión y Estilo",
}
CAT_ORDER = ["general", "ofensivas", "defensivas", "posesion"]

# key, col, label, cat, pct
# col=None means the value is computed after parsing (gf/ga/gd/puntos), not read directly.
METRICS = [
    # GENERAL (contexto de resultado — visible aquí, pero NO como titular del informe)
    ("gf", None, "Goles a favor", "general", False),
    ("ga", None, "Goles en contra", "general", False),
    ("gd", None, "Diferencia de goles", "general", False),
    ("puntos_partido", None, "Puntos en el partido", "general", False),
    ("expg", "ExpG", "xG del equipo", "general", False),
    ("bgchnc", "BgChnc", "Ocasiones claras", "general", False),
    ("shtincbl", "ShtIncBl", "Tiros (incluidos bloqueados)", "general", False),

    # POSESIÓN Y ESTILO
    ("touchopbox", "TouchOpBox", "Toques en el área rival", "posesion", False),
    ("toques_tercio_rival_p90", "Toques Tercio Rival P90", "Toques en tercio rival (P90)", "posesion", False),
    ("poss_campo_rival", "Poss% Campo Rival", "% Posesión en campo rival", "posesion", True),
    ("poss_campo_defensivo", "Poss% Campo Defensivo", "% Posesión en campo defensivo", "posesion", True),
    ("poss_campo_def_equipo", "Poss% Campo Def (Equipo)", "% Posesión en campo defensivo (equipo)", "posesion", True),
    ("avgposswidth", "AvgPossWidth", "Anchura media de posesión (m)", "posesion", False),
    ("avgposstime", "AvgPossTime", "Duración media de posesión (s)", "posesion", False),
    ("avgwp", "AvgWP", "Índice medio de posesión/control (Avg WP)", "posesion", True),
    ("goalkick", "GoalKick", "Saques de puerta", "posesion", False),
    ("attack_left_pct", "% Attack through Left Flank", "% Ataques por banda izquierda", "posesion", True),
    ("attack_middle_pct", "% Attack through Middle", "% Ataques por el centro", "posesion", True),
    ("attack_right_pct", "% Attack through Right Flank", "% Ataques por banda derecha", "posesion", True),

    # OFENSIVAS (progresión, centros, ataque)
    ("progpass", "ProgPass", "Pases progresivos", "ofensivas", False),
    ("progcarry", "ProgCarry", "Conducciones progresivas", "ofensivas", False),
    ("conducc_prog", "ConduccProg", "Conducciones progresivas (alt)", "ofensivas", False),
    ("carrypass", "CarryPass", "Conducciones seguidas de pase", "ofensivas", False),
    ("lbp", "LBP", "Líneas rivales rotas por pase", "ofensivas", False),
    ("lbpownhalf", "LBPOwnHalf", "Líneas rotas en campo propio", "ofensivas", False),
    ("lbpintoa3", "LBPIntoA3", "Líneas rotas hacia el último tercio", "ofensivas", False),
    ("lbp_midline", "LBP Mid Line", "Líneas rotas: línea media rival", "ofensivas", False),
    ("lbp_defline", "LBP Def Line", "Líneas rotas: línea defensiva rival", "ofensivas", False),
    ("fwdpass", "FwdPass", "Pases hacia adelante", "ofensivas", False),
    ("fwdpass_pct", "FwdPass%", "% Pases hacia adelante", "ofensivas", True),
    ("pct_passfwd", "%PassFwd", "% Pases hacia adelante (alt)", "ofensivas", True),
    ("keypassp90", "KeyPassPer90", "Pases clave (P90)", "ofensivas", False),
    ("prlgcnescabza", "PrlgcnesCabza", "Prolongaciones de cabeza", "ofensivas", False),
    ("centros_3_4_izq", "centros 3_4 izq", "Centros desde tercio final (izq.)", "ofensivas", False),
    ("centros_3_4_der", "centros 3_4 der", "Centros desde tercio final (der.)", "ofensivas", False),
    ("crosses", "Crosses", "Centros totales", "ofensivas", False),
    ("goles_desde_area", "Goles desde el Area", "Goles desde dentro del área", "ofensivas", False),
    ("golcarrilcentral", "GolCarrilCentral", "Goles por el carril central", "ofensivas", False),
    ("golbanizq", "GolBanIZQ", "Goles por banda izquierda", "ofensivas", False),
    ("golbander", "GolBanDER", "Goles por banda derecha", "ofensivas", False),
    ("juego_interior", "juego interior", "Índice de juego interior", "ofensivas", False),
    ("v1v1_p90", "1v1/90", "1v1 (P90)", "ofensivas", False),

    # DEFENSIVAS (presión, recuperación, duelos)
    ("presiones_altas_p90", "Presiones AltasP90", "Presiones altas (P90)", "defensivas", False),
    ("highprsrapp", "HighPrsrApp", "Presiones altas (total)", "defensivas", False),
    ("highprsrappd3", "HighPrsrAppD3", "Presiones altas en tercio defensivo rival", "defensivas", False),
    ("highprsrappownhalf", "HighPrsrAppOwnHalf", "Presiones altas en campo propio", "defensivas", False),
    ("highprsrappopphalf", "HighPrsrAppOppHalf", "Presiones altas en campo rival", "defensivas", False),
    ("highprsrappm3", "HighPrsrAppM3", "Presiones altas en tercio medio", "defensivas", False),
    ("highprsrappa3", "HighPrsrAppA3", "Presiones altas en último tercio", "defensivas", False),
    ("highprsrperopptchd3", "HighPrsrPerOppTchD3", "Presión alta por toque rival en su tercio defensivo", "defensivas", False),
    ("highprsrbwopphflft", "HighPrsrBWOppHfLft", "Recuperaciones tras presión alta (campo rival, izq.)", "defensivas", False),
    ("highprsrbwopphfrght", "HighPrsrBWOppHfRght", "Recuperaciones tras presión alta (campo rival, der.)", "defensivas", False),
    ("highprsrbwtoshot10s", "HighPrsrBWToShot10s", "Recuperaciones que acaban en tiro en 10s", "defensivas", False),
    ("hightoendgoal", "HighTOEndGoal", "Recuperaciones altas que acaban en gol", "defensivas", False),
    ("recup_5s_pct", "Recuperaciones entre 5 segundos %", "% Recuperaciones en los primeros 5s", "defensivas", True),
    ("recup_10s_pct", "Recuperaciones entre 10 segundos %", "% Recuperaciones en los primeros 10s", "defensivas", True),
    ("rcvrym3", "RcvryM3", "Recuperaciones en tercio medio", "defensivas", False),
    ("rcvryd3", "RcvryD3", "Recuperaciones en tercio defensivo", "defensivas", False),
    ("rcvrya3", "RcvryA3", "Recuperaciones en tercio ofensivo", "defensivas", False),
    ("duelos_ganados_ctl", "Duelos ganados ctl", "% Duelos ganados (control)", "defensivas", True),
    ("duelos_def", "Duelos Def", "Duelos defensivos", "defensivas", False),
]
CAT_BY_KEY = {k: {"key": k, "col": c, "label": l, "cat": cat, "pct": p} for k, c, l, cat, p in METRICS}


def clean_num(v):
    if pd.isna(v):
        return None
    if isinstance(v, str):
        v = v.strip()
        if v in ("", "-", "nan"):
            return None
        v = v.replace(",", "")
        if v.endswith("%"):
            v = v[:-1]
        try:
            return float(v)
        except Exception:
            return None
    try:
        return float(v)
    except Exception:
        return None


def fmt_value(v, meta):
    if v is None or pd.isna(v):
        return "—"
    if meta["pct"]:
        return f"{v:.1f}%"
    if abs(v) < 10 and not float(v).is_integer():
        return f"{v:.2f}"
    if abs(v) < 100:
        return f"{v:.1f}"
    return f"{v:,.0f}"


def match_label(m):
    d = m["date"].split(" ")[0] if m["date"] else "?"
    venue = "vs" if m["home"] else "@"
    return f"{d} {venue} {m['opponent']} ({m['resultLabel']})"


def find_coach_column(df: pd.DataFrame):
    lower_map = {c.lower(): c for c in df.columns}
    for candidate in COACH_COLUMN_CANDIDATES:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]
    return None


@st.cache_data
def load_league_data():
    with open(LEAGUE_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_col(c: str) -> str:
    return c.lower().replace(" ", "").replace("_", "")


# Manual overrides for match-metrics whose column name doesn't match the team-season
# dataset exactly (or at all) but does have a genuine equivalent:
#   - str value  -> reuse another match-metric's benchmark (same underlying concept,
#                   alternate column name from the data source).
#   - list value -> sum these team-season columns per team before computing the benchmark
#                   (e.g. a total split across two zones in the team dataset).
MANUAL_LEAGUE_LINKS = {
    "fwdpass_pct": {"alias_of": "pct_passfwd"},
    "progcarry": {"sum_cols": ["ProgCarr mc", "ProgCarr mp"]},
}


@st.cache_data
def compute_league_benchmarks():
    """Mean/std/sorted values across the 20 LaLiga teams, computed directly from their own
    match-level CSVs in data/matches/ (each team's season average per metric). This gives
    genuine benchmarks for ALL match metrics, not just the ones that happen to share an
    exact column name with the separate team-season dataset."""
    team_files = list_team_files()
    per_team_averages = {key: [] for key, col, label, cat, is_pct in METRICS if col}

    for path_str in team_files.values():
        try:
            _, team_matches, _ = load_matches_from_path(path_str)
        except Exception:
            continue
        for key in per_team_averages:
            vals = [m["metrics"].get(key) for m in team_matches if m["metrics"].get(key) is not None]
            if vals:
                per_team_averages[key].append(statistics.mean(vals))

    benchmarks = {}
    for key, team_avgs in per_team_averages.items():
        if len(team_avgs) >= 2:
            benchmarks[key] = {
                "mean": statistics.mean(team_avgs),
                "std": statistics.pstdev(team_avgs) or 1.0,
                "values": sorted(team_avgs),
                "n_teams": len(team_avgs),
            }
    return benchmarks


@st.cache_data
def compute_league_benchmarks_legacy_crosswalk():
    """Old approach kept only as a fallback: derives benchmarks from the separate
    team-season dataset (data.json) by matching column names. Only used for metrics that
    compute_league_benchmarks() (real match data) couldn't cover, e.g. if the team library
    in data/matches/ doesn't yet have all 20 teams."""
    league_data = load_league_data()
    team_col_to_key = {m["col"]: m["key"] for m in league_data["catalog"]}
    team_col_normalized = {_normalize_col(m["col"]): m["key"] for m in league_data["catalog"]}
    team_cat_by_key = {m["key"]: m for m in league_data["catalog"]}

    def per_match_values(tkey, tmeta):
        vals = []
        for t in league_data["teams"]:
            v = t["metrics"].get(tkey)
            if v is None:
                continue
            if not tmeta["pct"] and not tmeta["p90"]:
                gm = t.get("gm") or 38
                v = v / gm
            vals.append(v)
        return vals

    benchmarks = {}
    for key, col, label, cat, is_pct in METRICS:
        if not col:
            continue
        tkey = team_col_to_key.get(col) or team_col_normalized.get(_normalize_col(col))
        if tkey:
            tmeta = team_cat_by_key[tkey]
            vals = per_match_values(tkey, tmeta)
            if len(vals) >= 2:
                benchmarks[key] = {"mean": statistics.mean(vals), "std": statistics.pstdev(vals) or 1.0,
                                    "values": sorted(vals)}

    for key, link in MANUAL_LEAGUE_LINKS.items():
        if key in benchmarks:
            continue
        if "alias_of" in link and link["alias_of"] in benchmarks:
            benchmarks[key] = benchmarks[link["alias_of"]]
        elif "sum_cols" in link:
            sum_keys = [team_col_to_key.get(c) for c in link["sum_cols"]]
            if all(sum_keys):
                vals = []
                for t in league_data["teams"]:
                    parts = [t["metrics"].get(k) for k in sum_keys]
                    if any(p is None for p in parts):
                        continue
                    total = sum(parts)
                    gm = t.get("gm") or 38
                    vals.append(total / gm)
                if len(vals) >= 2:
                    benchmarks[key] = {"mean": statistics.mean(vals), "std": statistics.pstdev(vals) or 1.0,
                                        "values": sorted(vals)}
    return benchmarks


def get_combined_league_benchmarks():
    """Real match-data benchmarks (preferred) merged with the legacy crosswalk as a
    fallback for any metric that couldn't be computed from the real files (e.g. a team
    file missing that particular column)."""
    real = compute_league_benchmarks()
    legacy = compute_league_benchmarks_legacy_crosswalk()
    combined = dict(legacy)
    combined.update(real)  # real data always wins when available
    return combined


def value_to_rank(value, sorted_league_values):
    n = len(sorted_league_values)
    rank = sum(1 for x in sorted_league_values if x >= value) + 1
    rank = min(rank, n)
    percentile = round(100 * (n - rank) / (n - 1)) if n > 1 else 100
    return rank, n, percentile


def list_team_files():
    """Only lists CSVs that actually have at least one row with a usable Date — an
    empty or corrupted file is skipped here instead of crashing the page later."""
    valid = {}
    for p in sorted(MATCHES_DIR.glob("*.csv")):
        try:
            df = pd.read_csv(p, nrows=5)
            if "Date" in df.columns and df["Date"].notna().any():
                valid[p.stem] = str(p)
            else:
                st.sidebar.caption(f"⚠️ `{p.name}` no tiene columna Date válida — se ha ignorado.")
        except Exception:
            st.sidebar.caption(f"⚠️ `{p.name}` no se pudo leer — se ha ignorado.")
    return valid


def build_matches_from_df(df: pd.DataFrame):
    coach_col = find_coach_column(df)
    matches = []
    for _, row in df.iterrows():
        result_str = row.get("Result", "")
        rm = re.match(r"([WLD])\s+(\d+)-(\d+)", str(result_str))
        outcome, gf, ga = (rm.group(1), int(rm.group(2)), int(rm.group(3))) if rm else (None, None, None)
        match = {
            "gameId": row.get("gameId"),
            "date": row.get("Date"),
            "opponent": row.get("opponent"),
            "home": bool(row.get("Home")),
            "outcome": outcome, "gf": gf, "ga": ga,
            "resultLabel": result_str,
            "coach": (row.get(coach_col) if coach_col and pd.notna(row.get(coach_col)) else None),
            "metrics": {},
        }
        for key, col, label, cat, is_pct in METRICS:
            if col is None:
                continue
            match["metrics"][key] = clean_num(row.get(col)) if col in df.columns else None
        # Inject the computed general/result metrics so they're filterable like any other.
        match["metrics"]["gf"] = float(gf) if gf is not None else None
        match["metrics"]["ga"] = float(ga) if ga is not None else None
        match["metrics"]["gd"] = float(gf - ga) if gf is not None and ga is not None else None
        match["metrics"]["puntos_partido"] = (3.0 if outcome == "W" else 1.0 if outcome == "D" else 0.0
                                               if outcome == "L" else None)
        matches.append(match)
    matches.sort(key=lambda m: m["date"] or "")
    team_name = df["Team"].iloc[0] if "Team" in df.columns and len(df) else "Equipo"
    for match in matches:
        match["_team_name"] = team_name
        match["_game_date"] = str(match["date"]).split(" ")[0] if match["date"] else None
    has_coach_column = coach_col is not None
    return team_name, matches, has_coach_column


@st.cache_data
def load_matches_from_path(path_str: str):
    df = pd.read_csv(path_str)
    return build_matches_from_df(df)


def merge_weekly_update(existing_path: Path, new_file_bytes: bytes):
    new_df = pd.read_csv(pd.io.common.BytesIO(new_file_bytes))
    if existing_path.exists():
        existing_df = pd.read_csv(existing_path)
    else:
        existing_df = pd.DataFrame(columns=new_df.columns)
    n_existing = len(existing_df)
    existing_ids = set(existing_df["gameId"]) if "gameId" in existing_df.columns else set()
    new_rows = new_df[~new_df["gameId"].isin(existing_ids)] if "gameId" in new_df.columns else new_df
    n_new_added = len(new_rows)
    n_duplicates_skipped = len(new_df) - n_new_added
    merged = pd.concat([existing_df, new_rows], ignore_index=True)
    if "Date" in merged.columns:
        merged = merged.sort_values("Date").reset_index(drop=True)
    return merged, n_existing, n_new_added, n_duplicates_skipped


# ---------------------------------------------------------------------------
# Reusable sidebar filter block: fecha, local/visit., resultado, entrenador, partidos
# ---------------------------------------------------------------------------
def render_match_selection_sidebar(team_name, matches, key_prefix):
    """Renders the shared sidebar controls and returns the list of selected match dicts."""
    st.sidebar.header(f"Filtros — {team_name}")

    dates = [m["date"] for m in matches if m["date"]]
    if not dates:
        st.error(
            f"El equipo **{team_name}** no tiene ningún partido con fecha válida en su CSV "
            f"(`data/matches/{team_name}.csv`). Revisa que el archivo no esté vacío o "
            f"corrupto y vuelve a subirlo."
        )
        st.stop()

    # Widget keys are scoped by team_name so that switching teams gives every widget a
    # fresh default instead of keeping a stale selection from the previous team (which
    # would otherwise intersect to zero matches and silently show "no hay partidos").
    tkey = f"{key_prefix}_{team_name}"

    min_date, max_date = min(dates), max(dates)
    date_range = st.sidebar.date_input(
        "Rango de fechas",
        value=(pd.to_datetime(min_date).date(), pd.to_datetime(max_date).date()),
        min_value=pd.to_datetime(min_date).date(), max_value=pd.to_datetime(max_date).date(),
        key=f"{tkey}_date_range",
    )
    venue_filter = st.sidebar.multiselect("Local / Visitante", ["Local", "Visitante"],
                                           default=["Local", "Visitante"], key=f"{tkey}_venue")
    result_filter = st.sidebar.multiselect(
        "Resultado", ["W", "D", "L"], default=["W", "D", "L"],
        format_func=lambda x: {"W": "Victoria", "D": "Empate", "L": "Derrota"}[x],
        key=f"{tkey}_result",
    )

    st.sidebar.divider()
    has_coach_column = any(m.get("coach") for m in matches)
    coach_filter = None
    if has_coach_column:
        coach_names = sorted({m["coach"] for m in matches if m.get("coach")})
        coach_filter = st.sidebar.multiselect("Filtrar por entrenador", coach_names, default=coach_names,
                                               key=f"{tkey}_coach_real")
    else:
        st.sidebar.caption("**Entrenador** — no viene una columna de entrenador en este CSV. "
                            "Puedes etiquetar tramos de fechas manualmente.")
        if "coach_ranges" not in st.session_state:
            st.session_state.coach_ranges = []
        with st.sidebar.expander("➕ Añadir tramo de entrenador"):
            c_name = st.text_input("Nombre del entrenador", key=f"{tkey}_coach_name_input")
            c_start = st.date_input("Desde", key=f"{tkey}_coach_start_input",
                                     value=pd.to_datetime(min_date).date())
            c_end = st.date_input("Hasta", key=f"{tkey}_coach_end_input",
                                   value=pd.to_datetime(max_date).date())
            if st.button("Añadir tramo", key=f"{tkey}_coach_add_btn"):
                if c_name:
                    st.session_state.coach_ranges.append({"name": c_name, "start": str(c_start), "end": str(c_end)})
                    st.rerun()
        if st.session_state.coach_ranges:
            for r in st.session_state.coach_ranges:
                st.sidebar.caption(f"• {r['name']}: {r['start']} → {r['end']}")
            coach_names = sorted({r["name"] for r in st.session_state.coach_ranges})
            coach_filter = st.sidebar.multiselect("Filtrar por entrenador", coach_names, default=coach_names,
                                                   key=f"{tkey}_coach_manual")
            if st.sidebar.button("Borrar tramos de entrenador", key=f"{tkey}_coach_clear_btn"):
                st.session_state.coach_ranges = []
                st.rerun()

    def match_coach_manual(m):
        if not m["date"] or "coach_ranges" not in st.session_state:
            return None
        d = pd.to_datetime(m["date"]).date()
        for r in st.session_state.coach_ranges:
            if pd.to_datetime(r["start"]).date() <= d <= pd.to_datetime(r["end"]).date():
                return r["name"]
        return None

    start_d, end_d = (date_range if isinstance(date_range, tuple) and len(date_range) == 2
                       else (pd.to_datetime(min_date).date(), pd.to_datetime(max_date).date()))
    candidates = []
    for m in matches:
        if not m["date"]:
            continue
        d = pd.to_datetime(m["date"]).date()
        if not (start_d <= d <= end_d):
            continue
        if m["home"] and "Local" not in venue_filter:
            continue
        if not m["home"] and "Visitante" not in venue_filter:
            continue
        if m["outcome"] and m["outcome"] not in result_filter:
            continue
        if coach_filter is not None:
            mc = m.get("coach") if has_coach_column else match_coach_manual(m)
            if mc is not None and mc not in coach_filter:
                continue
        candidates.append(m)

    st.sidebar.divider()
    match_labels = [match_label(m) for m in candidates]
    selected_labels = st.sidebar.multiselect("Selecciona los partidos a incluir", match_labels,
                                              default=match_labels, key=f"{tkey}_match_select")
    selected_matches = [m for m, lbl in zip(candidates, match_labels) if lbl in selected_labels]
    return selected_matches, len(matches)


# ---------------------------------------------------------------------------
# Selector de equipo + panel de actualización semanal (compartido por Rival/Propio)
# ---------------------------------------------------------------------------
def render_mode_toggle(key_prefix):
    """Total / Por 90' toggle. Returns 'p90' or 'total'."""
    choice = st.radio(
        "Modo de visualización", ["Por partido (P90)", "Total del periodo"],
        horizontal=True, key=f"{key_prefix}_mode_toggle",
        help="'Por partido' promedia cada métrica entre los partidos seleccionados "
             "(cada partido ya son ~90 minutos). 'Total' suma el valor bruto de todos "
             "los partidos seleccionados. Los porcentajes siempre se muestran como media.",
    )
    return "p90" if choice == "Por partido (P90)" else "total"


def render_team_picker_and_updater(key_prefix):
    team_files = list_team_files()
    if not team_files:
        st.error("No hay ningún CSV en `data/matches/`. Añade al menos uno (ver README).")
        st.stop()
    selected_team_file = st.selectbox("Equipo a analizar", list(team_files.keys()), key=f"{key_prefix}_team_selector")
    team_name, matches, has_coach_column = load_matches_from_path(team_files[selected_team_file])

    with st.expander("🔄 Actualizar datos de un equipo (export semanal)"):
        st.caption("Sube el export más reciente de TruMedia/Opta para un equipo. Se fusiona con "
                   "el histórico ya guardado sin duplicar partidos (se comparan por gameId) — "
                   "puedes subir tanto la temporada completa como solo los últimos partidos.")
        upd_col1, upd_col2 = st.columns([1, 2])
        with upd_col1:
            update_target = st.selectbox("Equipo a actualizar", ["(nuevo equipo)"] + list(team_files.keys()),
                                          key=f"{key_prefix}_update_target")
            new_team_name_input = ""
            if update_target == "(nuevo equipo)":
                new_team_name_input = st.text_input("Nombre del nuevo equipo (para el archivo)",
                                                      key=f"{key_prefix}_new_team_name")
        with upd_col2:
            weekly_file = st.file_uploader("Export de esta semana (CSV)", type=["csv"],
                                            key=f"{key_prefix}_weekly_upload")

        if weekly_file is not None:
            target_name = new_team_name_input.strip() if update_target == "(nuevo equipo)" else update_target
            if not target_name:
                st.warning("Escribe un nombre para el nuevo equipo antes de continuar.")
            else:
                target_path = MATCHES_DIR / f"{target_name}.csv"
                merged_df, n_existing, n_added, n_dupe = merge_weekly_update(target_path, weekly_file.getvalue())
                st.success(f"Fusión lista: {n_existing} partidos ya guardados + {n_added} partidos nuevos "
                           f"añadidos ({n_dupe} ya existían y se han ignorado).")
                csv_bytes = merged_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    f"⬇️ Descargar {target_name}.csv actualizado ({len(merged_df)} partidos en total)",
                    data=csv_bytes, file_name=f"{target_name}.csv", mime="text/csv",
                    key=f"{key_prefix}_download_btn",
                )
                st.info(
                    "**Para que el cambio se quede guardado para la próxima vez:** si usas la app en "
                    "local, guarda este archivo descargado directamente en `data/matches/` (sobrescribiendo "
                    "el anterior si existe) y recarga la página. Si la tienes desplegada en Streamlit "
                    "Community Cloud, sube este mismo archivo a la carpeta `data/matches/` de tu repositorio "
                    "de GitHub — Streamlit Cloud redesplegará solo en 1-2 minutos."
                )

    return team_name, matches, has_coach_column
# ---------------------------------------------------------------------------
# Panel de métricas por categoría: NO filtra partidos, solo muestra el valor medio
# de cada métrica de la categoría junto a su ranking real en LaLiga (cuando existe
# comparativa de liga para esa métrica).
# ---------------------------------------------------------------------------
def render_metric_category_report(matches, league_benchmarks, key_prefix, mode="p90"):
    """Shows every metric in the chosen category as (valor, percentil, ranking en LaLiga)
    for the currently selected matches. Purely informative — does not filter anything.

    mode='p90'   -> average per match (each row is already ~90 minutes).
    mode='total' -> sum across all selected matches (percentages are still averaged,
                    since summing a percentage doesn't mean anything).
    """
    import statistics as _stats

    cat = st.selectbox("Categoría de métricas", CAT_ORDER,
                        format_func=lambda c: CAT_LABELS[c], key=f"{key_prefix}_filtercat")
    metrics_in_cat = [m for m in METRICS if m[3] == cat]
    n_benchmarked_in_cat = sum(1 for m in metrics_in_cat if m[0] in league_benchmarks)
    mode_label = "por partido (P90)" if mode == "p90" else "total del periodo seleccionado"
    st.caption(f"{len(metrics_in_cat)} métricas en esta categoría ({n_benchmarked_in_cat} con "
               f"comparativa de liga) · valores {mode_label} sobre {len(matches)} partidos "
               f"seleccionados. La comparativa de liga sale de los partidos reales de los 20 "
               f"equipos de LaLiga y siempre se calcula sobre el promedio por partido.")

    rows = []
    for key, col, label, c, is_pct in metrics_in_cat:
        vals = [m["metrics"].get(key) for m in matches if m["metrics"].get(key) is not None]
        if not vals:
            continue
        agg_val = _stats.mean(vals) if (mode == "p90" or is_pct) else sum(vals)
        meta = CAT_BY_KEY[key]
        row = {"Métrica": label, "Valor": fmt_value(agg_val, meta)}
        bench = league_benchmarks.get(key)
        if bench and (mode == "p90" or is_pct):
            avg_val = _stats.mean(vals)
            rank, n, percentile = value_to_rank(avg_val, bench["values"])
            row["Percentil"] = percentile
            row["Ranking en LaLiga"] = f"{rank}º de {n}"
        elif bench:
            row["Percentil"] = None
            row["Ranking en LaLiga"] = "ranking disponible en modo 'Por partido (P90)'"
        else:
            row["Percentil"] = None
            row["Ranking en LaLiga"] = "sin comparativa de liga"
        rows.append(row)

    if not rows:
        st.info("No hay datos suficientes en esta categoría para los partidos seleccionados.")
        return

    df_report = pd.DataFrame(rows).sort_values(
        "Percentil", ascending=False, na_position="last"
    ).drop(columns="Percentil")
    st.dataframe(df_report, use_container_width=True, hide_index=True)

    # ---- Top 3 jugadores por métrica (cuando hay datos individuales de esos partidos) ----
    render_top_players_for_category(matches, metrics_in_cat, key_prefix)


def render_top_players_for_category(matches, metrics_in_cat, key_prefix):
    """For metrics in this category that also exist in the individual player-match
    catalog, shows the top 3 players (within the SAME team and selected matches)."""
    try:
        from player_common import PLAYER_METRICS, load_player_matches, TEAM_CODE_TO_NAME
    except ImportError:
        return

    player_col_to_key = {c: k for k, c, l, cat, p in PLAYER_METRICS if c}
    linked = [(key, col, label) for key, col, label, cat, is_pct in metrics_in_cat if col in player_col_to_key]
    if not linked:
        return

    team_codes_in_scope = {m.get("_team_name") for m in matches if m.get("_team_name")}
    dates_in_scope = {m.get("_game_date") for m in matches if m.get("_game_date")}
    if not team_codes_in_scope:
        return

    team_display_names = {TEAM_CODE_TO_NAME.get(c, c) for c in team_codes_in_scope}
    any_data = any(not load_player_matches(t).empty for t in team_display_names)
    if not any_data:
        return  # no individual data ingested yet for this team — stay silent

    st.markdown("**🏅 Top 3 jugadores en estas métricas** (mismo equipo y partidos seleccionados)")
    cols_ui = st.columns(min(3, len(linked)))
    for i, (key, col, label) in enumerate(linked[:6]):
        with cols_ui[i % len(cols_ui)]:
            st.caption(label)
            frames = []
            for team_display in team_display_names:
                pdf = load_player_matches(team_display)
                if pdf.empty or col not in pdf.columns:
                    continue
                if dates_in_scope:
                    pdf = pdf[pdf["Date"].isin(dates_in_scope)]
                if pdf.empty:
                    continue
                agg = pdf.groupby("PlayerClean")[col].sum(min_count=1).reset_index()
                frames.append(agg)
            if not frames:
                st.write("Sin datos individuales para estos partidos.")
                continue
            all_players = pd.concat(frames, ignore_index=True)
            all_players = all_players.dropna(subset=[col])
            if all_players.empty:
                st.write("Sin datos.")
                continue
            top3 = all_players.sort_values(col, ascending=False).head(3)
            for _, r in top3.iterrows():
                val = r[col]
                val_str = f"{val:.0f}" if float(val).is_integer() else f"{val:.2f}"
                st.write(f"• **{r['PlayerClean']}** — {val_str}")

