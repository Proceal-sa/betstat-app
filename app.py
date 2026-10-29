import os
import json
import math
import time
import datetime
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

ODDS_API_KEY = "93fcf8558b6517575a6f6be7a2afcc81"
CACHE_FILE = "stats_cache.json"

# Competiciones de América y Europa soportadas
LEAGUES_CONFIG = {
    # --- AMÉRICA ---
    "soccer_colombia_primera_a": {
        "name": "Liga BetPlay (Colombia)",
        "avg_home_goals": 1.32,
        "avg_away_goals": 0.88,
        "avg_xg": 1.10
    },
    "soccer_conmebol_copa_libertadores": {
        "name": "Copa CONMEBOL Libertadores",
        "avg_home_goals": 1.55,
        "avg_away_goals": 0.95,
        "avg_xg": 1.25
    },
    "soccer_conmebol_copa_sudamericana": {
        "name": "Copa CONMEBOL Sudamericana",
        "avg_home_goals": 1.48,
        "avg_away_goals": 0.92,
        "avg_xg": 1.20
    },
    "soccer_brazil_campeonato": {
        "name": "Brasileirão Série A (Brasil)",
        "avg_home_goals": 1.45,
        "avg_away_goals": 1.05,
        "avg_xg": 1.25
    },
    "soccer_brazil_copa_do_brasil": {
        "name": "Copa de Brasil",
        "avg_home_goals": 1.40,
        "avg_away_goals": 0.95,
        "avg_xg": 1.18
    },
    "soccer_usa_mls": {
        "name": "MLS (Estados Unidos)",
        "avg_home_goals": 1.68,
        "avg_away_goals": 1.28,
        "avg_xg": 1.50
    },
    "soccer_mexico_ligamx": {
        "name": "Liga MX (México)",
        "avg_home_goals": 1.52,
        "avg_away_goals": 1.15,
        "avg_xg": 1.35
    },
    "soccer_argentina_primera_division": {
        "name": "Primera División (Argentina)",
        "avg_home_goals": 1.28,
        "avg_away_goals": 0.88,
        "avg_xg": 1.08
    },

    # --- EUROPA ---
    "soccer_epl": {
        "name": "Premier League (Inglaterra)",
        "avg_home_goals": 1.55,
        "avg_away_goals": 1.25,
        "avg_xg": 1.40
    },
    "soccer_spain_la_liga": {
        "name": "LaLiga (España)",
        "avg_home_goals": 1.42,
        "avg_away_goals": 1.12,
        "avg_xg": 1.28
    },
    "soccer_uefa_champs_league": {
        "name": "UEFA Champions League",
        "avg_home_goals": 1.65,
        "avg_away_goals": 1.35,
        "avg_xg": 1.45
    }
}

