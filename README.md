# 🏥 NurseFlow — Plannings Infirmiers Intelligents v2.0

Interface web professionnelle avec IA (Groq) pour gérer les plannings infirmiers hospitaliers — analyse, modifications en langage naturel, export Excel et statistiques temps réel.

---

## 🚀 Lancement rapide

```bash
# 1. Créer un environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate          # Linux/Mac
venv\Scripts\activate             # Windows

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Lancer le serveur (développement)
python app.py

# 4. Ouvrir dans le navigateur
http://localhost:5000
```

---

## 🏭 Déploiement en production

### Option A — Gunicorn (Linux/Mac)
```bash
gunicorn app:app --workers 2 --bind 0.0.0.0:5000
```

### Option B — Variables d'environnement
```bash
PORT=8080 DEBUG=false python app.py
```

### Option C — Docker
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "app:app", "--workers", "2", "--bind", "0.0.0.0:5000"]
```

---

## ✨ Fonctionnalités v2.0

| Fonctionnalité | Description |
|---|---|
| 📋 Planning interactif | Tableau semaine avec cellules cliquables |
| 🤖 IA Groq (llama-3.3-70b) | Modifications en langage naturel |
| ⚡ 5 types de gardes | M (Matin), N (Nuit), S (Soirée), R (Repos), C (Congé) |
| 📊 KPIs temps réel | Heures, nuits, alertes, score d'équité |
| 🔍 Analyse automatique | Violations réglementaires, sous-effectifs |
| 📁 Export Excel professionnel | Mise en forme couleurs + statistiques |
| 👥 Gestion agents | Ajout / modification / suppression avec avatar coloré |
| ↔ Navigation semaines | Historique multi-semaines |
| 🎨 UI premium | Design system complet, animations, responsive |

---

## 💬 Exemples de commandes IA

```
"Déplace Sophie du lundi matin au mercredi soir"
"Échange les gardes de Thomas et Hugo jeudi"
"Qui est disponible samedi nuit ?"
"Mets Karim en congé vendredi"
"Génère un planning équitable pour la semaine"
"Vérifie les conflits et heures supplémentaires"
"Analyse tous les problèmes réglementaires"
"Quel est le score d'équité et comment l'améliorer ?"
"Quels jours sont en sous-effectif ?"
```

---

## 🔑 Clé API Groq

Gratuite sur [console.groq.com](https://console.groq.com) → API Keys

Entrez-la dans le champ en haut du panneau de chat. Elle est sauvegardée dans localStorage.

---

## 📐 Architecture

```
nurseflow/
├── app.py                  # Backend Flask (routes, IA, analytics, Excel)
├── templates/
│   └── index.html          # Frontend (HTML/CSS/JS tout-en-un)
├── requirements.txt
└── README.md
```

### Endpoints API

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/planning?date=` | Récupère le planning + stats |
| POST | `/api/planning` | Met à jour le planning |
| POST | `/api/infirmier` | Ajoute un infirmier |
| PUT | `/api/infirmier/<id>` | Modifie un infirmier |
| DELETE | `/api/infirmier/<id>` | Supprime un infirmier |
| POST | `/api/chat` | Chat IA (Groq) |
| POST | `/api/export` | Génère le fichier Excel |
| GET | `/api/analytics` | Statistiques avancées |
| POST | `/api/reset` | Réinitialise les données |
| GET | `/api/health` | Vérification de l'état du serveur |

---

## ⚖️ Référentiel réglementaire intégré

- **Art. L3121-20 CT** — Max 48h effectives/semaine
- **Art. L3131-1 CT** — Repos minimum 11h entre deux prises de poste (N→M interdit)
- **Art. L3132-1 CT** — Au moins 1 jour de repos par période de 7 jours
- Alerte 3 nuits consécutives, violation grave à 4+
- Score d'équité de charge 0–100

---

## 🛠 Stack technique

- **Backend** : Python 3.12 · Flask 3 · openpyxl
- **IA** : Groq API · llama-3.3-70b-versatile
- **Frontend** : HTML/CSS/JS vanilla · DM Sans · DM Mono (Google Fonts)
- **Export** : Excel (.xlsx) avec mise en forme couleurs professionnelle
