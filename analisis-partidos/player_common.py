"""
Datos individuales de jugador por partido (Opta) para Análisis de Partidos.
Un CSV por partido (todos los jugadores de ambos equipos); este módulo los separa por
equipo, los acumula en data/player_matches/{Equipo}.csv, y expone un catálogo de
métricas categorizado (General, Ofensivas, Defensivas, Posesión y Estilo).
"""
import re
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).parent
PLAYER_MATCHES_DIR = APP_DIR / "data" / "player_matches"
PLAYER_MATCHES_DIR.mkdir(parents=True, exist_ok=True)

# key, col, label, cat, pct
PLAYER_METRICS = [
    # GENERAL
    ("min", "Min", "Minutos jugados", "general", False),
    ("touches", "Touches", "Toques", "general", False),
    ("goal", "Goal", "Goles", "general", False),
    ("ast", "Ast", "Asistencias", "general", False),

    # OFENSIVAS
    ("psatt", "PsAtt", "Pases intentados", "ofensivas", False),
    ("pass_pct", "Pass%", "% Acierto de pase", "ofensivas", True),
    ("ps_a3_pct", "Ps%InA3rd", "% Pases en último tercio", "ofensivas", True),
    ("pases_ultimo_tercio", "Pases en Ultimo Tercio", "Pases al último tercio", "ofensivas", False),
    ("pasescmpcamporival", "PasesCmpCampoRival", "Pases completados en campo rival", "ofensivas", False),
    ("fwdpass", "FwdPass", "Pases hacia adelante", "ofensivas", False),
    ("fwdpass_pct", "FwdPass%", "% Pases hacia adelante", "ofensivas", True),
    ("pct_passfwd", "%PassFwd", "% Pases hacia adelante (alt)", "ofensivas", True),
    ("pct_passright", "%PassRight", "% Pases hacia la derecha", "ofensivas", True),
    ("pct_passleft", "%PassLeft", "% Pases hacia la izquierda", "ofensivas", True),
    ("cambios_orientacion", "CambiosOrientación", "Cambios de orientación", "ofensivas", False),
    ("progcarry", "ProgCarry", "Conducciones progresivas", "ofensivas", False),
    ("lbp", "LBP", "Líneas rivales rotas por pase", "ofensivas", False),
    ("lbpownhalf", "LBPOwnHalf", "Líneas rotas en campo propio", "ofensivas", False),
    ("lbpopphalf", "LBPOppHalf", "Líneas rotas en campo rival", "ofensivas", False),
    ("chance", "Chance", "Ocasiones creadas", "ofensivas", False),
    ("xa", "xA", "xA (asistencia esperada)", "ofensivas", False),
    ("keypass", "KeyPass", "Pases clave", "ofensivas", False),
    ("bgchnc", "BgChnc", "Ocasiones claras", "ofensivas", False),
    ("bgchnccrtd", "BgChncCrtd", "Ocasiones claras creadas", "ofensivas", False),
    ("crosses", "Crosses", "Centros", "ofensivas", False),
    ("juego_interior", "juego interior", "Índice de juego interior", "ofensivas", False),
    ("juego_area", "Juego dentro del área", "Juego dentro del área", "ofensivas", False),
    ("toquescentroarea", "ToquesCentroÁrea", "Toques en el centro del área", "ofensivas", False),
    ("intooutruns", "IntoOutRuns", "Desmarques de dentro a fuera", "ofensivas", False),
    ("inbehindruns", "InBehindRuns", "Desmarques a la espalda", "ofensivas", False),
    ("takeon", "TakeOn", "Regates intentados", "ofensivas", False),
    ("psrec", "PsRec", "Pases recibidos", "ofensivas", False),
    ("psfwdhighprsrcmp_pct", "PsFwdHighPrsrCmp%", "% Acierto pase adelante bajo presión", "ofensivas", True),
    ("pscmpsop", "PsCmpSoP", "Pases completados inicio de posesión", "ofensivas", False),

    # REMATE (dentro de ofensivas)
    ("shot", "Shot", "Tiros", "ofensivas", False),
    ("shotexcblk", "ShotExcBlk", "Tiros no bloqueados", "ofensivas", False),
    ("sog", "SOG", "Tiros a puerta", "ofensivas", False),
    ("ontarget_pct", "OnTarget%", "% Tiros a puerta", "ofensivas", True),
    ("expg", "ExpG", "xG", "ofensivas", False),
    ("expg_shot", "ExpG/Shot", "xG por tiro", "ofensivas", False),

    # DEFENSIVAS
    ("int_", "Int", "Intercepciones", "defensivas", False),
    ("duels", "Duels", "Duelos totales", "defensivas", False),
    ("duel_pct", "Duel%", "% Duelos ganados", "defensivas", True),
    ("aerials", "Aerials", "Duelos aéreos", "defensivas", False),
    ("aerial_pct", "Aerial%", "% Duelos aéreos ganados", "defensivas", True),
    ("tackle_pct", "Tackle%", "% Entradas ganadas", "defensivas", True),
    ("recovery", "Recovery", "Recuperaciones", "defensivas", False),
    ("recup_5s_pct", "Recuperaciones entre 5 segundos %", "% Recuperaciones en 5s", "defensivas", True),
    ("recup_10s_pct", "Recuperaciones entre 10 segundos %", "% Recuperaciones en 10s", "defensivas", True),
    ("recup_campo_rival_p90", "Recuperaciones Campo Rival/90", "Recuperaciones en campo rival (P90)", "defensivas", False),
    ("highprsrapp", "HighPrsrApp", "Presiones altas", "defensivas", False),
    ("highprsrballwon", "HighPrsrBallWon", "Balones ganados en presión alta", "defensivas", False),
    ("highturnovers", "HighTurnovers", "Pérdidas rivales forzadas altas", "defensivas", False),
    ("grnddlwn", "GrndDlWn", "Duelos al suelo ganados", "defensivas", False),
    ("clrncd3", "ClrncD3", "Despejes en tercio defensivo", "defensivas", False),
    ("disposs", "Disposs", "Balones perdidos por presión rival", "defensivas", False),
    ("perdidascampopropio", "PerdidasCampoPropio", "Pérdidas en campo propio", "defensivas", False),
    ("perdidascamporival", "PérdidasCampoRival", "Pérdidas en campo rival", "defensivas", False),
    ("v1v1", "1v1", "1v1 defensivos", "defensivas", False),
]

