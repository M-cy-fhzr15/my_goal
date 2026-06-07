# 🎯 Budget Tracker — Suivi d'objectif d'épargne

Application web de suivi budgétaire construite avec **Python** et **Streamlit**. Elle permet de définir un objectif d'épargne, de saisir ses revenus et dépenses au quotidien, et de visualiser sa progression en temps réel grâce à un avatar animé qui avance vers la ligne d'arrivée.

## Fonctionnalités

- **Objectif personnalisable** — montant cible, date limite, solde de départ
- **Revenus fixes** — revenu quotidien pré-rempli automatiquement, avec gestion d'un jour sans revenu (ex : dimanche)
- **Saisie journalière** — revenus et dépenses enregistrés par date, modifiables à tout moment
- **Avatar animé** 🏃‍♀️ — se déplace sur une route proportionnellement à la progression vers l'objectif
- **Barre de progression** — pourcentage atteint avec dégradé visuel
- **Tableau de bord** — solde actuel, montant restant, jours ouvrés restants, projection finale avec indicateur de faisabilité
- **Historique complet** — tableau de toutes les entrées + graphe d'évolution du solde cumulé
- **Stockage local** — données sauvegardées dans une base SQLite (`budget.db`) dans le même dossier que l'application

## Stack technique

- Python 3.8+
- Streamlit
- SQLite (via le module standard `sqlite3`)
- Pandas
- 