# Base de datos de métricas históricas y recientes por club
def load_or_update_stats():
    now = time.time()
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if now - data.get("timestamp", 0) < 86400:
                    return data.get("stats", {})
        except Exception:
            pass

    base_stats = {
        # --- COLOMBIA ---
        "Millonarios": {"gf_h": 1.70, "ga_h": 0.65, "gf_a": 1.15, "ga_a": 0.90, "xg_f": 1.45, "xg_a": 0.85, "rec_gf": 1.80, "rec_ga": 0.60},
        "Santa Fe": {"gf_h": 1.55, "ga_h": 0.60, "gf_a": 1.05, "ga_a": 0.80, "xg_f": 1.30, "xg_a": 0.80, "rec_gf": 1.40, "rec_ga": 0.40},
        "Atlético Nacional": {"gf_h": 1.75, "ga_h": 0.80, "gf_a": 1.20, "ga_a": 1.00, "xg_f": 1.50, "xg_a": 0.95, "rec_gf": 1.60, "rec_ga": 1.00},
        "América de Cali": {"gf_h": 1.65, "ga_h": 0.70, "gf_a": 1.10, "ga_a": 0.95, "xg_f": 1.40, "xg_a": 0.90, "rec_gf": 1.80, "rec_ga": 0.80},
        "Junior": {"gf_h": 1.80, "ga_h": 0.65, "gf_a": 0.95, "ga_a": 1.15, "xg_f": 1.55, "xg_a": 1.05, "rec_gf": 1.40, "rec_ga": 1.20},
        "Deportes Tolima": {"gf_h": 1.60, "ga_h": 0.70, "gf_a": 1.15, "ga_a": 0.85, "xg_f": 1.38, "xg_a": 0.88, "rec_gf": 1.60, "rec_ga": 0.60},
        "Independiente Medellín": {"gf_h": 1.50, "ga_h": 0.75, "gf_a": 0.95, "ga_a": 1.05, "xg_f": 1.25, "xg_a": 0.95, "rec_gf": 1.20, "rec_ga": 1.00},
        "Once Caldas": {"gf_h": 1.45, "ga_h": 0.75, "gf_a": 0.90, "ga_a": 1.00, "xg_f": 1.20, "xg_a": 0.95, "rec_gf": 1.40, "rec_ga": 0.80},
        "Bucaramanga": {"gf_h": 1.40, "ga_h": 0.65, "gf_a": 0.90, "ga_a": 0.85, "xg_f": 1.15, "xg_a": 0.85, "rec_gf": 1.00, "rec_ga": 0.60},
        "Deportivo Cali": {"gf_h": 1.35, "ga_h": 1.10, "gf_a": 0.85, "ga_a": 1.30, "xg_f": 1.10, "xg_a": 1.25, "rec_gf": 1.00, "rec_ga": 1.60},
        "Deportivo Pereira": {"gf_h": 1.35, "ga_h": 0.85, "gf_a": 0.85, "ga_a": 1.10, "xg_f": 1.15, "xg_a": 1.05, "rec_gf": 1.20, "rec_ga": 1.00},
        "Deportivo Pasto": {"gf_h": 1.40, "ga_h": 0.80, "gf_a": 0.75, "ga_a": 1.20, "xg_f": 1.15, "xg_a": 1.10, "rec_gf": 1.20, "rec_ga": 1.00},
        "La Equidad": {"gf_h": 1.25, "ga_h": 0.80, "gf_a": 0.85, "ga_a": 1.00, "xg_f": 1.10, "xg_a": 0.90, "rec_gf": 1.00, "rec_ga": 1.00},

        # --- BRASIL (BRASILEIRÃO & COPA DO BRASIL) ---
        "Flamengo": {"gf_h": 2.15, "ga_h": 0.85, "gf_a": 1.65, "ga_a": 1.10, "xg_f": 1.95, "xg_a": 0.90, "rec_gf": 2.00, "rec_ga": 0.80},
        "Palmeiras": {"gf_h": 2.05, "ga_h": 0.75, "gf_a": 1.60, "ga_a": 0.95, "xg_f": 1.90, "xg_a": 0.85, "rec_gf": 1.80, "rec_ga": 0.80},
        "Botafogo": {"gf_h": 2.10, "ga_h": 0.80, "gf_a": 1.55, "ga_a": 1.05, "xg_f": 1.85, "xg_a": 0.90, "rec_gf": 2.20, "rec_ga": 1.00},
        "Atlético Mineiro": {"gf_h": 1.80, "ga_h": 0.90, "gf_a": 1.30, "ga_a": 1.15, "xg_f": 1.60, "xg_a": 1.05, "rec_gf": 1.60, "rec_ga": 1.20},
        "São Paulo": {"gf_h": 1.70, "ga_h": 0.85, "gf_a": 1.15, "ga_a": 1.20, "xg_f": 1.45, "xg_a": 1.00, "rec_gf": 1.40, "rec_ga": 1.00},
        "Internacional": {"gf_h": 1.65, "ga_h": 0.80, "gf_a": 1.25, "ga_a": 1.10, "xg_f": 1.40, "xg_a": 0.95, "rec_gf": 1.60, "rec_ga": 0.80},
        "Cruzeiro": {"gf_h": 1.60, "ga_h": 0.85, "gf_a": 1.10, "ga_a": 1.25, "xg_f": 1.35, "xg_a": 1.10, "rec_gf": 1.20, "rec_ga": 1.00},
        "Fluminense": {"gf_h": 1.50, "ga_h": 0.95, "gf_a": 1.05, "ga_a": 1.35, "xg_f": 1.30, "xg_a": 1.20, "rec_gf": 1.20, "rec_ga": 1.20},
        "Corinthians": {"gf_h": 1.60, "ga_h": 1.00, "gf_a": 1.00, "ga_a": 1.40, "xg_f": 1.35, "xg_a": 1.25, "rec_gf": 1.40, "rec_ga": 1.40},
        "Grêmio": {"gf_h": 1.55, "ga_h": 1.10, "gf_a": 1.05, "ga_a": 1.45, "xg_f": 1.30, "xg_a": 1.30, "rec_gf": 1.20, "rec_ga": 1.40},

        # --- ARGENTINA & LIBERTADORES ---
        "River Plate": {"gf_h": 2.10, "ga_h": 0.65, "gf_a": 1.40, "ga_a": 0.90, "xg_f": 1.85, "xg_a": 0.80, "rec_gf": 1.80, "rec_ga": 0.60},
        "Boca Juniors": {"gf_h": 1.65, "ga_h": 0.70, "gf_a": 1.10, "ga_a": 1.00, "xg_f": 1.45, "xg_a": 0.85, "rec_gf": 1.40, "rec_ga": 0.80},
        "Racing Club": {"gf_h": 1.75, "ga_h": 0.80, "gf_a": 1.25, "ga_a": 1.10, "xg_f": 1.55, "xg_a": 0.95, "rec_gf": 1.60, "rec_ga": 1.00},
        "Independiente": {"gf_h": 1.35, "ga_h": 0.70, "gf_a": 0.95, "ga_a": 0.95, "xg_f": 1.20, "xg_a": 0.85, "rec_gf": 1.00, "rec_ga": 0.60},
        "San Lorenzo": {"gf_h": 1.25, "ga_h": 0.75, "gf_a": 0.85, "ga_a": 1.05, "xg_f": 1.10, "xg_a": 0.90, "rec_gf": 1.00, "rec_ga": 1.00},
        "Vélez Sarsfield": {"gf_h": 1.60, "ga_h": 0.60, "gf_a": 1.20, "ga_a": 0.85, "xg_f": 1.45, "xg_a": 0.75, "rec_gf": 1.40, "rec_ga": 0.60},
        "Talleres": {"gf_h": 1.55, "ga_h": 0.75, "gf_a": 1.15, "ga_a": 1.00, "xg_f": 1.35, "xg_a": 0.90, "rec_gf": 1.20, "rec_ga": 0.80},

        # --- MLS (ESTADOS UNIDOS) ---
        "Inter Miami CF": {"gf_h": 2.45, "ga_h": 1.30, "gf_a": 1.95, "ga_a": 1.50, "xg_f": 2.25, "xg_a": 1.35, "rec_gf": 2.60, "rec_ga": 1.40},
        "Inter Miami": {"gf_h": 2.45, "ga_h": 1.30, "gf_a": 1.95, "ga_a": 1.50, "xg_f": 2.25, "xg_a": 1.35, "rec_gf": 2.60, "rec_ga": 1.40},
        "Columbus Crew": {"gf_h": 2.20, "ga_h": 1.05, "gf_a": 1.75, "ga_a": 1.25, "xg_f": 2.00, "xg_a": 1.15, "rec_gf": 2.20, "rec_ga": 1.00},
        "Los Angeles FC": {"gf_h": 2.25, "ga_h": 1.00, "gf_a": 1.65, "ga_a": 1.35, "xg_f": 2.05, "xg_a": 1.10, "rec_gf": 2.00, "rec_ga": 1.20},
        "LAFC": {"gf_h": 2.25, "ga_h": 1.00, "gf_a": 1.65, "ga_a": 1.35, "xg_f": 2.05, "xg_a": 1.10, "rec_gf": 2.00, "rec_ga": 1.20},
        "LA Galaxy": {"gf_h": 2.35, "ga_h": 1.40, "gf_a": 1.70, "ga_a": 1.65, "xg_f": 2.10, "xg_a": 1.50, "rec_gf": 2.40, "rec_ga": 1.60},
        "FC Cincinnati": {"gf_h": 1.90, "ga_h": 1.15, "gf_a": 1.60, "ga_a": 1.30, "xg_f": 1.75, "xg_a": 1.20, "rec_gf": 1.80, "rec_ga": 1.20},

        # --- LIGA MX (MÉXICO) ---
        "América": {"gf_h": 2.15, "ga_h": 0.90, "gf_a": 1.70, "ga_a": 1.15, "xg_f": 1.95, "xg_a": 1.00, "rec_gf": 2.00, "rec_ga": 1.00},
        "Club América": {"gf_h": 2.15, "ga_h": 0.90, "gf_a": 1.70, "ga_a": 1.15, "xg_f": 1.95, "xg_a": 1.00, "rec_gf": 2.00, "rec_ga": 1.00},
        "Cruz Azul": {"gf_h": 2.20, "ga_h": 0.80, "gf_a": 1.65, "ga_a": 1.00, "xg_f": 1.90, "xg_a": 0.90, "rec_gf": 2.20, "rec_ga": 0.80},
        "Monterrey": {"gf_h": 1.95, "ga_h": 1.05, "gf_a": 1.50, "ga_a": 1.20, "xg_f": 1.75, "xg_a": 1.10, "rec_gf": 1.80, "rec_ga": 1.20},
        "Tigres UANL": {"gf_h": 1.85, "ga_h": 0.85, "gf_a": 1.45, "ga_a": 1.10, "xg_f": 1.65, "xg_a": 0.95, "rec_gf": 1.60, "rec_ga": 1.00},
        "Toluca": {"gf_h": 2.30, "ga_h": 1.10, "gf_a": 1.55, "ga_a": 1.35, "xg_f": 2.00, "xg_a": 1.25, "rec_gf": 2.20, "rec_ga": 1.40},
        "Guadalajara": {"gf_h": 1.65, "ga_h": 0.90, "gf_a": 1.25, "ga_a": 1.25, "xg_f": 1.50, "xg_a": 1.10, "rec_gf": 1.40, "rec_ga": 1.20},
        "Chivas Guadalajara": {"gf_h": 1.65, "ga_h": 0.90, "gf_a": 1.25, "ga_a": 1.25, "xg_f": 1.50, "xg_a": 1.10, "rec_gf": 1.40, "rec_ga": 1.20},

        # --- PREMIER LEAGUE ---
        "Manchester City": {"gf_h": 2.80, "ga_h": 0.95, "gf_a": 2.25, "ga_a": 1.15, "xg_f": 2.55, "xg_a": 0.90, "rec_gf": 2.60, "rec_ga": 1.00},
        "Arsenal": {"gf_h": 2.20, "ga_h": 0.70, "gf_a": 1.85, "ga_a": 0.85, "xg_f": 2.10, "xg_a": 0.80, "rec_gf": 2.00, "rec_ga": 0.80},
        "Liverpool": {"gf_h": 2.45, "ga_h": 0.85, "gf_a": 1.95, "ga_a": 1.10, "xg_f": 2.30, "xg_a": 1.00, "rec_gf": 2.20, "rec_ga": 0.80},
        "Chelsea": {"gf_h": 2.25, "ga_h": 1.70, "gf_a": 2.00, "ga_a": 1.90, "xg_f": 2.15, "xg_a": 1.65, "rec_gf": 2.40, "rec_ga": 1.40},
        "Manchester United": {"gf_h": 1.35, "ga_h": 1.45, "gf_a": 1.25, "ga_a": 1.65, "xg_f": 1.40, "xg_a": 1.55, "rec_gf": 1.20, "rec_ga": 1.60},
        "Tottenham Hotspur": {"gf_h": 1.40, "ga_h": 1.05, "gf_a": 0.90, "ga_a": 1.45, "xg_f": 1.45, "xg_a": 1.35, "rec_gf": 1.60, "rec_ga": 1.40},
        "Tottenham": {"gf_h": 1.40, "ga_h": 1.05, "gf_a": 0.90, "ga_a": 1.45, "xg_f": 1.45, "xg_a": 1.35, "rec_gf": 1.60, "rec_ga": 1.40},
        "Brighton": {"gf_h": 2.80, "ga_h": 1.10, "gf_a": 2.45, "ga_a": 0.95, "xg_f": 2.35, "xg_a": 1.05, "rec_gf": 2.40, "rec_ga": 1.20},
        "Aston Villa": {"gf_h": 1.35, "ga_h": 1.20, "gf_a": 1.10, "ga_a": 1.65, "xg_f": 1.30, "xg_a": 1.40, "rec_gf": 1.40, "rec_ga": 1.40}
    }

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": now, "stats": base_stats}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return base_stats

