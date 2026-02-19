# ✨ JobRadar France — AI Job Matching Agent

Agent conversationnel qui trouve les meilleures offres Data/BI en France et les match automatiquement avec un CV.

---

# 🎯 Problème métier

Chercher un job Data aujourd’hui est inefficace :

- Trop d’offres non pertinentes
- Offres US/remote inutiles
- Difficulté à savoir si son CV correspond vraiment
- Impossible d’expliquer pourquoi une offre est recommandée

👉 JobRadar France automatise tout ce processus.

L’utilisateur écrit simplement :
"Stage data analyst à Paris"

Et l’agent :
1. Comprend la demande
2. Cherche les offres
3. Analyse le CV
4. Match CV ↔ offres
5. Explique les résultats

---

# 🧠 Architecture globale

Utilisateur  
↓  
Streamlit UI (chat agent)  
↓  
MCP Client (JSON-RPC)  
↓  
MCP Server  
├── Connecteurs APIs (Adzuna / Remotive)  
├── Normalisation des offres  
├── Extraction compétences CV  
├── Extraction compétences Jobs  
├── Construction graphe skills  
├── Ranking IA  
└── Explicabilité du match  

---

# 🔎 Pipeline technique détaillé

## 1️⃣ Compréhension de la demande (NLP simple)

Exemple :
"Stage data analyst à Paris"

Extraction automatique :

| Élément | Détection |
|---|---|
| Rôle | Data Analyst |
| Contrat | Stage |
| Lieu | Paris |

Cette étape sert à piloter toute la suite du pipeline.

---

## 2️⃣ Recherche d’offres via APIs

Sources actuelles :

- Adzuna API
- Remotive API

Requête envoyée :

jobs_list(query="data analyst", location="Paris")

⚠️ Important :
La query reste centrée sur le rôle pour maximiser le nombre d’offres.
Les filtres contrat/pays sont appliqués après.

---

## 3️⃣ Filtrage France ��🇷

Problème réel :
Les APIs retournent souvent des jobs US même avec "Paris".

Solution :
Filtre géographique dur basé sur la localisation enrichie.

Exemple :
51 offres API → 50 offres France.

---

## 4️⃣ Filtrage contrat intelligent

Règles métier :

Si l’utilisateur demande :
- Stage → garder uniquement les titres contenant stage/intern
- Alternance → garder uniquement alternance/apprentice
- Rien → exclure stage/alternance

Ce filtrage se fait sur le TITRE pour éviter les faux positifs.

---

## 5️⃣ Extraction des compétences

### CV
Extraction automatique des compétences techniques uniquement :
Python, SQL, Docker, Airflow, Power BI…

### Jobs
Même extraction sur :
- titre
- description
- entreprise
- localisation

---

## 6️⃣ Construction du graphe de matching

On construit un graphe :

CV skills ↔ Job skills

Chaque skill partagée crée une relation.
Ce graphe permet un scoring explicable.

---

## 7️⃣ Ranking hybride IA + heuristique

Score final =

Score graphe + Bonus pertinence

Bonus si :
- rôle correspond
- contrat correspond
- overlap compétences élevé

Fallback ranking si graphe faible.

---

## 8️⃣ Explicabilité

Chaque recommandation affiche :

Skills matchées  
Skills manquantes  
Pourquoi cette offre est recommandée  

👉 L’utilisateur comprend la recommandation.

---

# 🚀 Installation locale

## 1. Cloner
git clone https://github.com/WalterWhite75/jobradar-france.git  
cd jobradar-france  

## 2. Installer serveur MCP
cd server  
python -m venv .venv  
source .venv/bin/activate  
pip install -r requirements.txt  

## 3. Lancer serveur
python -m server.mcp_server  

## 4. Lancer UI
cd ../ui  
pip install -r requirements.txt  
streamlit run app.py  

---

# 💬 Exemples de requêtes

Stage data analyst à Paris  
Alternance data engineer à Lyon  
CDI data scientist remote  
CDD business analyst à Lyon  

---

# 🧩 Stack technique

Backend : Python MCP Server  
Frontend : Streamlit  
Matching : Graph based ranking  
Data sources : Job APIs  
Architecture : JSON-RPC / MCP  

---

# 👨‍💻 Auteur
Mevlüt Cakin — M2 Big Data & BI  
GitHub : WalterWhite75

