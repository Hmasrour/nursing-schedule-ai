"""
NurseFlow — Gestion intelligente des plannings infirmiers
Production-ready Flask backend with enhanced AI prompting & analytics
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import requests, json, io, datetime, re, os, logging

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── App setup ───────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nurseflow")

# ── Constants ────────────────────────────────────────────────────────────
MOIS_FR  = ["Janvier","Février","Mars","Avril","Mai","Juin",
            "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
JOURS_FR = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]
JOURS_FULL = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]

SHIFT_CODES = {"M", "N", "R", "C", "S"}   # S = Soirée (added shift type)
SHIFT_H = {"M": 10, "N": 10, "S": 8, "R": 0, "C": 0}
SHIFT_LABELS = {"M": "Matin 8h–20h", "N": "Nuit 20h–8h", "S": "Soirée 14h–22h",
                "R": "Repos", "C": "Congé"}

GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

# ── Date helpers ─────────────────────────────────────────────────────────
def get_monday(d=None):
    d = d or datetime.date.today()
    return d - datetime.timedelta(days=d.weekday())

def fmt_week(start):
    label = f"{start.day} {MOIS_FR[start.month-1]} {start.year}"
    days  = [f"{JOURS_FR[(start+datetime.timedelta(i)).weekday()]} "
             f"{(start+datetime.timedelta(i)).day}/{(start+datetime.timedelta(i)).month}"
             for i in range(7)]
    return label, days

def parse_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return datetime.date.today()

# ── Initial staff data ───────────────────────────────────────────────────
INITIAL_STAFF = [
    {"id":1, "nom":"Sophie Martin",    "service":"Urgences",      "couleur":"#3B82F6",
     "gardes":["M","M","N","R","N","N","R"]},
    {"id":2, "nom":"Thomas Laurent",   "service":"Chirurgie",     "couleur":"#8B5CF6",
     "gardes":["N","M","M","N","R","R","M"]},
    {"id":3, "nom":"Léa Rousseau",     "service":"Bloc Op.",      "couleur":"#10B981",
     "gardes":["N","R","M","M","N","M","R"]},
    {"id":4, "nom":"Karim Benali",     "service":"Pédiatrie",     "couleur":"#F59E0B",
     "gardes":["R","N","N","M","M","R","N"]},
    {"id":5, "nom":"Marie Chevalier",  "service":"Coordination",  "couleur":"#EC4899",
     "gardes":["M","M","M","M","M","R","R"]},
    {"id":6, "nom":"Hugo Petit",       "service":"Urgences",      "couleur":"#06B6D4",
     "gardes":["N","N","R","N","N","M","M"]},
    {"id":7, "nom":"Amina Saidani",    "service":"Pédiatrie",     "couleur":"#84CC16",
     "gardes":["M","R","N","N","R","N","N"]},
    {"id":8, "nom":"Paul Durand",      "service":"Chirurgie",     "couleur":"#F97316",
     "gardes":["N","N","M","R","N","N","R"]},
]

planning_db = {}
STAFF_LIST  = json.loads(json.dumps(INITIAL_STAFF))

# ── State management ─────────────────────────────────────────────────────
def get_state(date_str=None):
    if not date_str:
        start    = get_monday()
        date_str = start.isoformat()
    else:
        start    = get_monday(parse_date(date_str))
        date_str = start.isoformat()

    if date_str not in planning_db:
        label, days = fmt_week(start)
        if not planning_db:
            staff = json.loads(json.dumps(STAFF_LIST))
        else:
            staff = [{"id": s["id"], "nom": s["nom"], "service": s["service"],
                      "couleur": s.get("couleur", "#64748B"), "gardes": ["R"]*7}
                     for s in STAFF_LIST]
        planning_db[date_str] = {"semaine": label, "jours": days, "infirmiers": staff,
                                 "notes": {}, "created_at": datetime.datetime.now().isoformat()}

    return planning_db[date_str], date_str

# ── Analytics ─────────────────────────────────────────────────────────────
def calculer_stats(gardes):
    heures = sum(SHIFT_H.get(g, 0) for g in gardes)
    nuits  = gardes.count("N")
    matins = gardes.count("M")
    repos  = gardes.count("R") + gardes.count("C")

    # Consecutive nights streak
    max_consec_nuits = streak = 0
    for g in gardes:
        streak = streak + 1 if g == "N" else 0
        max_consec_nuits = max(max_consec_nuits, streak)

    # Consecutive working days
    max_consec_work = w_streak = 0
    for g in gardes:
        w_streak = w_streak + 1 if g not in ("R","C") else 0
        max_consec_work = max(max_consec_work, w_streak)

    # Rest violations
    repos_violation = any(gardes[i] == "N" and gardes[i+1] == "M"
                          for i in range(len(gardes)-1))
    nuit_jour_double = any(gardes[i] in ("N","M") and gardes[i+1] in ("N","M")
                           and gardes[i] != gardes[i+1]
                           for i in range(len(gardes)-1))

    alertes = []
    if heures > 48:              alertes.append("⚠ Dépassement 48h/semaine")
    if heures > 40:              alertes.append("⚡ Heures supp. (>40h)")
    if max_consec_nuits >= 3:    alertes.append("🌙 3+ nuits consécutives")
    if repos_violation:          alertes.append("🚨 Repos insuffisant (N→M)")
    if max_consec_work >= 6:     alertes.append("⚠ 6+ jours sans repos")
    if repos == 0:               alertes.append("❌ Aucun repos cette semaine")

    # Remove "heures supp" if already flagged for 48h
    if "⚠ Dépassement 48h/semaine" in alertes and "⚡ Heures supp. (>40h)" in alertes:
        alertes.remove("⚡ Heures supp. (>40h)")

    return {
        "heures": heures, "nuits": nuits, "matins": matins,
        "repos": repos, "max_consec_nuits": max_consec_nuits,
        "max_consec_work": max_consec_work, "alertes": alertes,
        "score_charge": round((heures / 50) * 100)  # 0–100 load score
    }

def coverage_analysis(state):
    cov = []
    for di in range(7):
        gardes = [inf["gardes"][di] for inf in state["infirmiers"]]
        m = gardes.count("M"); n = gardes.count("N"); s = gardes.count("S")
        cov.append({
            "M": m, "N": n, "S": s, "total": m + n + s,
            "ok": m >= 1 and n >= 1,
            "critique": m == 0 or n == 0
        })
    return cov

def equity_score(state):
    """Compute fairness score 0–100 (100 = perfectly equal hours)"""
    hours = [calculer_stats(inf["gardes"])["heures"] for inf in state["infirmiers"]]
    if not hours or max(hours) == 0:
        return 100, 0, 0
    ecart = max(hours) - min(hours)
    score = max(0, 100 - (ecart * 2))
    return score, min(hours), max(hours)

def planning_to_text(state):
    """Detailed text representation for AI context"""
    txt  = f"═══ PLANNING — SEMAINE DU {state['semaine']} ═══\n\n"
    txt += "AFFECTATIONS DES AGENTS :\n"
    for inf in state["infirmiers"]:
        gardes_str = "  ".join(
            f"{JOURS_FR[i]}={g}" for i, g in enumerate(inf["gardes"])
        )
        stats = calculer_stats(inf["gardes"])
        alertes_str = (" | ".join(stats["alertes"])) if stats["alertes"] else "OK"
        txt += (f"  • {inf['nom']} [{inf['service']}] : {gardes_str} "
                f"→ {stats['heures']}h | Nuits:{stats['nuits']} | {alertes_str}\n")

    txt += "\nCOUVERTURE JOURNALIÈRE :\n"
    cov = coverage_analysis(state)
    for j, c in zip(state["jours"], cov):
        status = "✅ OK" if c["ok"] else "❌ CRITIQUE"
        txt += f"  {j}: {c['M']} Matin / {c['N']} Nuit / {c['S']} Soirée  {status}\n"

    txt += "\nÉQUITÉ DE CHARGE :\n"
    eq_score, mn, mx = equity_score(state)
    txt += f"  Score équité : {eq_score}/100  |  Min:{mn}h  Max:{mx}h  Écart:{mx-mn}h\n"

    # Identify violations
    violations = []
    for inf in state["infirmiers"]:
        stats = calculer_stats(inf["gardes"])
        for al in stats["alertes"]:
            violations.append(f"  ⚑ {inf['nom']} : {al}")
    if violations:
        txt += "\nVIOLATIONS RÉGLEMENTAIRES DÉTECTÉES :\n" + "\n".join(violations) + "\n"
    else:
        txt += "\n✅ Aucune violation réglementaire détectée.\n"

    return txt

# ── System Prompt ─────────────────────────────────────────────────────────
def build_system_prompt(state):
    planning_txt = planning_to_text(state)
    eq_score, mn, mx = equity_score(state)
    cov = coverage_analysis(state)
    jours_critiques = [state["jours"][i] for i, c in enumerate(cov) if not c["ok"]]

    return f"""Tu es **NurseFlow AI** — un assistant expert en gestion des plannings hospitaliers, spécialisé en droit du travail français et en optimisation des ressources humaines soignantes. Tu as un accès complet au planning en temps réel et peux le modifier directement.