PLAYER_CAT_LABELS = {"general": "General", "ofensivas": "Ofensivas", "defensivas": "Defensivas"}
PLAYER_CAT_ORDER = ["general", "ofensivas", "defensivas"]
PLAYER_CAT_BY_KEY = {k: {"key": k, "col": c, "label": l, "cat": cat, "pct": p} for k, c, l, cat, p in PLAYER_METRICS}

FILENAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_([A-Z]{3})-([A-Z]{3})")

# Bridges the 3-letter team code (used inside the team-level match CSVs / page headers)
# to the display name used for the data/matches/ and data/player_matches/ filenames.
TEAM_CODE_TO_NAME = {
    "ALA": "Alavés", "ATH": "Athletic Club", "ATM": "Atlético de Madrid", "BAR": "Barcelona",
    "BET": "Real Betis", "CEL": "Celta de Vigo", "ELC": "Elche", "ESP": "Espanyol",
    "GET": "Getafe", "GIR": "Girona", "LEV": "Levante", "MAL": "Málaga", "MGA": "Málaga",
    "OSA": "Osasuna", "RAC": "Racing", "RAY": "Rayo Vallecano", "RCD": "Espanyol",
    "RMA": "Real Madrid", "RSO": "Real Sociedad", "SEV": "Sevilla", "VAL": "Valencia",
    "VIL": "Villarreal", "DEP": "Deportivo", "OVI": "Real Oviedo",
}


def clean_num(v):
    if pd.isna(v):
        return None
    if isinstance(v, str):
        v = v.strip()
        if v in ("", "-", "n/a", "nan"):
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