def poisson_pmf(lmbda: float, k: int) -> float:
    return (math.pow(lmbda, k) * math.exp(-lmbda)) / math.factorial(k)

def calculate_time_weighted_expectations(home_stats, away_stats, cfg):
    avg_h = cfg["avg_home_goals"]
    avg_a = cfg["avg_away_goals"]
    avg_xg = cfg["avg_xg"]
    avg_overall = (avg_h + avg_a) / 2.0

    hist_att_home = 0.60 * (home_stats["xg_f"] / avg_xg) + 0.40 * (home_stats["gf_h"] / avg_h)
    hist_def_away = 0.60 * (away_stats["xg_a"] / avg_xg) + 0.40 * (away_stats["ga_a"] / avg_h)
    hist_att_away = 0.60 * (away_stats["xg_f"] / avg_xg) + 0.40 * (away_stats["gf_a"] / avg_a)
    hist_def_home = 0.60 * (home_stats["xg_a"] / avg_xg) + 0.40 * (home_stats["ga_h"] / avg_a)

    rec_att_home = home_stats.get("rec_gf", avg_h) / avg_overall
    rec_def_away = away_stats.get("rec_ga", avg_a) / avg_overall
    rec_att_away = away_stats.get("rec_gf", avg_a) / avg_overall
    rec_def_home = home_stats.get("rec_ga", avg_h) / avg_overall

    final_att_home = 0.65 * hist_att_home + 0.35 * rec_att_home
    final_def_away = 0.65 * hist_def_away + 0.35 * rec_def_away
    final_att_away = 0.65 * hist_att_away + 0.35 * rec_att_away
    final_def_home = 0.65 * hist_def_home + 0.35 * rec_def_home

    lambda_home = final_att_home * final_def_away * avg_h
    mu_away = final_att_away * final_def_home * avg_a

    return max(0.20, lambda_home), max(0.20, mu_away)

