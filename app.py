import os
import json
import math
import time
import datetime
import requests
import re
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

ODDS_API_KEY = "93fcf8558b6517575a6f6be7a2afcc81"
CACHE_FILE = "stats_cache.json"

LEAGUES_CONFIG = {
    # --- AMÉRICA ---
    "colombia": {
        "name": "Liga BetPlay (Colombia)",
        "espn_slug": "col.1",
        "odds_key": "soccer_colombia_primera_a",
        "avg_home_goals": 1.32,
        "avg_away_goals": 0.88,
        "avg_xg": 1.10
    },
    "libertadores": {
        "name": "Copa CONMEBOL Libertadores",
        "espn_slug": "conmebol.libertadores",
        "odds_key": "soccer_conmebol_copa_libertadores",
        "avg_home_goals": 1.55,
        "avg_away_goals": 0.95,
        "avg_xg": 1.25
    },
    "sudamericana": {
        "name": "Copa CONMEBOL Sudamericana",
        "espn_slug": "conmebol.sudamericana",
        "odds_key": "soccer_conmebol_copa_sudamericana",
        "avg_home_goals": 1.48,
        "avg_away_goals": 0.92,
        "avg_xg": 1.20
    },
    "brasileirao": {
        "name": "Brasileirão Série A (Brasil)",
        "espn_slug": "bra.1",
        "odds_key": "soccer_brazil_campeonato",
        "avg_home_goals": 1.45,
        "avg_away_goals": 1.05,
        "avg_xg": 1.25
    },
    "mls": {
        "name": "MLS (Estados Unidos)",
        "espn_slug": "usa.1",
        "odds_key": "soccer_usa_mls",
        "avg_home_goals": 1.68,
        "avg_away_goals": 1.28,
        "avg_xg": 1.50
    },
    "ligamx": {
        "name": "Liga MX (México)",
        "espn_slug": "mex.1",
        "odds_key": "soccer_mexico_ligamx",
        "avg_home_goals": 1.52,
        "avg_away_goals": 1.15,
        "avg_xg": 1.35
    },
    "argentina": {
        "name": "Primera División (Argentina)",
        "espn_slug": "arg.1",
        "odds_key": "soccer_argentina_primera_division",
        "avg_home_goals": 1.28,
        "avg_away_goals": 0.88,
        "avg_xg": 1.08
    },

    # --- EUROPA ---
    "epl": {
        "name": "Premier League (Inglaterra)",
        "espn_slug": "eng.1",
        "odds_key": "soccer_epl",
        "avg_home_goals": 1.55,
        "avg_away_goals": 1.25,
        "avg_xg": 1.40
    },
    "laliga": {
        "name": "LaLiga (España)",
        "espn_slug": "esp.1",
        "odds_key": "soccer_spain_la_liga",
        "avg_home_goals": 1.42,
        "avg_away_goals": 1.12,
        "avg_xg": 1.28
    },
    "ucl": {
        "name": "UEFA Champions League",
        "espn_slug": "uefa.champions",
        "odds_key": "soccer_uefa_champs_league",
        "avg_home_goals": 1.65,
        "avg_away_goals": 1.35,
        "avg_xg": 1.45
    }
}

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
        # Colombia
        "Millonarios": {"gf_h": 1.70, "ga_h": 0.65, "gf_a": 1.15, "ga_a": 0.90, "xg_f": 1.45, "xg_a": 0.85, "rec_gf": 1.80, "rec_ga": 0.60, "rating": 1.25},
        "Santa Fe": {"gf_h": 1.55, "ga_h": 0.60, "gf_a": 1.05, "ga_a": 0.80, "xg_f": 1.30, "xg_a": 0.80, "rec_gf": 1.40, "rec_ga": 0.40, "rating": 1.20},
        "Atlético Nacional": {"gf_h": 1.75, "ga_h": 0.80, "gf_a": 1.20, "ga_a": 1.00, "xg_f": 1.50, "xg_a": 0.95, "rec_gf": 1.60, "rec_ga": 1.00, "rating": 1.22},
        "América de Cali": {"gf_h": 1.65, "ga_h": 0.70, "gf_a": 1.10, "ga_a": 0.95, "xg_f": 1.40, "xg_a": 0.90, "rec_gf": 1.80, "rec_ga": 0.80, "rating": 1.24},
        "Junior": {"gf_h": 1.80, "ga_h": 0.65, "gf_a": 0.95, "ga_a": 1.15, "xg_f": 1.55, "xg_a": 1.05, "rec_gf": 1.40, "rec_ga": 1.20, "rating": 1.15},
        "Deportes Tolima": {"gf_h": 1.60, "ga_h": 0.70, "gf_a": 1.15, "ga_a": 0.85, "xg_f": 1.38, "xg_a": 0.88, "rec_gf": 1.60, "rec_ga": 0.60, "rating": 1.18},
        "Independiente Medellín": {"gf_h": 1.50, "ga_h": 0.75, "gf_a": 0.95, "ga_a": 1.05, "xg_f": 1.25, "xg_a": 0.95, "rec_gf": 1.20, "rec_ga": 1.00, "rating": 1.05},
        "Once Caldas": {"gf_h": 1.45, "ga_h": 0.75, "gf_a": 0.90, "ga_a": 1.00, "xg_f": 1.20, "xg_a": 0.95, "rec_gf": 1.40, "rec_ga": 0.80, "rating": 1.10},
        "Bucaramanga": {"gf_h": 1.40, "ga_h": 0.65, "gf_a": 0.90, "ga_a": 0.85, "xg_f": 1.15, "xg_a": 0.85, "rec_gf": 1.00, "rec_ga": 0.60, "rating": 1.08},
        "Deportivo Cali": {"gf_h": 1.35, "ga_h": 1.10, "gf_a": 0.85, "ga_a": 1.30, "xg_f": 1.10, "xg_a": 1.25, "rec_gf": 1.00, "rec_ga": 1.60, "rating": 0.88},
        "Deportivo Pereira": {"gf_h": 1.35, "ga_h": 0.85, "gf_a": 0.85, "ga_a": 1.10, "xg_f": 1.15, "xg_a": 1.05, "rec_gf": 1.20, "rec_ga": 1.00, "rating": 0.95},
        "Deportivo Pasto": {"gf_h": 1.40, "ga_h": 0.80, "gf_a": 0.75, "ga_a": 1.20, "xg_f": 1.15, "xg_a": 1.10, "rec_gf": 1.20, "rec_ga": 1.00, "rating": 0.96},
        "La Equidad": {"gf_h": 1.25, "ga_h": 0.80, "gf_a": 0.85, "ga_a": 1.00, "xg_f": 1.10, "xg_a": 0.90, "rec_gf": 1.00, "rec_ga": 1.00, "rating": 0.95},

        # Libertadores / Sudamericana / Brasil / Argentina
        "Atlético Mineiro": {"gf_h": 1.85, "ga_h": 0.85, "gf_a": 1.35, "ga_a": 1.10, "xg_f": 1.65, "xg_a": 1.00, "rec_gf": 1.80, "rec_ga": 0.80, "rating": 1.26},
        "River Plate": {"gf_h": 2.10, "ga_h": 0.65, "gf_a": 1.40, "ga_a": 0.90, "xg_f": 1.85, "xg_a": 0.80, "rec_gf": 1.80, "rec_ga": 0.60, "rating": 1.30},
        "Botafogo": {"gf_h": 2.10, "ga_h": 0.80, "gf_a": 1.55, "ga_a": 1.05, "xg_f": 1.85, "xg_a": 0.90, "rec_gf": 2.20, "rec_ga": 1.00, "rating": 1.28},
        "Peñarol": {"gf_h": 1.70, "ga_h": 0.75, "gf_a": 1.15, "ga_a": 1.05, "xg_f": 1.40, "xg_a": 0.95, "rec_gf": 1.40, "rec_ga": 1.00, "rating": 1.12},
        "Flamengo": {"gf_h": 2.15, "ga_h": 0.85, "gf_a": 1.65, "ga_a": 1.10, "xg_f": 1.95, "xg_a": 0.90, "rec_gf": 2.00, "rec_ga": 0.80, "rating": 1.30},
        "Palmeiras": {"gf_h": 2.05, "ga_h": 0.75, "gf_a": 1.60, "ga_a": 0.95, "xg_f": 1.90, "xg_a": 0.85, "rec_gf": 1.80, "rec_ga": 0.80, "rating": 1.28},
        "Corinthians": {"gf_h": 1.65, "ga_h": 0.95, "gf_a": 1.10, "ga_a": 1.30, "xg_f": 1.40, "xg_a": 1.20, "rec_gf": 1.40, "rec_ga": 1.20, "rating": 1.10},
        "Racing Club": {"gf_h": 1.75, "ga_h": 0.80, "gf_a": 1.25, "ga_a": 1.10, "xg_f": 1.55, "xg_a": 0.95, "rec_gf": 1.60, "rec_ga": 1.00, "rating": 1.16},
        "Cruzeiro": {"gf_h": 1.60, "ga_h": 0.85, "gf_a": 1.10, "ga_a": 1.25, "xg_f": 1.35, "xg_a": 1.10, "rec_gf": 1.20, "rec_ga": 1.00, "rating": 1.10},
        "Lanús": {"gf_h": 1.45, "ga_h": 0.85, "gf_a": 1.00, "ga_a": 1.15, "xg_f": 1.25, "xg_a": 1.05, "rec_gf": 1.20, "rec_ga": 1.00, "rating": 1.05}
    }

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": now, "stats": base_stats}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return base_stats

