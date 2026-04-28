# 🏥 Planning IA Infirmiers — Application Web Python

Interface web avec chat IA (Groq) pour gérer votre planning infirmier
et exporter en Excel en un clic.

## Lancement rapide

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Lancer le serveur
python app.py

# 3. Ouvrir dans le navigateur
http://localhost:5000
```

## Fonctionnalités

- Tableau de planning interactif (cliquez sur une cellule pour la modifier)
- Chat IA en langage naturel (Groq llama-3.3-70b — gratuit)
- Modifications automatiques du tableau via l'IA
- Export Excel avec mise en forme professionnelle
- Statistiques en temps réel (heures, nuits, alertes)

## Exemples de commandes IA

- "Déplace Sophie du lundi matin au mercredi soir"
- "Échange les gardes de Thomas et Hugo jeudi"
- "Qui est disponible samedi nuit ?"
- "Mets Karim en congé vendredi"
- "Génère un planning équitable pour la semaine prochaine"
- "Vérifie les conflits et heures supplémentaires"

## Clé API Groq

Gratuit sur https://console.groq.com → API Keys
Entrez-la dans le champ en haut du panneau de chat.
