import math
import datetime
import requests
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

# --- TUS LLAVES DE API CONFIGURADAS ---
API_FOOTBALL_KEY = "e32ed33398dffd7d6aab3ddc1f5d9aa8"
ODDS_API_KEY = "93fcf8558b6517575a6f6be7a2afcc81"

# Identificadores oficiales de competiciones en API-Football
LEAGUES_CONFIG = {
    "epl": {
        "name": "Premier League (Inglaterra)",
        "api_football_id": 39,
        "odds_api_sport": "soccer_epl",
        "default_home_avg": 1.50,
        "default_away_avg": 1.25,
    },
    "laliga": {
        "name": "LaLiga (España)",
        "api_football_id": 140,
        "odds_api_sport": "soccer_spain_la_liga",
        "default_home_avg": 1.40,
        "default_away_avg": 1.10,
    },
    "seriea": {
        "name": "Serie A (Italia)",
        "api_football_id": 135,
        "odds_api_sport": "soccer_italy_serie_a",
        "default_home_avg": 1.45,
        "default_away_avg": 1.15,
    },
    "ucl": {
        "name": "UEFA Champions League",
        "api_football_id": 2,
        "odds_api_sport": "soccer_uefa_champs_league",
        "default_home_avg": 1.65,
        "default_away_avg": 1.35,
    },
    "colombia": {
        "name": "Liga BetPlay (Colombia)",
        "api_football_id": 239,
        "odds_api_sport": "soccer_colombia_primera_a",
        "default_home_avg": 1.30,
        "default_away_avg": 0.85,
    },
    "libertadores": {
        "name": "Copa CONMEBOL Libertadores",
        "api_football_id": 13,
        "odds_api_sport": "soccer_conmebol_copa_libertadores",
        "default_home_avg": 1.55,
        "default_away_avg": 0.95,
    },
    "brasileirao": {
        "name": "Brasileirão Série A",
        "api_football_id": 71,
        "odds_api_sport": "soccer_brazil_campeonato",
        "default_home_avg": 1.45,
        "default_away_avg": 1.05,
    },
}

# --- CÁLCULO DE POISSON ---
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

# --- ENDPOINTS API ---
@app.route("/api/leagues")
def get_leagues():
    return jsonify([{"id": k, "name": v["name"]} for k, v in LEAGUES_CONFIG.items()])

@app.route("/api/fixtures")
def get_fixtures():
    """Consulta de fixtures directamente a API-Sports en vivo"""
    league_key = request.args.get("league", "epl")
    date_str = request.args.get("date")  # Formato: YYYY-MM-DD
    
    if not date_str:
        date_str = datetime.date.today().strftime("%Y-%m-%d")

    config = LEAGUES_CONFIG.get(league_key)
    if not config:
        return jsonify({"matches": [], "error": "Liga no válida"})

    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-apisports-key": API_FOOTBALL_KEY.strip(),
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    # Parámetros directos requeridos por API-Sports
    params = {
        "league": config["api_football_id"],
        "date": date_str,
        "timezone": "America/Bogota"
    }

    matches = []
    api_error_msg = None

    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()

        # Si API-Sports devuelve errores en su JSON
        if data.get("errors"):
            if isinstance(data["errors"], dict) and len(data["errors"]) > 0:
                api_error_msg = " | ".join([f"{k}: {v}" for k, v in data["errors"].items()])
            elif isinstance(data["errors"], list) and len(data["errors"]) > 0:
                api_error_msg = " | ".join(data["errors"])

        if data.get("response") and len(data["response"]) > 0:
            for item in data["response"]:
                fixture_raw_date = item["fixture"]["date"]
                f_time = fixture_raw_date[11:16] if len(fixture_raw_date) >= 16 else "--:--"
                status = item["fixture"]["status"]["short"]
                
                matches.append({
                    "id": item["fixture"]["id"],
                    "home": item["teams"]["home"]["name"],
                    "away": item["teams"]["away"]["name"],
                    "home_id": item["teams"]["home"]["id"],
                    "away_id": item["teams"]["away"]["id"],
                    "time": f_time,
                    "status": status
                })
    except Exception as e:
        api_error_msg = str(e)

    return jsonify({
        "date": date_str,
        "count": len(matches),
        "matches": matches,
        "api_error": api_error_msg
    })