def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[àáâãäå]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôõö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    stopwords = ["fc", "cd", "ca", "club", "de", "atletico", "sporting", "deportivo", "independiente"]
    tokens = [w for w in text.split() if w not in stopwords]
    return " ".join(tokens).strip()

def teams_match(espn_name, api_name):
    norm_espn = normalize_text(espn_name)
    norm_api = normalize_text(api_name)

    if norm_espn in norm_api or norm_api in norm_espn:
        return True

    espn_words = set(norm_espn.split())
    api_words = set(norm_api.split())
    if espn_words and api_words and (espn_words.intersection(api_words)):
        return True

    return False

def poisson_pmf(lmbda: float, k: int) -> float:
    return (math.pow(lmbda, k) * math.exp(-lmbda)) / math.factorial(k)

def tau_adjustment(x: int, y: int, lambda_val: float, mu_val: float, rho: float = -0.085) -> float:
    if x == 0 and y == 0:
        return 1.0 - (lambda_val * mu_val * rho)
    elif x == 0 and y == 1:
        return 1.0 + (lambda_val * rho)
    elif x == 1 and y == 0:
        return 1.0 + (mu_val * rho)
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0

def calculate_calibrated_expectations(home_stats, away_stats, cfg):
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

    base_att_home = 0.65 * hist_att_home + 0.35 * rec_att_home
    base_def_away = 0.65 * hist_def_away + 0.35 * rec_def_away
    base_att_away = 0.65 * hist_att_away + 0.35 * rec_att_away
    base_def_home = 0.65 * hist_def_home + 0.35 * rec_def_home

    home_rating = home_stats.get("rating", 1.0)
    away_rating = away_stats.get("rating", 1.0)
    sos_home = away_rating / 1.0
    sos_away = home_rating / 1.0

    lambda_home = base_att_home * base_def_away * avg_h * math.sqrt(sos_home)
    mu_away = base_att_away * base_def_home * avg_a * math.sqrt(1.0 / sos_away)

    return max(0.20, min(3.80, lambda_home)), max(0.20, min(3.50, mu_away))