{planning_txt}

══════════════════════════════════════════════════
RÉFÉRENTIEL RÉGLEMENTAIRE — SECTEUR HOSPITALIER (Droit français)
══════════════════════════════════════════════════

CODES DE GARDE :
  M = Matin   8h00→20h00  | 10h effectives | Pauses : 10h-11h, 17h-18h
  N = Nuit   20h00→08h00  | 10h effectives | Pauses : 23h-00h, 04h-05h
  S = Soirée 14h00→22h00  |  8h effectives | Pause  : 18h-18h30
  R = Repos  (Journée non travaillée)
  C = Congé  (Annuel, RTT, événementiel)

RÈGLES IMPÉRATIVES (par ordre de priorité) :
  🔴 CRITIQUE  — Repos minimum 11h entre deux prises de poste (Art. L3131-1 CT)
               → Enchaînement N→M le lendemain = VIOLATION GRAVE
  🔴 CRITIQUE  — Maximum 48h de travail effectif par semaine (Art. L3121-20 CT)
  🟠 ALERTE    — Maximum 2 nuits consécutives recommandé ; 3 = alerte ; 4+ = violation
  🟠 ALERTE    — Au moins 1 jour de repos par période de 7 jours (Art. L3132-1 CT)
  🟡 VIGILANCE — Équité de charge : écart max/min < 10h recommandé
  🟡 VIGILANCE — Couverture minimale : ≥1 agent M ET ≥1 agent N chaque jour

