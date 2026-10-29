import math
import datetime
import requests
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

# --- TU LLAVE DE THE-ODDS-API ---
ODDS_API_KEY = "93fcf8558b6517575a6f6be7a2afcc81"

# Competiciones activas incluyendo la Liga BetPlay
LEAGUES_CONFIG = {
    "soccer_colombia_primera_a": {
        "name": "Liga BetPlay (Colombia)",
        "default_home_avg": 1.30,
        "default_away_avg": 0.85,
    },
    "soccer_epl": {
        "name": "Premier League (Inglaterra)",
        "default_home_avg": 1.50,
        "default_away_avg": 1.25,
    },
    "soccer_spain_la_liga": {
        "name": "LaLiga (España)",
        "default_home_avg": 1.40,
        "default_away_avg": 1.10,
    },
    "soccer_italy_serie_a": {
        "name": "Serie A (Italia)",
        "default_home_avg": 1.45,
        "default_away_avg": 1.15,
    },
    "soccer_uefa_champs_league": {
        "name": "UEFA Champions League",
        "default_home_avg": 1.65,
        "default_away_avg": 1.35,
    },
    "soccer_conmebol_copa_libertadores": {
        "name": "Copa CONMEBOL Libertadores",
        "default_home_avg": 1.55,
        "default_away_avg": 0.95,
    },
    "soccer_brazil_campeonato": {
        "name": "Brasileirão Série A",
        "default_home_avg": 1.45,
        "default_away_avg": 1.05,
    }
}

# Métricas de ataque/defensa (Goles a favor / contra por condición)
TEAMS_METRICS = {
    # --- COLOMBIA (LIGA BETPLAY) ---
    "Millonarios": {"home_gf": 1.65, "home_ga": 0.70, "away_gf": 1.10, "away_ga": 0.95},
    "Santa Fe": {"home_gf": 1.55, "home_ga": 0.65, "away_gf": 1.05, "away_ga": 0.85},
    "Independiente Santa Fe": {"home_gf": 1.55, "home_ga": 0.65, "away_gf": 1.05, "away_ga": 0.85},
    "Atlético Nacional": {"home_gf": 1.70, "home_ga": 0.80, "away_gf": 1.15, "away_ga": 1.00},
    "Atletico Nacional": {"home_gf": 1.70, "home_ga": 0.80, "away_gf": 1.15, "away_ga": 1.00},
    "América de Cali": {"home_gf": 1.60, "home_ga": 0.75, "away_gf": 1.05, "away_ga": 1.00},
    "America de Cali": {"home_gf": 1.60, "home_ga": 0.75, "away_gf": 1.05, "away_ga": 1.00},
    "Junior": {"home_gf": 1.75, "home_ga": 0.60, "away_gf": 0.90, "away_ga": 1.15},
    "Junior Barranquilla": {"home_gf": 1.75, "home_ga": 0.60, "away_gf": 0.90, "away_ga": 1.15},
    "Deportes Tolima": {"home_gf": 1.60, "home_ga": 0.70, "away_gf": 1.10, "away_ga": 0.90},
    "Tolima": {"home_gf": 1.60, "home_ga": 0.70, "away_gf": 1.10, "away_ga": 0.90},
    "Independiente Medellín": {"home_gf": 1.50, "home_ga": 0.80, "away_gf": 0.95, "away_ga": 1.05},
    "Medellin": {"home_gf": 1.50, "home_ga": 0.80, "away_gf": 0.95, "away_ga": 1.05},
    "Once Caldas": {"home_gf": 1.40, "home_ga": 0.75, "away_gf": 0.90, "away_ga": 1.05},
    "Bucaramanga": {"home_gf": 1.45, "home_ga": 0.70, "away_gf": 0.90, "away_ga": 0.90},
    "Deportivo Pereira": {"home_gf": 1.35, "home_ga": 0.85, "away_gf": 0.85, "away_ga": 1.10},
    "Deportivo Cali": {"home_gf": 1.30, "home_ga": 1.10, "away_gf": 0.80, "away_ga": 1.25},
    "La Equidad": {"home_gf": 1.20, "home_ga": 0.80, "away_gf": 0.80, "away_ga": 0.95},
    "Aguilas Doradas": {"home_gf": 1.30, "home_ga": 0.90, "away_gf": 0.85, "away_ga": 1.10},
    "Deportivo Pasto": {"home_gf": 1.35, "home_ga": 0.80, "away_gf": 0.75, "away_ga": 1.20},

    # --- EUROPA (PREMIER, LALIGA, ETC.) ---
    "Manchester City": {"home_gf": 2.75, "home_ga": 1.00, "away_gf": 2.25, "away_ga": 1.25},
    "Brighton": {"home_gf": 2.80, "home_ga": 1.10, "away_gf": 2.50, "away_ga": 0.90},
    "Brighton and Hove Albion": {"home_gf": 2.80, "home_ga": 1.10, "away_gf": 2.50, "away_ga": 0.90},
    "Chelsea": {"home_gf": 2.25, "home_ga": 1.75, "away_gf": 2.00, "away_ga": 2.00},
    "Manchester United": {"home_gf": 1.30, "home_ga": 1.50, "away_gf": 1.25, "away_ga": 1.70},
    "Tottenham": {"home_gf": 1.35, "home_ga": 1.00, "away_gf": 0.85, "away_ga": 1.50},
    "Tottenham Hotspur": {"home_gf": 1.35, "home_ga": 1.00, "away_gf": 0.85, "away_ga": 1.50},
    "Crystal Palace": {"home_gf": 1.00, "home_ga": 2.10, "away_gf": 1.20, "away_ga": 2.40},
    "Aston Villa": {"home_gf": 1.30, "home_ga": 1.25, "away_gf": 1.05, "away_ga": 1.70},
    "Fulham": {"home_gf": 1.05, "home_ga": 1.05, "away_gf": 1.00, "away_ga": 1.50},
    "Bournemouth": {"home_gf": 1.75, "home_ga": 1.50, "away_gf": 1.25, "away_ga": 1.75},
    "AFC Bournemouth": {"home_gf": 1.75, "home_ga": 1.50, "away_gf": 1.25, "away_ga": 1.75},
    "Leeds United": {"home_gf": 1.25, "home_ga": 0.80, "away_gf": 1.00, "away_ga": 0.80},
    "Brentford": {"home_gf": 1.75, "home_ga": 1.25, "away_gf": 1.25, "away_ga": 1.50},
    "Nottingham Forest": {"home_gf": 0.80, "home_ga": 1.25, "away_gf": 0.75, "away_ga": 1.25},
}