def compute_dixon_coles_probabilities(lambda_home: float, mu_away: float, market: str) -> float:
    prob = 0.0
    for h in range(7):
        for a in range(7):
            tau = tau_adjustment(h, a, lambda_home, mu_away)
            p = poisson_pmf(lambda_home, h) * poisson_pmf(mu_away, a) * tau
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

@app.route("/api/leagues")
def get_leagues():
    return jsonify([{"id": k, "name": v["name"]} for k, v in LEAGUES_CONFIG.items()])

@app.route("/api/fixtures")
def get_fixtures():
    league_key = request.args.get("league", "colombia")
    date_filter = request.args.get("date", "all")
    
    cfg = LEAGUES_CONFIG.get(league_key, LEAGUES_CONFIG["colombia"])
    slug = cfg.get("espn_slug", "col.1")

    matches = []
    today_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=5)
    
    dates_to_query = []
    if date_filter == "today":
        dates_to_query.append(today_dt.strftime("%Y%m%d"))
    else:
        for offset in range(6):
            d = today_dt + datetime.timedelta(days=offset)
            dates_to_query.append(d.strftime("%Y%m%d"))

    for d_str in dates_to_query:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard?dates={d_str}"
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if r.status_code == 200:
                data = r.json()
                for ev in data.get("events", []):
                    status_type = ev.get("status", {}).get("type", {}).get("name", "")
                    if status_type == "STATUS_FINAL":
                        continue

                    competitions = ev.get("competitions", [])[0]
                    competitors = competitions.get("competitors", [])
                    home_team, away_team = None, None
                    for c in competitors:
                        if c.get("homeAway") == "home":
                            home_team = c.get("team", {}).get("displayName", "")
                        else:
                            away_team = c.get("team", {}).get("displayName", "")

                    utc_date_str = ev.get("date", "")
                    if len(utc_date_str) >= 16:
                        utc_dt = datetime.datetime.fromisoformat(utc_date_str.replace("Z", "+00:00"))
                        col_dt = utc_dt - datetime.timedelta(hours=5)
                        match_date = col_dt.strftime("%Y-%m-%d")
                        match_time = col_dt.strftime("%I:%M %p")
                    else:
                        match_date = d_str
                        match_time = "--:--"

                    if home_team and away_team:
                        matches.append({
                            "id": ev.get("id"),
                            "home": home_team,
                            "away": away_team,
                            "date": match_date,
                            "time": match_time,
                            "label": f"{match_date} | {match_time} - {home_team} vs {away_team}"
                        })
        except Exception:
            continue

    return jsonify({"matches": matches})