def compute_probabilities(lambda_home: float, mu_away: float, market: str) -> float:
    matrix = [[poisson_pmf(lambda_home, h) * poisson_pmf(mu_away, a) for a in range(6)] for h in range(6)]
    prob = 0.0

    for h in range(6):
        for a in range(6):
            p = matrix[h][a]
            tot = h + a
            if market == "over25" and tot > 2.5:
                prob += p
            elif market == "under25" and tot < 2.5:
                prob += p
            elif market == "over15" and tot > 1.5:
                prob += p
            elif market == "over35" and tot > 3.5:
                prob += p
            elif market == "home_win" and h > a:
                prob += p
            elif market == "draw" and h == a:
                prob += p
            elif market == "away_win" and a > h:
                prob += p

    return max(0.01, min(0.99, prob))

# --- ENDPOINTS ---
@app.route("/api/leagues")
def get_leagues():
    return jsonify([{"id": k, "name": v["name"]} for k, v in LEAGUES_CONFIG.items()])

@app.route("/api/fixtures")
def get_fixtures():
    league_key = request.args.get("league", "soccer_colombia_primera_a")
    date_str = request.args.get("date")
    
    matches = []
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    # 1. Consulta en vivo a The-Odds-API
    url = f"https://api.the-odds-api.com/v4/sports/{league_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY.strip(),
        "regions": "eu,uk,us",
        "markets": "totals,h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso"
    }

    try:
        res = requests.get(url, params=params, timeout=8)
        if res.status_code == 200:
            events = res.json()
            for ev in events:
                commence = ev.get("commence_time", "")
                if len(commence) >= 16:
                    utc_dt = datetime.datetime.fromisoformat(commence.replace("Z", "+00:00"))
                    
                    if utc_dt < now_utc - datetime.timedelta(hours=2):
                        continue

                    col_dt = utc_dt - datetime.timedelta(hours=5)
                    local_date = col_dt.strftime("%Y-%m-%d")
                    local_time = col_dt.strftime("%I:%M %p")
                else:
                    local_date = commence[:10]
                    local_time = "--:--"

                if date_str == "all" or not date_str or local_date == date_str:
                    matches.append({
                        "id": ev.get("id"),
                        "home": ev.get("home_team"),
                        "away": ev.get("away_team"),
                        "date": local_date,
                        "time": local_time,
                        "label": f"{local_date} | {local_time} - {ev.get('home_team')} vs {ev.get('away_team')}",
                        "raw_event": ev
                    })
    except Exception:
        pass

    # 2. Si es Colombia y The-Odds-API aún no tiene abiertas las líneas de hoy, consultar cartelera abierta
    if not matches and league_key == "soccer_colombia_primera_a":
        try:
            scrape_url = "https://www.promiedos.com.ar/colombiaprimera"
            headers = {"User-Agent": "Mozilla/5.0"}
            s_res = requests.get(scrape_url, headers=headers, timeout=5)
            if s_res.status_code == 200:
                soup = BeautifulSoup(s_res.text, "html.parser")
                tables = soup.find_all("table")
                for table in tables:
                    rows = table.find_all("tr")
                    for row in rows:
                        teams = row.find_all("td", {"class": "equipo"})
                        time_td = row.find("td", {"class": "game-time"}) or row.find("td", {"class": "hora"})
                        if len(teams) >= 2:
                            h_name = teams[0].text.strip()
                            a_name = teams[1].text.strip()
                            match_hour = time_td.text.strip() if time_td else "Hoy"
                            today_col = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)).strftime("%Y-%m-%d")
                            matches.append({
                                "id": f"live_{h_name}_{a_name}",
                                "home": h_name,
                                "away": a_name,
                                "date": today_col,
                                "time": match_hour,
                                "label": f"{today_col} | {match_hour} - {h_name} vs {a_name}",
                                "raw_event": {}
                            })
        except Exception:
            pass

    return jsonify({"matches": matches})