ÉTAT ACTUEL DU PLANNING :
  • Score d'équité   : {eq_score}/100
  • Charge min/max   : {mn}h / {mx}h (écart : {mx-mn}h)
  • Jours critiques  : {', '.join(jours_critiques) if jours_critiques else 'Aucun ✅'}

══════════════════════════════════════════════════
MÉTHODE D'ANALYSE ET RÔLE
══════════════════════════════════════════════════

À chaque interaction, applique cette méthode structurée :

ÉTAPE 1 — DIAGNOSTIC RAPIDE (2-3 lignes max)
  • Identifier le problème principal avec son niveau de criticité
  • Quantifier l'impact (ex: "Sophie dépasse 48h de 10h")
  • Signaler si d'autres violations découlent de la modification demandée

ÉTAPE 2 — PROPOSITION OPTIMALE
  • Proposer la solution qui résout le problème SANS en créer d'autres
  • Si plusieurs options : présenter la MEILLEURE et expliquer brièvement pourquoi
  • Mentionner l'impact sur l'équité de charge si significatif (>5h de delta)
  • Vérifier que la couverture journalière est maintenue

ÉTAPE 3 — EXÉCUTION PRÉCISE
  • Générer le JSON d'actions avec des indices de jours corrects
  • Vérifier chaque action avant de l'inclure