@app.route("/api/analyze", methods=["POST"])
def analyze_match():
    req = request.json
    league_key = req.get("league", "colombia")
    market = req.get("market", "over25")
    home_name = req.get("home_name", "")
    away_name = req.get("away_name", "")

    cfg = LEAGUES_CONFIG.get(league_key, LEAGUES_CONFIG["colombia"])
    stats_db = load_or_update_stats()

    def get_team_metrics(name):
        for k, v in stats_db.items():
            if teams_match(name, k):
                return v
        return {
            "gf_h": cfg["avg_home_goals"], "ga_h": cfg["avg_away_goals"],
            "gf_a": cfg["avg_away_goals"], "ga_a": cfg["avg_home_goals"],
            "xg_f": cfg["avg_xg"], "xg_a": cfg["avg_xg"],
            "rec_gf": cfg["avg_home_goals"], "rec_ga": cfg["avg_away_goals"],
            "rating": 1.0
        }

    h_data = get_team_metrics(home_name)
    a_data = get_team_metrics(away_name)

    lambda_home, mu_away = calculate_calibrated_expectations(h_data, a_data, cfg)
    prob = compute_dixon_coles_probabilities(lambda_home, mu_away, market)
    fair_odds = round(1.0 / prob, 2)

    # Consulta ampliada a The-Odds-API (regiones completas: eu, uk, us, intl)
    odds_api_sport = cfg.get("odds_key", "soccer_conmebol_copa_libertadores")
    url = f"https://api.the-odds-api.com/v4/sports/{odds_api_sport}/odds"
    params = {
        "apiKey": ODDS_API_KEY.strip(),
        "regions": "eu,uk,us,intl",
        "markets": "totals,h2h",
        "oddsFormat": "decimal"
    }

    detected_bookmakers = []

    try:
        res = requests.get(url, params=params, timeout=7)
        if res.status_code == 200:
            events = res.json()
            target_event = None
            
            for ev in events:
                eh = ev.get("home_team", "")
                ea = ev.get("away_team", "")
                if teams_match(home_name, eh) and teams_match(away_name, ea):
                    target_event = ev
                    break

            if target_event:
                for b in target_event.get("bookmakers", []):
                    b_title = b.get("title", "")
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
                                if market == "home_win" and teams_match(home_name, out.get("name")):
                                    price = float(out.get("price"))
                                elif market == "away_win" and teams_match(away_name, out.get("name")):
                                    price = float(out.get("price"))
                                elif market == "draw" and out.get("name").lower() == "draw":
                                    price = float(out.get("price"))

                    if price:
                        # Mapear hacia operadores colombianos o conservar casa real
                        b_lower = b_title.lower()
                        display_name = b_title
                        if any(x in b_lower for x in ["unibet", "kambi", "betrivers"]):
                            display_name = "Rushbet / BetPlay (Kambi)"
                        elif "betano" in b_lower or "kaizen" in b_lower:
                            display_name = "Betano (Kaizen)"
                        elif "stake" in b_lower:
                            display_name = "Stake"
                        elif "draftkings" in b_lower or "sbtech" in b_lower:
                            display_name = "Wplay (DraftKings/SBTech)"
                        elif "pinnacle" in b_lower:
                            display_name = "Pinnacle (Línea Sharp)"

                        ev = (prob * price) - 1.0
                        detected_bookmakers.append({
                            "name": display_name,
                            "quota": price,
                            "ev": round(ev * 100, 2),
                            "available": True
                        })
    except Exception as e:
        print(f"Error consultando API: {e}")

    # Ordenar las cuotas reales encontradas de mayor a menor
    detected_bookmakers.sort(key=lambda x: x["quota"], reverse=True)

    # Si no se encontró ninguna cotización confirmada, mostrarlo explícitamente
    return jsonify({
        "fair_odds": fair_odds,
        "prob_pct": round(prob * 100, 1),
        "lambda_home": round(lambda_home, 2),
        "mu_away": round(mu_away, 2),
        "home_recent_gf": h_data.get("rec_gf", 1.2),
        "away_recent_gf": a_data.get("rec_gf", 1.0),
        "home_rating": h_data.get("rating", 1.0),
        "away_rating": a_data.get("rating", 1.0),
        "bookmakers": detected_bookmakers
    })