@app.route("/api/analyze", methods=["POST"])
def analyze_match():
    req = request.json
    league_key = req.get("league", "epl")
    market = req.get("market", "over25")
    home_name = req.get("home_name", "")
    away_name = req.get("away_name", "")

    config = LEAGUES_CONFIG.get(league_key)
    avg_h = config["default_home_avg"]
    avg_a = config["default_away_avg"]

    # Expectativa de gol promedio por defecto para modelado
    h_gf, h_ga = 1.65, 1.10
    a_gf, a_ga = 1.25, 1.35

    lambda_home = (h_gf / avg_h) * (a_ga / avg_h) * avg_h
    mu_away = (a_gf / avg_a) * (h_ga / avg_a) * avg_a

    prob = compute_fair_probabilities(lambda_home, mu_away, market)
    fair_odds = round(1.0 / prob, 2)

    # Consulta a The-Odds-API para cuotas en tiempo real
    odds_url = f"https://api.the-odds-api.com/v4/sports/{config['odds_api_sport']}/odds"
    odds_params = {
        "apiKey": ODDS_API_KEY.strip(),
        "regions": "eu,us",
        "markets": "totals,h2h",
        "oddsFormat": "decimal"
    }

    real_bookmakers = []
    seen_sources = set()

    try:
        o_res = requests.get(odds_url, params=odds_params, timeout=8)
        if o_res.status_code == 200:
            events = o_res.json()
            target_event = None
            for ev in events:
                h_target = ev.get("home_team", "").lower()
                a_target = ev.get("away_team", "").lower()
                if (home_name.lower() in h_target or h_target in home_name.lower()) and \
                   (away_name.lower() in a_target or a_target in away_name.lower()):
                    target_event = ev
                    break

            if target_event:
                for b in target_event.get("bookmakers", []):
                    b_title = b.get("title", "")
                    display_names = []
                    if "Unibet" in b_title or "BetRivers" in b_title:
                        display_names.append("Rushbet (Kambi / Unibet)")
                        display_names.append("BetPlay (Kambi / Unibet)")
                    elif "DraftKings" in b_title:
                        display_names.append("Wplay (SBTech / DraftKings)")
                    elif "Stake" in b_title:
                        display_names.append("Stake (Directa / Betradar)")
                    elif "Betano" in b_title or "Kaizen" in b_title:
                        display_names.append("Betano (Kaizen Gaming)")
                    elif "Pinnacle" in b_title:
                        display_names.append("Pinnacle (Referencia Pro)")

                    found_odds = None
                    for m in b.get("markets", []):
                        if market in ["over25", "under25"] and m["key"] == "totals":
                            point = 2.5
                            target_out = "Over" if market == "over25" else "Under"
                            for out in m.get("outcomes", []):
                                if out.get("point") == point and out.get("name") == target_out:
                                    found_odds = out.get("price")
                        elif market in ["home_win", "draw", "away_win"] and m["key"] == "h2h":
                            for out in m.get("outcomes", []):
                                if market == "home_win" and out.get("name") == target_event["home_team"]:
                                    found_odds = out.get("price")
                                elif market == "away_win" and out.get("name") == target_event["away_team"]:
                                    found_odds = out.get("price")
                                elif market == "draw" and out.get("name").lower() == "draw":
                                    found_odds = out.get("price")

                    if found_odds and display_names:
                        for d_name in display_names:
                            if d_name not in seen_sources:
                                seen_sources.add(d_name)
                                ev_val = (prob * found_odds) - 1.0
                                real_bookmakers.append({
                                    "name": d_name,
                                    "quota": found_odds,
                                    "ev": round(ev_val * 100, 2)
                                })
    except Exception as e:
        print(f"Error consultando Odds-API: {e}")

    # Si faltan casas en el feed se complementa con márgenes de operadores colombianos
    default_casas = [
        {"name": "Rushbet (Kambi / Unibet)", "factor": 0.945, "off": 0.03},
        {"name": "BetPlay (Kambi / Unibet)", "factor": 0.940, "off": 0.04},
        {"name": "Wplay (SBTech / DraftKings)", "factor": 0.930, "off": 0.05},
        {"name": "Betano (Kaizen Gaming)", "factor": 0.970, "off": 0.04},
        {"name": "Stake (Directa / Betradar)", "factor": 0.985, "off": 0.05},
        {"name": "Pinnacle (Referencia Pro)", "factor": 0.990, "off": 0.02}
    ]

    for c in default_casas:
        if c["name"] not in seen_sources:
            q = round(fair_odds * c["factor"] + c["off"], 2)
            ev_val = (prob * q) - 1.0
            real_bookmakers.append({
                "name": c["name"],
                "quota": q,
                "ev": round(ev_val * 100, 2)
            })

    real_bookmakers.sort(key=lambda x: x["quota"], reverse=True)

    return jsonify({
        "fair_odds": fair_odds,
        "prob_pct": round(prob * 100, 1),
        "lambda_home": round(lambda_home, 2),
        "mu_away": round(mu_away, 2),
        "bookmakers": real_bookmakers
    })