══════════════════════════════════════════════════
FORMAT DE RÉPONSE STRICT
══════════════════════════════════════════════════

Pour toute modification du planning, réponds UNIQUEMENT avec ce format :

[1-3 lignes de diagnostic ou confirmation]

```json
[
  {{"action": "set",  "infirmier": "Prénom Nom", "jour_index": 0-6, "garde": "M|N|S|R|C"}},
  {{"action": "move", "infirmier": "Prénom Nom", "de": 0-6, "vers": 0-6}},
  {{"action": "swap", "infirmier1": "Nom1", "infirmier2": "Nom2", "jour_index": 0-6}}
]
```

MAPPING jour_index :
  0=Lundi · 1=Mardi · 2=Mercredi · 3=Jeudi · 4=Vendredi · 5=Samedi · 6=Dimanche

RÈGLES JSON :
  - Utiliser les prénoms et noms EXACTS comme dans le planning
  - Pour les questions d'analyse sans modification → répondre directement, SANS bloc JSON
  - Pour une génération de planning → créer autant d'actions "set" que nécessaire
  - Ne JAMAIS créer d'actions qui violent les règles impératives

LANGUE : Français. TON : Expert, professionnel, orienté solutions. Concis."""

# ── Routes ────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/planning", methods=["GET"])
def get_planning():
    state, date_str = get_state(request.args.get("date"))
    cov  = coverage_analysis(state)
    eq_s, mn, mx = equity_score(state)
    data = []
    for inf in state["infirmiers"]:
        s = calculer_stats(inf["gardes"])
        data.append({**inf, **s})
    return jsonify({
        "jours": state["jours"], "semaine": state["semaine"],
        "infirmiers": data, "date": date_str, "coverage": cov,
        "equity": {"score": eq_s, "min": mn, "max": mx}
    })

@app.route("/api/planning", methods=["POST"])
def update_planning():
    body = request.json
    state, date_str = get_state(body.get("date"))
    state["infirmiers"] = body["infirmiers"]
    if "semaine" in body:
        state["semaine"] = body["semaine"]
    return jsonify({"ok": True, "date": date_str})

@app.route("/api/infirmier", methods=["POST"])
def add_infirmier():
    body   = request.json
    new_id = max((i["id"] for i in STAFF_LIST), default=0) + 1
    colors = ["#3B82F6","#8B5CF6","#10B981","#F59E0B","#EC4899","#06B6D4","#84CC16","#F97316"]
    entry  = {
        "id": new_id, "nom": body.get("nom", "Nouveau"),
        "service": body.get("service", "Général"),
        "couleur": colors[new_id % len(colors)],
        "gardes": ["R"] * 7
    }
    STAFF_LIST.append(entry)
    for state in planning_db.values():
        state["infirmiers"].append(json.loads(json.dumps(entry)))
    return jsonify({"ok": True, "id": new_id})

@app.route("/api/infirmier/<int:inf_id>", methods=["PUT", "DELETE"])
def edit_delete_infirmier(inf_id):
    global STAFF_LIST
    if request.method == "DELETE":
        STAFF_LIST = [i for i in STAFF_LIST if i["id"] != inf_id]
        for state in planning_db.values():
            state["infirmiers"] = [i for i in state["infirmiers"] if i["id"] != inf_id]
        return jsonify({"ok": True})
    body = request.json
    for lst in [STAFF_LIST] + [s["infirmiers"] for s in planning_db.values()]:
        for inf in lst:
            if inf["id"] == inf_id:
                if "nom"     in body: inf["nom"]     = body["nom"]
                if "service" in body: inf["service"] = body["service"]
                if "couleur" in body: inf["couleur"] = body["couleur"]
    return jsonify({"ok": True})

@app.route("/api/analytics", methods=["GET"])
def analytics():
    date_str   = request.args.get("date")
    state, actual = get_state(date_str)
    cov        = coverage_analysis(state)
    eq_s, mn, mx = equity_score(state)
    uncovered  = [state["jours"][i] for i, c in enumerate(cov) if not c["ok"]]

    agent_stats = []
    for inf in state["infirmiers"]:
        s = calculer_stats(inf["gardes"])
        agent_stats.append({
            "nom": inf["nom"], "service": inf["service"],
            "couleur": inf.get("couleur", "#64748B"), **s
        })
    agent_stats.sort(key=lambda x: x["heures"], reverse=True)

    return jsonify({
        "date": actual, "coverage": cov,
        "uncovered_days": uncovered, "agents": agent_stats,
        "equity": {"score": eq_s, "min": mn, "max": mx}
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    body       = request.json
    message    = body.get("message", "").strip()
    api_key    = body.get("api_key", "").strip()
    historique = body.get("historique", [])
    date_str   = body.get("date")

    if not message:
        return jsonify({"erreur": "Message vide"}), 400
    if not api_key:
        return jsonify({"erreur": "Clé API manquante. Renseignez votre clé Groq."}), 400

    state, actual = get_state(date_str)
    system_prompt = build_system_prompt(state)

    messages = [{"role": "system", "content": system_prompt}]
    for h in historique[-10:]:   # Keep last 10 turns for context
        messages.append(h)
    messages.append({"role": "user", "content": message})

    try:
        resp = requests.post(
            GROQ_ENDPOINT,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "max_tokens": 1500,
                "temperature": 0.1,       # Very deterministic for schedule management
                "top_p": 0.9,
            },
            timeout=30
        )

        if resp.status_code == 401:
            return jsonify({"erreur": "Clé API invalide ou expirée."}), 401
        if resp.status_code == 429:
            return jsonify({"erreur": "Limite de débit Groq atteinte. Patientez quelques secondes."}), 429
        resp.raise_for_status()

        contenu = resp.json()["choices"][0]["message"]["content"]
        actions = []
        m = re.search(r'```json\s*([\s\S]*?)\s*```', contenu)
        if m:
            try:
                actions = json.loads(m.group(1))
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error in AI response: {e}")

        texte         = re.sub(r'```json[\s\S]*?```', '', contenu).strip()
        modifications = [r for act in actions if (r := appliquer_action(act, state))]

        usage = resp.json().get("usage", {})
        logger.info(f"Chat — tokens: {usage.get('total_tokens','?')} | "
                    f"actions: {len(actions)} | mods: {len(modifications)}")

        return jsonify({
            "texte": texte, "actions": actions,
            "modifications": modifications, "date": actual,
            "tokens_used": usage.get("total_tokens", 0)
        })

    except requests.exceptions.Timeout:
        return jsonify({"erreur": "Délai d'attente dépassé. Réessayez."}), 504
    except requests.exceptions.ConnectionError:
        return jsonify({"erreur": "Impossible de joindre l'API Groq. Vérifiez votre connexion."}), 503
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({"erreur": f"Erreur inattendue : {str(e)}"}), 500

def appliquer_action(act, state):
    action     = act.get("action", "")
    infirmiers = state["infirmiers"]

    def find(nom):
        if not nom:
            return None
        nl = nom.lower().strip()
        # Exact match first
        for i in infirmiers:
            if i["nom"].lower() == nl:
                return i
        # Partial match (last name or first name)
        for i in infirmiers:
            parts = i["nom"].lower().split()
            if nl in parts or any(nl in p for p in parts):
                return i
        # Contains match
        for i in infirmiers:
            if nl in i["nom"].lower():
                return i
        return None

    if action == "set":
        inf = find(act.get("infirmier", ""))
        idx = act.get("jour_index")
        g   = act.get("garde", "").upper()
        if inf and idx is not None and 0 <= idx <= 6 and g in SHIFT_CODES:
            old = inf["gardes"][idx]
            inf["gardes"][idx] = g
            return f"{inf['nom']} — {state['jours'][idx]} : {old} → {g}"

    elif action == "move":
        inf = find(act.get("infirmier", ""))
        src, dst = act.get("de"), act.get("vers")
        if inf and src is not None and dst is not None and 0 <= src <= 6 and 0 <= dst <= 6:
            v = inf["gardes"][src]
            inf["gardes"][dst] = v
            inf["gardes"][src] = "R"
            return f"{inf['nom']} — {state['jours'][src]} → {state['jours'][dst]} ({v})"

    elif action == "swap":
        i1  = find(act.get("infirmier1", ""))
        i2  = find(act.get("infirmier2", ""))
        idx = act.get("jour_index")
        if i1 and i2 and idx is not None and 0 <= idx <= 6:
            i1["gardes"][idx], i2["gardes"][idx] = i2["gardes"][idx], i1["gardes"][idx]
            return f"Échange {i1['nom']} ↔ {i2['nom']} — {state['jours'][idx]}"

    return None

# ── Excel Export ──────────────────────────────────────────────────────────
@app.route("/api/export", methods=["POST"])
def export_excel():
    body     = request.json or {}
    date_str = body.get("date")
    state, actual = get_state(date_str)
    start_dt = parse_date(actual)
    titre    = f"Planning — Semaine du {state['semaine']}"

    wb = Workbook()
    ws = wb.active
    ws.title = "Planning Infirmiers"
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "D6"

    # ── Color palette ──
    C = {
        "navy":   "0F172A", "navy_m":  "1E3A5F", "navy_l":  "EFF6FF",
        "blue":   "1D4ED8", "blue_l":  "DBEAFE",
        "night":  "0F172A", "night_l": "CBD5E1",
        "amber":  "92400E", "amber_l": "FEF3C7",
        "red":    "991B1B", "red_l":   "FEE2E2",
        "green":  "14532D", "green_l": "DCFCE7",
        "gray":   "1E293B", "gray_m":  "475569", "gray_l":  "F8FAFC",
        "white":  "FFFFFF", "bg":      "F1F5F9",
        "soiree": "4C1D95", "soiree_l":"EDE9FE",
    }

    def fl(h):    return PatternFill("solid", fgColor=h)
    def ft(h, bold=False, sz=10): return Font(name="Calibri", color=h, bold=bold, size=sz)
    def ctr():    return Alignment(horizontal="center", vertical="center", wrap_text=True)
    def lft():    return Alignment(horizontal="left",   vertical="center", wrap_text=True)
    def brd():
        s = Side(style="thin", color="E2E8F0")
        return Border(left=s, right=s, top=s, bottom=s)
    def brd_bold():
        s = Side(style="medium", color="CBD5E1")
        return Border(left=s, right=s, top=s, bottom=s)

    SHIFT_STYLE = {
        "M": (C["blue_l"],   C["blue"]),
        "N": (C["night"],    C["night_l"]),
        "S": (C["soiree_l"], C["soiree"]),
        "R": (C["navy_l"],   C["navy_m"]),
        "C": (C["amber_l"],  C["amber"]),
    }
    MAX_COL = 14
    TOTAL_ROWS = 6 + len(state["infirmiers"]) + 4

    # Background
    for r in ws.iter_rows(1, TOTAL_ROWS, 1, MAX_COL):
        for c in r:
            c.fill = fl(C["bg"])

    # Row 1 — Title
    ws.merge_cells(f"A1:{get_column_letter(MAX_COL)}1")
    ws["A1"] = f"🏥  {titre}"
    ws["A1"].font = Font(name="Calibri", color=C["white"], bold=True, size=15)
    ws["A1"].fill = fl(C["navy"])
    ws["A1"].alignment = ctr()
    ws.row_dimensions[1].height = 38

    # Row 2 — Subtitle
    ws.merge_cells(f"A2:{get_column_letter(MAX_COL)}2")
    generated = datetime.datetime.now().strftime("%d/%m/%Y à %H:%M")
    ws["A2"] = f"Généré le {generated}  ·  Shifts 10h (M/N)  ·  8h (Soirée)  ·  NurseFlow Planning System"
    ws["A2"].font = Font(name="Calibri", color=C["gray_m"], size=8, italic=True)
    ws["A2"].fill = fl(C["navy_l"])
    ws["A2"].alignment = ctr()
    ws.row_dimensions[2].height = 15

    # Row 3 — blank separator
    ws.row_dimensions[3].height = 6

    # Row 4 — Legend
    legends = [("M","Matin 8h–20h",C["blue_l"],C["blue"]),
               ("N","Nuit 20h–8h",C["night"],C["night_l"]),
               ("S","Soirée 14h–22h",C["soiree_l"],C["soiree"]),
               ("R","Repos",C["navy_l"],C["navy_m"]),
               ("C","Congé",C["amber_l"],C["amber"])]
    ws.merge_cells("A4:C4")
    ws["A4"] = "LÉGENDE DES CODES"
    ws["A4"].font = ft(C["gray_m"], True, 8)
    ws["A4"].fill = fl(C["bg"])
    ws["A4"].alignment = lft()
    for i, (code, label, bg, fg) in enumerate(legends, 4):
        c = ws.cell(4, i, f"  {code} = {label}")
        c.fill = fl(bg); c.font = ft(fg, True, 8); c.alignment = ctr()
    ws.row_dimensions[4].height = 14

    # Row 5 — blank
    ws.row_dimensions[5].height = 6

    # Row 6 — Headers
    hdrs  = ["#", "Infirmier / Agent", "Service"] + state["jours"] + ["Total H", "Nuits", "Score", "Alertes"]
    wcols = [4, 22, 13] + [10]*7 + [9, 7, 8, 28]
    for i, (h, w) in enumerate(zip(hdrs, wcols), 1):
        c = ws.cell(6, i, h)
        c.fill = fl(C["navy_m"]); c.font = ft(C["white"], True, 9)
        c.alignment = ctr(); c.border = brd()
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[6].height = 28

    cov = coverage_analysis(state)
    for idx, inf in enumerate(state["infirmiers"]):
        row = 7 + idx
        ws.row_dimensions[row].height = 28
        rb  = C["white"] if idx % 2 == 0 else C["gray_l"]

        # # cell
        c1 = ws.cell(row, 1, idx+1); c1.fill=fl(rb)
        c1.font=ft(C["gray_m"],sz=9); c1.alignment=ctr(); c1.border=brd()

        # Name cell
        c2 = ws.cell(row, 2, inf["nom"]); c2.fill=fl(rb)
        c2.font=ft(C["gray"],True,10); c2.alignment=lft(); c2.border=brd()

        # Service
        c3 = ws.cell(row, 3, inf["service"]); c3.fill=fl(rb)
        c3.font=ft(C["gray_m"],sz=9); c3.alignment=ctr(); c3.border=brd()

        # Shift cells
        for d, g in enumerate(inf["gardes"]):
            bg, fg = SHIFT_STYLE.get(g, (rb, C["gray"]))
            c = ws.cell(row, 4+d, g)
            c.fill=fl(bg); c.font=ft(fg,True,11); c.alignment=ctr(); c.border=brd()

        stats = calculer_stats(inf["gardes"])
        h, n  = stats["heures"], stats["nuits"]

        # Total hours
        hbg = C["red_l"] if h > 48 else (C["green_l"] if h >= 30 else C["amber_l"])
        hfg = C["red"]   if h > 48 else (C["green"]   if h >= 30 else C["amber"])
        ch = ws.cell(row, 11, f"{h}h"); ch.fill=fl(hbg); ch.font=ft(hfg,True)
        ch.alignment=ctr(); ch.border=brd()

        # Nights
        nbg = C["amber_l"] if n >= 3 else C["bg"]
        nfg = C["amber"]   if n >= 3 else C["gray_m"]
        cn = ws.cell(row, 12, n); cn.fill=fl(nbg); cn.font=ft(nfg,True)
        cn.alignment=ctr(); cn.border=brd()

        # Load score
        sc  = stats["score_charge"]
        scbg = C["red_l"] if sc > 90 else (C["green_l"] if sc > 50 else C["amber_l"])
        scfg = C["red"]   if sc > 90 else (C["green"]   if sc > 50 else C["amber"])
        cs = ws.cell(row, 13, f"{sc}%"); cs.fill=fl(scbg); cs.font=ft(scfg,True,9)
        cs.alignment=ctr(); cs.border=brd()

        # Alerts
        al_txt = " | ".join(stats["alertes"])
        abg = C["red_l"] if al_txt else rb
        afg = C["red"]   if al_txt else C["gray_m"]
        ca  = ws.cell(row, 14, al_txt); ca.fill=fl(abg)
        ca.font=ft(afg,sz=8); ca.alignment=lft(); ca.border=brd()

    # Coverage row
    cr = 7 + len(state["infirmiers"])
    ws.row_dimensions[cr].height = 22
    ws.merge_cells(f"A{cr}:C{cr}")
    ws[f"A{cr}"] = "COUVERTURE JOURNALIÈRE"
    ws[f"A{cr}"].fill=fl(C["navy"]); ws[f"A{cr}"].font=ft(C["white"],True,8)
    ws[f"A{cr}"].alignment=ctr()
    for d, c in enumerate(cov):
        cell = ws.cell(cr, 4+d, f"M:{c['M']} N:{c['N']}")
        bg   = C["green_l"] if c["ok"] else C["red_l"]
        fg   = C["green"]   if c["ok"] else C["red"]
        cell.fill=fl(bg); cell.font=ft(fg,True,8); cell.alignment=ctr(); cell.border=brd()

    # Equity row
    er = cr + 1
    eq_s, mn, mx = equity_score(state)
    ws.row_dimensions[er].height = 18
    ws.merge_cells(f"A{er}:{get_column_letter(MAX_COL)}{er}")
    ws[f"A{er}"] = (f"Score d'équité : {eq_s}/100  ·  Charge min : {mn}h  ·  "
                    f"Charge max : {mx}h  ·  Écart : {mx-mn}h")
    ebg = C["green_l"] if eq_s >= 80 else (C["amber_l"] if eq_s >= 60 else C["red_l"])
    efg = C["green"]   if eq_s >= 80 else (C["amber"]   if eq_s >= 60 else C["red"])
    ws[f"A{er}"].fill=fl(ebg); ws[f"A{er}"].font=ft(efg,sz=8)
    ws[f"A{er}"].alignment=ctr()

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"planning_infirmiers_{actual}.xlsx"
    return send_file(buf, as_attachment=True, download_name=fn,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route("/api/reset", methods=["POST"])
def reset():
    global planning_db, STAFF_LIST
    planning_db = {}
    STAFF_LIST  = json.loads(json.dumps(INITIAL_STAFF))
    logger.info("Planning reset to initial state")
    return jsonify({"ok": True})

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "version": "2.0.0",
        "weeks_stored": len(planning_db),
        "staff_count": len(STAFF_LIST),
        "timestamp": datetime.datetime.now().isoformat()
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "true").lower() == "true"
    logger.info(f"🏥 NurseFlow starting on port {port} (debug={debug})")
    app.run(debug=debug, port=port, host="0.0.0.0")