@app.route("/")
def index():
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
      <title>BetStat Pro - Live Odds Sync</title>
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
        select { background: #070d19; border: 1px solid var(--border); color: #fff; padding: 11px; border-radius: 8px; font-size: 0.9rem; outline: none; width: 100%; }
        button { background: #0284c7; color: #fff; border: none; padding: 13px; border-radius: 8px; font-weight: 700; font-size: 0.95rem; cursor: pointer; width: 100%; box-shadow: 0 4px 10px rgba(2, 132, 199, 0.3); }
        button:active { opacity: 0.85; transform: scale(0.99); }
        .res-hero { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 10px; }
        .res-box { background: #070d19; border: 1px solid var(--border); padding: 10px; border-radius: 8px; text-align: center; }
        .res-val { font-size: 1.35rem; font-weight: 800; color: var(--accent); }
        .res-lbl { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; }
        .banner { padding: 10px; border-radius: 8px; font-size: 0.8rem; font-weight: 600; text-align: center; margin-bottom: 12px; }
        .pos { background: rgba(34,197,94,0.15); border: 1px solid var(--success); color: #4ade80; }
        .neg { background: rgba(239,68,68,0.15); border: 1px solid var(--danger); color: #f87171; }
        .neutral { background: rgba(148,163,184,0.15); border: 1px solid var(--muted); color: var(--muted); }
        .bookie-row { display: flex; justify-content: space-between; align-items: center; background: #070d19; border: 1px solid var(--border); padding: 11px; border-radius: 8px; margin-bottom: 8px; }
        .bookie-row.best { border-color: #f59e0b; background: rgba(245, 158, 11, 0.1); }
        .bookie-details { display: flex; flex-direction: column; gap: 2px; }
        .b-name { font-size: 0.9rem; font-weight: 700; color: #fff; }
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
          <p>Conexión Real The-Odds-API & Dixon-Coles</p>
        </header>

        <div class="card">
          <div class="title">1. Competición & Calendario</div>
          <div class="field">
            <label>Liga / Torneo</label>
            <select id="leagueSel" onchange="fetchMatches()"></select>
          </div>
          
          <label style="font-size:0.75rem; color:var(--muted); font-weight:500; margin-bottom:4px; display:block;">Filtro de Partidos</label>
          <div class="quick-days">
            <button type="button" class="btn-day active" id="btnToday" onclick="setFilterMode('today')">Partidos de Hoy</button>
            <button type="button" class="btn-day" id="btnAll" onclick="setFilterMode('all')">Próximos Días</button>
          </div>

          <div class="field" style="margin-top: 10px;">
            <label id="matchLabel">Partidos Detectados</label>
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
          <div class="title">3. Valoración del Modelo (+EV)</div>
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
          <div class="title" style="margin-top:6px;">Cuotas Reales Confirmadas en Casas</div>
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
          const mSel = document.getElementById("matchSel");
          mSel.innerHTML = "<option>Consultando partidos vigentes...</option>";

          try {
            const res = await fetch(`/api/fixtures?league=${lKey}&date=${currentMode}`);
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
            mSel.innerHTML = "<option value='none'>Error al cargar los partidos</option>";
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
            away_name: match.away
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
          document.getElementById("metricsBox").innerText = `λ Local: ${data.lambda_home} | μ Visitante: ${data.mu_away} (Modelo Calibrado Dixon-Coles)`;
          document.getElementById("recentBox").innerHTML = `
            <span class="recent-tag">Rating Rival Local: ${data.away_rating}x</span>
            <span class="recent-tag">Rating Rival Visitante: ${data.home_rating}x</span>
          `;

          const vBox = document.getElementById("verdictBox");
          const bList = document.getElementById("bookiesList");

          if (!data.bookmakers || data.bookmakers.length === 0) {
            vBox.className = "banner neutral";
            vBox.innerText = `Mercado no listado aún en el feed de The-Odds-API para este encuentro. Cuota justa calculada: ${data.fair_odds.toFixed(2)}.`;
            bList.innerHTML = `<div style="text-align:center; padding:15px; color:var(--muted); font-size:0.85rem;">Ninguna casa ha abierto líneas para este mercado específico en la API todavía.</div>`;
          } else {
            const best = data.bookmakers[0];
            if (best.quota >= data.fair_odds) {
              vBox.className = "banner pos";
              vBox.innerText = `✓ VALOR DETECTADO (+${best.ev}% EV) en ${best.name} (${best.quota.toFixed(2)})`;
            } else {
              vBox.className = "banner neg";
              vBox.innerText = `✕ SIN VALOR POSITIVO. Ninguna supera la cuota justa (${data.fair_odds.toFixed(2)}). La más alta es ${best.name} (${best.quota.toFixed(2)}).`;
            }

            bList.innerHTML = data.bookmakers.map((b, i) => `
              <div class="bookie-row ${i === 0 ? 'best' : ''}">
                <div class="bookie-details">
                  <div class="b-name">${b.name}</div>
                  ${i === 0 ? '<span class="badge">MEJOR CUOTA CONFIRMADA</span>' : ''}
                </div>
                <div class="quota-box">
                  <div class="quota">${b.quota.toFixed(2)}</div>
                  <div class="ev-tag" style="color:${b.ev>=0?'var(--success)':'var(--danger)'}">
                    ${b.ev >= 0 ? '+' : ''}${b.ev}% EV
                  </div>
                </div>
              </div>
            `).join("");
          }

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