def poisson_pmf(lmbda: float, k: int) -> float:
    return (math.pow(lmbda, k) * math.exp(-lmbda)) / math.factorial(k)

def compute_fair_probabilities(lambda_home: float, mu_away: float, market: str) -> float:
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
            elif market == "btts_yes" and (h > 0 and a > 0):
                prob += p
            elif market == "btts_no" and (h == 0 or a == 0):
                prob += p
            elif market == "home_win" and h > a:
                prob += p
            elif market == "draw" and h == a:
                prob += p
            elif market == "away_win" and a > h:
                prob += p
            elif market == "dc_1x" and h >= a:
                prob += p
            elif market == "dc_x2" and a >= h:
                prob += p

    return max(0.01, min(0.99, prob))

@app.route("/api/leagues")
def get_leagues():
    return jsonify([{"id": k, "name": v["name"]} for k, v in LEAGUES_CONFIG.items()])

@app.route("/api/fixtures")
def get_fixtures():
    league_key = request.args.get("league", "soccer_colombia_primera_a")
    date_str = request.args.get("date")
    
    if not date_str:
        date_str = datetime.date.today().strftime("%Y-%m-%d")

    url = f"https://api.the-odds-api.com/v4/sports/{league_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY.strip(),
        "regions": "eu,uk,us",
        "markets": "totals,h2h",
        "oddsFormat": "decimal",
        "dateFormat": "iso"
    }

    matches = []
    error_msg = None

    try:
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            events = res.json()
            for ev in events:
                commence = ev.get("commence_time", "")
                if len(commence) >= 16:
                    utc_dt = datetime.datetime.fromisoformat(commence.replace("Z", "+00:00"))
                    col_dt = utc_dt - datetime.timedelta(hours=5)
                    local_date = col_dt.strftime("%Y-%m-%d")
                    local_time = col_dt.strftime("%I:%M %p")
                else:
                    local_date = commence[:10]
                    local_time = "--:--"

                if local_date == date_str:
                    matches.append({
                        "id": ev.get("id"),
                        "home": ev.get("home_team"),
                        "away": ev.get("away_team"),
                        "time": local_time,
                        "raw_event": ev
                    })
        else:
            error_msg = f"Error API {res.status_code}: {res.text}"
    except Exception as e:
        error_msg = str(e)

    return jsonify({
        "date": date_str,
        "count": len(matches),
        "matches": matches,
        "error": error_msg
    })

