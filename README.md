# 🏥 NurseFlow — AI-Powered Hospital Scheduling v2.0

A professional web application powered by Groq AI to manage hospital nursing schedules — natural language modifications, real-time KPIs, regulatory compliance checks, and professional Excel exports.

---

## 🚀 Quick Start (Local)

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate          # Linux/Mac
venv\Scripts\activate             # Windows

# 2. Install dependencies
pip install -r requirements.txt
pip install python-dotenv

# 3. Configure your Groq API key
# Create a .env file at the root of the project and add:
# GROQ_API_KEY="gsk_your_api_key_here"
# GROQ_MODEL="openai/gpt-oss-120b"

# 4. Start the development server
python app.py

# 5. Open in your browser
# http://localhost:5000
```

> ⚠️ **Important**: Never commit the `.env` file to GitHub. It is already listed in `.gitignore`.

---

## ☁️ AWS EC2 Deployment (Complete Guide)

### Prerequisites
- An AWS account with a running EC2 Ubuntu instance (e.g. `t2.micro` Free Tier)
- Your `.pem` private key file downloaded from the AWS Console
- Your GitHub repository containing this project
- A free Groq API key from [console.groq.com](https://console.groq.com)

---

### Step 1 — Navigate to your .pem file (Windows PowerShell)

Open **PowerShell** on your computer and navigate to the folder where your `.pem` file is located (e.g. Downloads):

```powershell
cd C:\Users\YOUR_USERNAME\Downloads
```

---

### Step 2 — Connect to the server via SSH

```bash
ssh -i "key_pair_nursing_app.pem" ubuntu@YOUR_EC2_IP
```

When prompted with `Are you sure you want to continue connecting (yes/no)?`, type **yes** and press Enter.

> ✅ Your terminal will display `ubuntu@ip-xxx-xxx-xxx-xxx:~$` once connected.

---

### Step 3 — Install Python 3.11 and required tools

```bash
sudo apt update && sudo apt install python3.11 python3.11-venv python3-pip git nano -y
```

---

### Step 4 — Clone the GitHub repository

> If the folder already exists, delete it first with: `rm -rf nursing-schedule-ai`

```bash
git clone https://github.com/YOUR_USERNAME/nursing-schedule-ai.git
cd nursing-schedule-ai
```

---

### Step 5 — Create a virtual environment and install dependencies

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install python-dotenv
```

---

### Step 6 — Configure your Groq API key using nano

```bash
nano .env
```

In the editor that opens, paste these two lines (with your real key):

```
GROQ_API_KEY="gsk_your_real_api_key_here"
GROQ_MODEL="openai/gpt-oss-120b"
```

To save and exit nano:
- Press `Ctrl+O` then `Enter` to save
- Press `Ctrl+X` to quit

---

### Step 7 — Launch the application in the background

```bash
nohup gunicorn app:app --workers 1 --bind 0.0.0.0:5000 &
```

Press **Enter** one more time to get your cursor back.

To verify that the application started successfully:

```bash
cat nohup.out
```

> ✅ You should see `[INFO] Listening at: http://0.0.0.0:5000`

---

### Step 8 — Open port 5000 in AWS

By default, AWS blocks all ports except port 22 (SSH). You need to allow port 5000:

1. Go to **AWS Console → EC2 → Instances**
2. Click on your instance, then on the **Security** tab
3. Click on the **Security Group** link (e.g. `sg-0abc...`)
4. Click **Edit inbound rules → Add rule**
5. Configure it as follows:
   - **Type**: Custom TCP
   - **Port range**: 5000
   - **Source**: Anywhere-IPv4 (0.0.0.0/0)
6. Click **Save rules**

---

### Step 9 — Access the application

Open your browser and go to:

```
http://YOUR_EC2_IP:5000
```

🎉 Your NurseFlow application is now live!

---

### Useful server commands