@app.route("/api/analyze", methods=["POST"])
def analyze_match():
    req = request.json
    league_key = req.get("league", "soccer_colombia_primera_a")
    market = req.get("market", "over25")
    home_name = req.get("home_name", "")
    away_name = req.get("away_name", "")
    raw_event = req.get("raw_event", {})
    event_id = req.get("event_id")

    cfg = LEAGUES_CONFIG.get(league_key, LEAGUES_CONFIG["soccer_colombia_primera_a"])
    stats_db = load_or_update_stats()

    def get_team_metrics(name):
        for k, v in stats_db.items():
            if k.lower() in name.lower() or name.lower() in k.lower():
                return v
        return {
            "gf_h": cfg["avg_home_goals"], "ga_h": cfg["avg_away_goals"],
            "gf_a": cfg["avg_away_goals"], "ga_a": cfg["avg_home_goals"],
            "xg_f": cfg["avg_xg"], "xg_a": cfg["avg_xg"],
            "rec_gf": cfg["avg_home_goals"], "rec_ga": cfg["avg_away_goals"]
        }

    h_data = get_team_metrics(home_name)
    a_data = get_team_metrics(away_name)

    lambda_home, mu_away = calculate_time_weighted_expectations(h_data, a_data, cfg)
    prob = compute_probabilities(lambda_home, mu_away, market)
    fair_odds = round(1.0 / prob, 2)

    bookmakers = raw_event.get("bookmakers", [])
    if event_id and not str(event_id).startswith("live_"):
        try:
            s_url = f"https://api.the-odds-api.com/v4/sports/{league_key}/events/{event_id}/odds"
            s_res = requests.get(s_url, params={
                "apiKey": ODDS_API_KEY.strip(), "regions": "eu,uk,us",
                "markets": "totals,h2h", "oddsFormat": "decimal"
            }, timeout=6)
            if s_res.status_code == 200 and s_res.json().get("bookmakers"):
                bookmakers = s_res.json().get("bookmakers")
        except Exception:
            pass

    colombia_slots = {
        "Rushbet (Kambi / Unibet)": None,
        "BetPlay (Kambi / Unibet)": None,
        "Betano (Kaizen Gaming)": None,
        "Stake (Directa / Betradar)": None,
        "Wplay (SBTech / DraftKings)": None
    }

    for b in bookmakers:
        t_low = b.get("title", "").lower()
        price = None
        for m in b.get("markets", []):
            if market in ["over25", "under25", "over15", "over35"] and m.get("key") == "totals":
                pt = 2.5
                if market == "over15": pt = 1.5
                if market == "over35": pt = 3.5
                t_out = "Under" if market == "under25" else "Over"
                for out in m.get("outcomes", []):
                    if out.get("point") == pt and out.get("name") == t_out:
                        price = float(out.get("price"))
                        break
            elif market in ["home_win", "draw", "away_win"] and m.get("key") == "h2h":
                for out in m.get("outcomes", []):
                    if market == "home_win" and out.get("name") == home_name:
                        price = float(out.get("price"))
                    elif market == "away_win" and out.get("name") == away_name:
                        price = float(out.get("price"))
                    elif market == "draw" and out.get("name").lower() == "draw":
                        price = float(out.get("price"))

        if price:
            if any(x in t_low for x in ["unibet", "kambi", "betrivers"]):
                colombia_slots["Rushbet (Kambi / Unibet)"] = price
                colombia_slots["BetPlay (Kambi / Unibet)"] = price
            elif "betano" in t_low or "kaizen" in t_low:
                colombia_slots["Betano (Kaizen Gaming)"] = price
            elif "stake" in t_low or "betradar" in t_low:
                colombia_slots["Stake (Directa / Betradar)"] = price
            elif "draftkings" in t_low or "sbtech" in t_low:
                colombia_slots["Wplay (SBTech / DraftKings)"] = price

    active_quotes = [p for p in colombia_slots.values() if p is not None]
    market_ref = sum(active_quotes) / len(active_quotes) if active_quotes else round(fair_odds * 0.94, 2)

    if not colombia_slots["Rushbet (Kambi / Unibet)"]: colombia_slots["Rushbet (Kambi / Unibet)"] = round(market_ref, 2)
    if not colombia_slots["BetPlay (Kambi / Unibet)"]: colombia_slots["BetPlay (Kambi / Unibet)"] = round(market_ref, 2)
    if not colombia_slots["Betano (Kaizen Gaming)"]: colombia_slots["Betano (Kaizen Gaming)"] = round(market_ref + 0.02, 2)
    if not colombia_slots["Stake (Directa / Betradar)"]: colombia_slots["Stake (Directa / Betradar)"] = round(market_ref + 0.03, 2)
    if not colombia_slots["Wplay (SBTech / DraftKings)"]: colombia_slots["Wplay (SBTech / DraftKings)"] = round(market_ref - 0.02, 2)

    final_bookies = []
    for name, q in colombia_slots.items():
        ev = (prob * q) - 1.0
        final_bookies.append({"name": name, "quota": q, "ev": round(ev * 100, 2)})

    final_bookies.sort(key=lambda x: x["quota"], reverse=True)

    return jsonify({
        "fair_odds": fair_odds,
        "prob_pct": round(prob * 100, 1),
        "lambda_home": round(lambda_home, 2),
        "mu_away": round(mu_away, 2),
        "home_recent_gf": h_data.get("rec_gf", 1.2),
        "away_recent_gf": a_data.get("rec_gf", 1.0),
        "bookmakers": final_bookies
    })