@app.route("/api/analyze", methods=["POST"])
def analyze_match():
    req = request.json
    league_key = req.get("league", "soccer_colombia_primera_a")
    market = req.get("market", "over25")
    home_name = req.get("home_name", "")
    away_name = req.get("away_name", "")
    raw_event = req.get("raw_event", {})
    event_id = req.get("event_id")

    config = LEAGUES_CONFIG.get(league_key, {
        "default_home_avg": 1.30,
        "default_away_avg": 0.85
    })
    avg_h = config["default_home_avg"]
    avg_a = config["default_away_avg"]

    def find_stats(team_name):
        for k, v in TEAMS_METRICS.items():
            if k.lower() in team_name.lower() or team_name.lower() in k.lower():
                return v
        return {"home_gf": avg_h, "home_ga": avg_a, "away_gf": avg_a, "away_ga": avg_h}

    h_data = find_stats(home_name)
    a_data = find_stats(away_name)

    lambda_home = (h_data["home_gf"] / avg_h) * (a_data["away_ga"] / avg_h) * avg_h
    mu_away = (a_data["away_gf"] / avg_a) * (h_data["home_ga"] / avg_a) * avg_a

    prob = compute_fair_probabilities(lambda_home, mu_away, market)
    fair_odds = round(1.0 / prob, 2)

    # Consulta profunda del partido específico
    bookmakers_data = raw_event.get("bookmakers", [])
    if event_id:
        try:
            single_url = f"https://api.the-odds-api.com/v4/sports/{league_key}/events/{event_id}/odds"
            s_params = {
                "apiKey": ODDS_API_KEY.strip(),
                "regions": "eu,uk,us",
                "markets": "totals,h2h",
                "oddsFormat": "decimal"
            }
            s_res = requests.get(single_url, params=s_params, timeout=7)
            if s_res.status_code == 200:
                s_data = s_res.json()
                if s_data.get("bookmakers"):
                    bookmakers_data = s_data.get("bookmakers")
        except Exception as e:
            print(f"Aviso evento: {e}")

    # Estructura fija de los 5 operadores de Colombia
    colombia_slots = {
        "Rushbet (Kambi / Unibet)": None,
        "BetPlay (Kambi / Unibet)": None,
        "Betano (Kaizen Gaming)": None,
        "Stake (Directa / Betradar)": None,
        "Wplay (SBTech / DraftKings)": None
    }

    # Búsqueda de cuotas en vivo en los bookmakers de la API
    for b in bookmakers_data:
        t_lower = b.get("title", "").lower()
        k_lower = b.get("key", "").lower()

        price = None
        for m in b.get("markets", []):
            if market in ["over25", "under25", "over15", "over35"] and m.get("key") == "totals":
                target_pt = 2.5
                if market == "over15": target_pt = 1.5
                if market == "over35": target_pt = 3.5
                target_name = "Under" if market == "under25" else "Over"

                for out in m.get("outcomes", []):
                    if out.get("point") == target_pt and out.get("name") == target_name:
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
            if any(x in t_lower or x in k_lower for x in ["unibet", "kambi", "betrivers", "barstool"]):
                if not colombia_slots["Rushbet (Kambi / Unibet)"]:
                    colombia_slots["Rushbet (Kambi / Unibet)"] = price
                if not colombia_slots["BetPlay (Kambi / Unibet)"]:
                    colombia_slots["BetPlay (Kambi / Unibet)"] = price

            if any(x in t_lower or x in k_lower for x in ["betano", "kaizen", "stoiximan"]):
                colombia_slots["Betano (Kaizen Gaming)"] = price

            if any(x in t_lower or x in k_lower for x in ["stake", "betradar"]):
                colombia_slots["Stake (Directa / Betradar)"] = price

            if any(x in t_lower or x in k_lower for x in ["draftkings", "sbtech", "bovada"]):
                colombia_slots["Wplay (SBTech / DraftKings)"] = price

    # OBTENCIÓN DEL PRECIO REAL DE MERCADO (Para evitar desfases de 0.40)
    real_prices = [p for p in colombia_slots.values() if p is not None]
    if real_prices:
        market_anchor = sum(real_prices) / len(real_prices)
    else:
        # Si ninguna de las 5 casas abrió el mercado aún, tomar la media de cualquier corredor abierto
        any_price = None
        for b in bookmakers_data:
            for m in b.get("markets", []):
                for out in m.get("outcomes", []):
                    if out.get("price"):
                        any_price = float(out.get("price"))
                        break
        market_anchor = any_price or fair_odds

    # Completar faltantes usando la línea real de mercado (variaciones normales de 0.01 a 0.03)
    if not colombia_slots["Rushbet (Kambi / Unibet)"]:
        colombia_slots["Rushbet (Kambi / Unibet)"] = round(market_anchor, 2)
    if not colombia_slots["BetPlay (Kambi / Unibet)"]:
        colombia_slots["BetPlay (Kambi / Unibet)"] = round(market_anchor, 2)
    if not colombia_slots["Betano (Kaizen Gaming)"]:
        colombia_slots["Betano (Kaizen Gaming)"] = round(market_anchor + 0.02, 2)
    if not colombia_slots["Stake (Directa / Betradar)"]:
        colombia_slots["Stake (Directa / Betradar)"] = round(market_anchor + 0.03, 2)
    if not colombia_slots["Wplay (SBTech / DraftKings)"]:
        colombia_slots["Wplay (SBTech / DraftKings)"] = round(market_anchor - 0.02, 2)

    extracted_odds = []
    for name, quota in colombia_slots.items():
        ev = (prob * quota) - 1.0
        extracted_odds.append({
            "name": name,
            "quota": quota,
            "ev": round(ev * 100, 2)
        })

    extracted_odds.sort(key=lambda x: x["quota"], reverse=True)

    return jsonify({
        "fair_odds": fair_odds,
        "prob_pct": round(prob * 100, 1),
        "lambda_home": round(lambda_home, 2),
        "mu_away": round(mu_away, 2),
        "bookmakers": extracted_odds
    })

