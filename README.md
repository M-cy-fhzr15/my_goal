# 🎯 Mon Objectif Épargne

Application Streamlit de suivi budgétaire avec avatar animé.

## Installation

```bash
pip install -r requirements.txt
```

## Lancement

```bash
streamlit run app.py
```

L'app s'ouvre automatiquement sur http://localhost:8501

## Utilisation

1. **Configurer** dans la barre latérale :
   - Ton solde de départ
   - Ton objectif (ex: 1 200 000 Ar)
   - La date limite (ex: 31 août 2025)
   - Ton revenu fixe quotidien et le jour sans revenu

2. **Saisir chaque jour** tes revenus et dépenses

3. **Suivre** la progression avec l'avatar 🏃‍♀️ qui avance vers le drapeau 🏁

## Données

Toutes tes données sont sauvegardées localement dans `budget.db` (SQLite).
Tu peux le sauvegarder comme backup.