def parse_player_match_csv(file_bytes_or_path, filename: str) -> pd.DataFrame:
    """Parses one Opta per-match player CSV. Returns a tidy dataframe: one row per
    player, with Date/Opponent/GameKey columns added from the filename."""
    m = FILENAME_RE.search(filename)
    date, team1, team2 = (m.group(1), m.group(2), m.group(3)) if m else (None, None, None)
    game_key = f"{date}_{team1}-{team2}" if m else filename

    df = pd.read_csv(file_bytes_or_path)
    df = df[df["Player"].notna()].copy()

    # Drop the unreliable team-context columns accidentally duplicated per player row
    # (they come back as constant/blank per match and aren't genuine individual stats).
    for junk_col in ["W", "D", "L", "P", "GF", "GA", "GD", "Poss%", "Section"]:
        if junk_col in df.columns:
            df = df.drop(columns=[junk_col])

    df["Date"] = date
    df["GameKey"] = game_key
    df["Opponent"] = df["Team"].apply(lambda t: team2 if t == team1 else team1)

    for key, col, label, cat, is_pct in PLAYER_METRICS:
        if col in df.columns:
            df[col] = df[col].apply(clean_num)

    # Clean player name (strip trailing "(Position)")
    df["PlayerClean"] = df["Player"].str.replace(r"\s*\([^)]*\)\s*$", "", regex=True).str.strip()
    df["Position"] = df["Player"].str.extract(r"\(([^)]*)\)\s*$")

    return df


@st.cache_data
def list_player_match_files():
    return {p.stem: str(p) for p in sorted(PLAYER_MATCHES_DIR.glob("*.csv"))}


@st.cache_data
def load_player_matches(team_name: str) -> pd.DataFrame:
    path = PLAYER_MATCHES_DIR / f"{team_name}.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def ingest_match_file(file_bytes, filename: str):
    """Parses one match file and appends/merges each team's players into their
    running data/player_matches/{Team}.csv (de-duplicated by PlayerClean + GameKey)."""
    import io
    df = parse_player_match_csv(io.BytesIO(file_bytes), filename)
    summary = []
    for team_code, group in df.groupby("Team"):
        team_display = TEAM_CODE_TO_NAME.get(team_code, team_code)
        path = PLAYER_MATCHES_DIR / f"{team_display}.csv"
        if path.exists():
            existing = pd.read_csv(path)
            existing = existing[existing["GameKey"] != group["GameKey"].iloc[0]]
            combined = pd.concat([existing, group], ignore_index=True)
        else:
            combined = group
        combined.to_csv(path, index=False)
        summary.append({"team": team_display, "n_players": len(group)})
    return summary, df


def build_team_level_row(team_total_row: pd.Series, opponent_code: str, date: str, other_goals: float, home: bool):
    """Builds a minimal team-level match row (compatible with data/matches/*.csv) from
    the 'team total' row present in an individual-player match file (Player is NaN)."""
    my_goals = team_total_row.get("Goal")
    outcome = "W" if my_goals > other_goals else ("L" if my_goals < other_goals else "D")
    result_str = f"{outcome} {int(my_goals)}-{int(other_goals)}"
    row = {
        "gameId": f"{date}_{team_total_row['Team']}-{opponent_code}" if home
                  else f"{date}_{opponent_code}-{team_total_row['Team']}",
        "Date": f"{date} 00:00:00",
        "Team": team_total_row["Team"],
        "opponent": opponent_code,
        "Home": home,
        "Away": not home,
        "Result": result_str,
    }
    for k, v in team_total_row.items():
        if k in ("Team", "Player", "Min", "Goal") or pd.isna(v) and k not in row:
            continue
        if k not in row:
            row[k] = v
    row["Goal"] = my_goals
    return row