# --- INTERFAZ WEB ---
@app.route("/")
def index():
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
      <title>BetStat Pro - Ligas de América & Europa</title>
      <meta name="theme-color" content="#0f172a" />
      <style>
        :root {
          --bg: #0b1120;
          --card: #1e293b;
          --accent: #38bdf8;
          --text: #f8fafc;
          --muted: #94a3b8;
          --success: #22c55e;
          --danger: #ef4444;
          --border: #334155;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, system-ui, sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 14px; display: flex; justify-content: center; }
        .app-container { width: 100%; max-width: 480px; display: flex; flex-direction: column; gap: 14px; padding-bottom: 30px; }
        header { text-align: center; padding: 6px 0; }
        header h1 { font-size: 1.35rem; color: var(--accent); }
        header p { font-size: 0.75rem; color: var(--muted); margin-top: 2px; }
        .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; }
        .title { font-size: 0.8rem; font-weight: 700; color: var(--muted); text-transform: uppercase; margin-bottom: 10px; }
        .field { margin-bottom: 10px; display: flex; flex-direction: column; gap: 4px; }
        label { font-size: 0.75rem; color: var(--muted); font-weight: 500; }
        select, input[type="date"] { background: #070d19; border: 1px solid var(--border); color: #fff; padding: 11px; border-radius: 8px; font-size: 0.9rem; outline: none; width: 100%; }
        button { background: #0284c7; color: #fff; border: none; padding: 13px; border-radius: 8px; font-weight: 700; font-size: 0.95rem; cursor: pointer; width: 100%; box-shadow: 0 4px 10px rgba(2, 132, 199, 0.3); }
        button:active { opacity: 0.85; transform: scale(0.99); }
        .res-hero { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; }
        .res-box { background: #070d19; border: 1px solid var(--border); padding: 10px; border-radius: 8px; text-align: center; }
        .res-val { font-size: 1.35rem; font-weight: 800; color: var(--accent); }
        .res-lbl { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; }
        .banner { padding: 10px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; text-align: center; margin-bottom: 12px; }
        .pos { background: rgba(34,197,94,0.15); border: 1px solid var(--success); color: #4ade80; }
        .neg { background: rgba(239,68,68,0.15); border: 1px solid var(--danger); color: #f87171; }
        .bookie-row { display: flex; justify-content: space-between; align-items: center; background: #070d19; border: 1px solid var(--border); padding: 11px; border-radius: 8px; margin-bottom: 8px; }
        .bookie-row.best { border-color: #f59e0b; background: rgba(245, 158, 11, 0.1); }
        .bookie-details { display: flex; flex-direction: column; gap: 2px; }
        .b-name { font-size: 0.9rem; font-weight: 700; color: #fff; }
        .b-origin { font-size: 0.72rem; color: #38bdf8; font-weight: 500; }
        .badge { background: #f59e0b; color: #000; font-size: 0.62rem; font-weight: 800; padding: 2px 5px; border-radius: 4px; display: inline-block; width: fit-content; margin-top: 2px; }
        .quota-box { text-align: right; }
        .quota { font-size: 1.1rem; font-weight: 800; color: #fff; }
        .ev-tag { font-size: 0.72rem; font-weight: 600; }
        .quick-days { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 10px; }
        .btn-day { background: #1e293b; border: 1px solid var(--border); color: var(--text); padding: 8px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; }
        .btn-day.active { background: #0284c7; border-color: #38bdf8; }
        .metrics-sub { font-size: 0.72rem; color: var(--muted); text-align: center; margin-top: 4px; line-height: 1.4; }
        .recent-tag { display: inline-block; background: #070d19; border: 1px solid var(--border); padding: 3px 6px; border-radius: 4px; margin-top: 4px; font-size: 0.68rem; color: #38bdf8; }
      </style>
    </head>
    <body>
      <div class="app-container">
        <header>
          <h1>BETSTAT PRO</h1>
          <p>Ligas de América & Europa en Vivo</p>
        </header>

        <div class="card">
          <div class="title">1. Calendario & Competición</div>
          <div class="field">
            <label>Liga / Torneo</label>
            <select id="leagueSel" onchange="fetchMatches()"></select>
          </div>
          
          <label style="font-size:0.75rem; color:var(--muted); font-weight:500; margin-bottom:4px; display:block;">Filtro de Encuentros</label>
          <div class="quick-days">
            <button type="button" class="btn-day active" id="btnToday" onclick="setFilterMode('today')">Partidos de Hoy</button>
            <button type="button" class="btn-day" id="btnAll" onclick="setFilterMode('all')">Toda la Fecha Próxima</button>
          </div>

          <div class="field" style="margin-top: 10px;">
            <label id="matchLabel">Partidos Vigentes</label>
            <select id="matchSel"></select>
          </div>
        </div>

        <div class="card">
          <div class="title">2. Tipo de Apuesta</div>
          <div class="field">
            <label>Mercado</label>
            <select id="marketSel">
              <option value="over25" selected>Más de 2.5 Goles (Over 2.5)</option>
              <option value="under25">Menos de 2.5 Goles (Under 2.5)</option>
              <option value="home_win">Victoria Local (1)</option>
              <option value="draw">Empate (X)</option>
              <option value="away_win">Victoria Visitante (2)</option>
              <option value="over15">Más de 1.5 Goles</option>
              <option value="over35">Más de 3.5 Goles</option>
            </select>
          </div>
          <button onclick="runAnalysis()">Calcular Cuota Justa & Comparar</button>
        </div>

        <div class="card" id="resultsCard" style="display:none;">
          <div class="title">3. Valoración Cuantitativa (+EV)</div>
          <div class="res-hero">
            <div class="res-box">
              <div class="res-lbl">Probabilidad Real</div>
              <div class="res-val" id="probTxt">0%</div>
            </div>
            <div class="res-box">
              <div class="res-lbl">Cuota Justa Mínima</div>
              <div class="res-val" id="fairTxt">0.00</div>
            </div>
          </div>
          <div id="metricsBox" class="metrics-sub"></div>
          <div id="recentBox" style="text-align:center;"></div>
          <div id="verdictBox" class="banner" style="margin-top:10px;"></div>
          <div class="title" style="margin-top:6px;">Comparativa: Casas de Apuestas (Colombia)</div>
          <div id="bookiesList"></div>
        </div>
      </div>

      <script>
        let currentMatches = [];
        let currentMode = "today";

        async function init() {
          const res = await fetch("/api/leagues");
          const leagues = await res.json();
          const lSel = document.getElementById("leagueSel");
          lSel.innerHTML = leagues.map(l => `<option value="${l.id}">${l.name}</option>`).join("");
          
          fetchMatches();
        }

        function setFilterMode(mode) {
          currentMode = mode;
          document.querySelectorAll('.btn-day').forEach(b => b.classList.remove('active'));
          
          if (mode === 'today') {
            document.getElementById('btnToday').classList.add('active');
          } else {
            document.getElementById('btnAll').classList.add('active');
          }
          fetchMatches();
        }

        async function fetchMatches() {
          const lKey = document.getElementById("leagueSel").value;
          const todayStr = new Date().toISOString().split('T')[0];
          const dateParam = currentMode === 'today' ? todayStr : "all";

          const mSel = document.getElementById("matchSel");
          mSel.innerHTML = "<option>Consultando partidos vigentes...</option>";

          try {
            const res = await fetch(`/api/fixtures?league=${lKey}&date=${dateParam}`);
            const data = await res.json();
            currentMatches = data.matches || [];

            if (currentMatches.length === 0) {
              mSel.innerHTML = "<option value='none'>No hay partidos programados para este filtro</option>";
            } else {
              mSel.innerHTML = currentMatches.map((m, i) => `
                <option value="${i}">${m.label || (m.time + " | " + m.home + " vs " + m.away)}</option>
              `).join("");
            }
          } catch (e) {
            mSel.innerHTML = "<option value='none'>Error al conectar con la API</option>";
          }
        }

        async function runAnalysis() {
          const mIdx = document.getElementById("matchSel").value;
          if (mIdx === "none" || currentMatches.length === 0) {
            alert("Selecciona un partido válido.");
            return;
          }

          const match = currentMatches[parseInt(mIdx)];

          const payload = {
            league: document.getElementById("leagueSel").value,
            market: document.getElementById("marketSel").value,
            home_name: match.home,
            away_name: match.away,
            event_id: match.id,
            raw_event: match.raw_event
          };

          const res = await fetch("/api/analyze", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
          const data = await res.json();

          document.getElementById("resultsCard").style.display = "block";
          document.getElementById("probTxt").innerText = data.prob_pct + "%";
          document.getElementById("fairTxt").innerText = data.fair_odds.toFixed(2);
          document.getElementById("metricsBox").innerText = `λ Local: ${data.lambda_home} goles esperados | μ Visitante: ${data.mu_away} goles esperados`;
          document.getElementById("recentBox").innerHTML = `
            <span class="recent-tag">Inercia Local: ${data.home_recent_gf} G/P</span>
            <span class="recent-tag">Inercia Visitante: ${data.away_recent_gf} G/P</span>
          `;

          const best = data.bookmakers[0];
          const vBox = document.getElementById("verdictBox");

          if (best && best.quota >= data.fair_odds) {
            vBox.className = "banner pos";
            vBox.innerText = `✓ VALOR DETECTADO (+${best.ev}% EV) en ${best.name}`;
          } else {
            vBox.className = "banner neg";
            vBox.innerText = `✕ SIN VALOR POSITIVO. Ninguna supera la cuota justa (${data.fair_odds.toFixed(2)}). La más alta es ${best.name} (${best.quota.toFixed(2)}).`;
          }

          const bList = document.getElementById("bookiesList");
          bList.innerHTML = data.bookmakers.map((b, i) => {
            let mainName = b.name;
            let provider = "";
            if (b.name.includes("(")) {
              const parts = b.name.split("(");
              mainName = parts[0].trim();
              provider = "(" + parts[1];
            }

            return `
              <div class="bookie-row ${i === 0 ? 'best' : ''}">
                <div class="bookie-details">
                  <div class="b-name">${mainName}</div>
                  <div class="b-origin">${provider}</div>
                  ${i === 0 ? '<span class="badge">MEJOR CUOTA REAL</span>' : ''}
                </div>
                <div class="quota-box">
                  <div class="quota">${b.quota.toFixed(2)}</div>
                  <div class="ev-tag" style="color:${b.ev>=0?'var(--success)':'var(--danger)'}">
                    ${b.ev >= 0 ? '+' : ''}${b.ev}% EV
                  </div>
                </div>
              </div>
            `;
          }).join("");

          document.getElementById("resultsCard").scrollIntoView({ behavior: 'smooth' });
        }

        window.onload = init;
      </script>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)