```bash
# View application logs
cat nohup.out

# Stop the application
pkill gunicorn

# Restart after a change
pkill gunicorn
source venv/bin/activate
nohup gunicorn app:app --workers 1 --bind 0.0.0.0:5000 &

# Pull latest code from GitHub and restart
git pull
pkill gunicorn
nohup gunicorn app:app --workers 1 --bind 0.0.0.0:5000 &

# Stop the EC2 instance (from AWS Console)
# EC2 → Instances → Select → Instance state → Stop instance
```

> ⚠️ **Note**: Schedule data is stored in memory (non-persistent). If the server restarts, the data will be reset to default.

---

## ✨ Features v2.0

| Feature | Description |
|---|---|
| 📋 Interactive schedule | Weekly table with clickable cells |
| 🤖 Groq AI | Natural language schedule modifications |
| ⚡ 5 shift types | M (Morning), N (Night), S (Evening), R (Rest), C (Leave) |
| 📊 Real-time KPIs | Hours, nights, alerts, fairness score |
| 🔍 Automatic analysis | Regulatory violations, understaffing detection |
| 📁 Professional Excel export | Color-coded formatting + statistics |
| 👥 Staff management | Add / edit / delete nurses with color avatars |
| ↔ Week navigation | Multi-week schedule history |
| 🎨 Premium UI | Complete design system, animations, responsive |

---

## 💬 Example AI Commands

```
"Move Sophie from Monday morning to Wednesday evening"
"Swap Thomas and Hugo's shifts on Thursday"
"Who is available on Saturday night?"
"Put Karim on leave on Friday"
"Generate a fair schedule for the week"
"Check for conflicts and overtime"
"Analyze all regulatory violations"
"What is the fairness score and how can I improve it?"
"Which days are understaffed?"
```

---

## 🔑 Groq API Key

Get a free key at [console.groq.com](https://console.groq.com) → API Keys

Two ways to configure it:
1. **Via the `.env` file** (recommended for production) — the key is loaded automatically at startup.
2. **Via the web UI** — enter it directly in the field at the top of the chat panel. It is saved in the browser's localStorage.

> If both are present, the key entered in the UI takes priority.

---

## 📐 Architecture

```
nursing-schedule-ai/
├── app.py                  # Flask backend (routes, AI, analytics, Excel)
├── templates/
│   └── index.html          # Frontend (single-file HTML/CSS/JS)
├── requirements.txt
├── .env                    # API key config (do NOT commit!)
├── .gitignore
└── README.md
```

### API Endpoints

| Method | Route | Description |
|---|---|---|
| GET | `/api/planning?date=` | Fetch planning + stats |
| POST | `/api/planning` | Update planning |
| POST | `/api/infirmier` | Add a nurse |
| PUT | `/api/infirmier/<id>` | Edit a nurse |
| DELETE | `/api/infirmier/<id>` | Delete a nurse |
| POST | `/api/chat` | AI chat (Groq) |
| POST | `/api/export` | Generate Excel file |
| GET | `/api/analytics` | Advanced statistics |
| POST | `/api/reset` | Reset all data |
| GET | `/api/health` | Server health check |

---

## ⚖️ Built-in Regulatory Compliance

- **Art. L3121-20 CT** — Max 48 effective hours per week
- **Art. L3131-1 CT** — Minimum 11h rest between two shifts (Night → Morning forbidden)
- **Art. L3132-1 CT** — At least 1 rest day per 7-day period
- Alert at 3 consecutive night shifts, critical violation at 4+
- Workload fairness score from 0 to 100

---

## 🛠 Tech Stack

- **Backend**: Python 3.11 · Flask 3 · openpyxl · python-dotenv
- **AI**: Groq API · openai/gpt-oss-120b
- **Frontend**: Vanilla HTML/CSS/JS · DM Sans · DM Mono (Google Fonts)
- **Export**: Excel (.xlsx) with professional color formatting
- **Deployment**: AWS EC2 Ubuntu · Gunicorn