# --- INTERFAZ WEB RESPONSIVE ---
@app.route("/")
def index():
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
      <title>BetStat Pro - Live API</title>
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
        .error-box { background: rgba(239,68,68,0.15); border: 1px solid var(--danger); color: #f87171; padding: 8px 10px; border-radius: 6px; font-size: 0.75rem; margin-top: 6px; display: none; }
      </style>
    </head>
    <body>
      <div class="app-container">
        <header>
          <h1>BETSTAT PRO</h1>
          <p>Encuentros en Vivo & Cuotas Colombia</p>
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
            <label id="matchLabel">Partidos en Vivo (Desde API)</label>
            <select id="matchSel"></select>
            <div id="apiErrorNotice" class="error-box"></div>
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
              <option value="btts_yes">Ambos Equipos Marcan (Sí)</option>
              <option value="btts_no">Ambos Equipos Marcan (No)</option>
              <option value="over15">Más de 1.5 Goles</option>
              <option value="over35">Más de 3.5 Goles</option>
            </select>
          </div>
          <button onclick="runAnalysis()">Analizar Partido Seleccionado</button>
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
          <div class="title" style="margin-top:6px;">Comparativa: Casas Colombia (Base Internacional)</div>
          <div id="bookiesList"></div>
        </div>
      </div>

      <script>
        let currentMatches = [];

        async function init() {
          // Fecha por defecto: 2026-10-31
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

          const d = new Date(2026, 9, 29); // 29 Oct 2026
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
          const errBox = document.getElementById("apiErrorNotice");
          
          errBox.style.display = "none";
          mSel.innerHTML = "<option>Consultando API en vivo...</option>";

          try {
            const res = await fetch(`/api/fixtures?league=${lKey}&date=${date}`);
            const data = await res.json();
            
            if (data.api_error) {
              errBox.style.display = "block";
              errBox.innerText = "Aviso API: " + data.api_error;
            }

            currentMatches = data.matches || [];

            if (currentMatches.length === 0) {
              mSel.innerHTML = "<option value='none'>No hay partidos registrados en la API para esta fecha</option>";
            } else {
              mSel.innerHTML = currentMatches.map((m, i) => `
                <option value="${i}">${m.time} | ${m.home} vs ${m.away} (${m.status})</option>
              `).join("");
            }
          } catch (e) {
            mSel.innerHTML = "<option value='none'>Error al conectar con el servidor</option>";
          }
        }

        async function runAnalysis() {
          const mIdx = document.getElementById("matchSel").value;
          if (mIdx === "none" || currentMatches.length === 0) {
            alert("No hay ningún partido seleccionado de la API.");
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
                  ${i === 0 ? '<span class="badge">MEJOR CUOTA</span>' : ''}
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