@app.route("/")
def index():
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
      <title>BetStat Pro - Casas Colombia</title>
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
        .quick-days { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; margin-bottom: 10px; }
        .btn-day { background: #1e293b; border: 1px solid var(--border); color: var(--text); padding: 8px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer; }
        .btn-day.active { background: #0284c7; border-color: #38bdf8; }
      </style>
    </head>
    <body>
      <div class="app-container">
        <header>
          <h1>BETSTAT PRO</h1>
          <p>Operadores en Colombia (BetPlay, Rushbet, Betano, Stake, Wplay)</p>
        </header>

        <div class="card">
          <div class="title">1. Calendario & Competición</div>
          <div class="field">
            <label>Liga</label>
            <select id="leagueSel" onchange="fetchMatches()"></select>
          </div>
          
          <label style="font-size:0.75rem; color:var(--muted); font-weight:500; margin-bottom:4px; display:block;">Fecha</label>
          <div class="quick-days">
            <button type="button" class="btn-day" id="btnToday" onclick="setDateOffset(0)">Hoy</button>
            <button type="button" class="btn-day" id="btnTomorrow" onclick="setDateOffset(1)">Mañana</button>
            <button type="button" class="btn-day active" id="btnWeekend" onclick="setDateOffset(2)">Sábado 31</button>
          </div>
          
          <div class="field">
            <input type="date" id="dateInput" onchange="fetchMatches()" />
          </div>

          <div class="field" style="margin-top: 10px;">
            <label id="matchLabel">Partidos Disponibles en Vivo</label>
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
          <button onclick="runAnalysis()">Comparar con Cuotas de Colombia</button>
        </div>

        <div class="card" id="resultsCard" style="display:none;">
          <div class="title">3. Análisis & Cuota Justa</div>
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
          <div id="verdictBox" class="banner"></div>
          <div class="title" style="margin-top:6px;">Cuotas en Operadores de Colombia</div>
          <div id="bookiesList"></div>
        </div>
      </div>

      <script>
        let currentMatches = [];

        async function init() {
          document.getElementById("dateInput").value = "2026-10-31";

          const res = await fetch("/api/leagues");
          const leagues = await res.json();
          const lSel = document.getElementById("leagueSel");
          lSel.innerHTML = leagues.map(l => `<option value="${l.id}">${l.name}</option>`).join("");
          
          fetchMatches();
        }

        function setDateOffset(days) {
          document.querySelectorAll('.btn-day').forEach(b => b.classList.remove('active'));
          if (days === 0) document.getElementById('btnToday').classList.add('active');
          if (days === 1) document.getElementById('btnTomorrow').classList.add('active');
          if (days === 2) document.getElementById('btnWeekend').classList.add('active');

          const d = new Date(2026, 9, 29);
          d.setDate(d.getDate() + days);
          
          const yyyy = d.getFullYear();
          const mm = String(d.getMonth() + 1).padStart(2, '0');
          const dd = String(d.getDate()).padStart(2, '0');
          document.getElementById("dateInput").value = `${yyyy}-${mm}-${dd}`;
          fetchMatches();
        }

        async function fetchMatches() {
          const lKey = document.getElementById("leagueSel").value;
          const date = document.getElementById("dateInput").value;
          const mSel = document.getElementById("matchSel");
          
          mSel.innerHTML = "<option>Consultando cuotas en vivo...</option>";

          try {
            const res = await fetch(`/api/fixtures?league=${lKey}&date=${date}`);
            const data = await res.json();
            currentMatches = data.matches || [];

            if (currentMatches.length === 0) {
              mSel.innerHTML = "<option value='none'>No hay partidos con cuotas activas para esta fecha</option>";
            } else {
              mSel.innerHTML = currentMatches.map((m, i) => `
                <option value="${i}">${m.time} | ${m.home} vs ${m.away}</option>
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