def ingest_match_file_full(file_bytes, filename: str):
    """Full ingestion: splits the match file by team into data/player_matches/, AND
    extracts the two 'team total' rows to also append a new match into
    data/matches/{Team}.csv (so the team-level pages and the top-3-players cross-link
    pick it up immediately). Returns a summary list of what was written."""
    import io
    from common import MATCHES_DIR  # local import to avoid a circular import at module load

    raw_df = pd.read_csv(io.BytesIO(file_bytes))
    m = FILENAME_RE.search(filename)
    if not m:
        return [{"error": f"No se pudo leer la fecha/equipos del nombre de archivo: {filename}"}], []
    date, code_a, code_b = m.group(1), m.group(2), m.group(3)

    player_summary, player_df = ingest_match_file(file_bytes, filename)

    team_rows = raw_df[raw_df["Player"].isna()].copy()
    written_files = [f"data/player_matches/{s['team']}.csv" for s in player_summary]
    if len(team_rows) == 2:
        goals = dict(zip(team_rows["Team"], team_rows["Goal"]))
        for _, row in team_rows.iterrows():
            code = row["Team"]
            opp = code_b if code == code_a else code_a
            home = (code == code_a)
            new_row = build_team_level_row(row, opp, date, goals[opp], home)
            team_display = TEAM_CODE_TO_NAME.get(code, code)
            path = MATCHES_DIR / f"{team_display}.csv"
            if path.exists():
                existing = pd.read_csv(path)
                existing = existing[existing["gameId"] != new_row["gameId"]]
                combined = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
            else:
                combined = pd.DataFrame([new_row])
            combined.to_csv(path, index=False)
            written_files.append(f"data/matches/{team_display}.csv")

    return player_summary, written_files


def render_player_data_updater(key_prefix: str):
    """Multi-file uploader: drop one or several per-match Opta player CSVs and this
    ingests all of them at once (split by team, de-duplicated, and cross-appended into
    the team-level match library too). Offers a single zip download with every file
    that changed, ready to re-upload to data/player_matches/ and data/matches/ on GitHub."""
    with st.expander("🔄 Actualizar datos individuales (uno o varios partidos a la vez)"):
        st.caption(
            "Sube los CSV de partido individual (formato Opta: una fila por jugador, "
            "nombre de archivo tipo `YYYY-MM-DD_XXX-YYY.csv`). Puedes soltar varios de "
            "golpe. Se separan por equipo, se fusionan sin duplicar partidos, y también "
            "se añade una entrada a nivel de equipo para que el cruce con las tablas de "
            "Rival/Propio funcione automáticamente."
        )
        uploaded_files = st.file_uploader(
            "Uno o varios CSV de partido", type=["csv"], accept_multiple_files=True,
            key=f"{key_prefix}_player_multi_upload",
        )
        if uploaded_files:
            all_written = set()
            results = []
            for f in uploaded_files:
                summary, written = ingest_match_file_full(f.getvalue(), f.name)
                results.append((f.name, summary))
                all_written.update(written)

            for fname, summary in results:
                if summary and "error" in summary[0]:
                    st.error(f"{fname}: {summary[0]['error']}")
                else:
                    teams_txt = ", ".join(f"{s['team']} ({s['n_players']} jugadores)" for s in summary)
                    st.success(f"✅ {fname} → {teams_txt}")

            if all_written:
                st.cache_data.clear()  # avoid showing stale cached data after this update
                import zipfile
                import io as _io
                buf = _io.BytesIO()
                with zipfile.ZipFile(buf, "w") as zf:
                    for rel_path in sorted(all_written):
                        full_path = APP_DIR / rel_path
                        if full_path.exists():
                            zf.write(full_path, rel_path)
                st.download_button(
                    f"⬇️ Descargar los {len(all_written)} archivos actualizados (.zip)",
                    data=buf.getvalue(), file_name="datos_actualizados.zip", mime="application/zip",
                )
                st.info(
                    "**Para que quede guardado**: descomprime el zip y sube esos mismos "
                    "archivos (respetando las carpetas `data/matches/` y "
                    "`data/player_matches/`) a tu repositorio de GitHub — Streamlit Cloud "
                    "redesplegará solo en 1-2 minutos. En local, basta con guardarlos en "
                    "su sitio y recargar la página."
                )
