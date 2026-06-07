import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, timedelta
import json
import os
import hashlib

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mon Objectif Épargne",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "budget.db")

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_conn()
    c = conn.cursor()
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT UNIQUE NOT NULL,
            password  TEXT NOT NULL
        )
    """)
    # Config per user
    c.execute("""
        CREATE TABLE IF NOT EXISTS config (
            user_id INTEGER NOT NULL,
            key     TEXT    NOT NULL,
            value   TEXT,
            PRIMARY KEY (user_id, key)
        )
    """)
    # Entries per user
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_entries (
            user_id    INTEGER NOT NULL,
            entry_date TEXT    NOT NULL,
            income     REAL    DEFAULT 0,
            expenses   REAL    DEFAULT 0,
            note       TEXT    DEFAULT '',
            PRIMARY KEY (user_id, entry_date)
        )
    """)
    conn.commit()
    conn.close()

# ── Auth helpers ──────────────────────────────────────────────────────────────
def register_user(username: str, password: str) -> tuple[bool, str]:
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?,?)",
                  (username.strip(), hash_pw(password)))
        conn.commit()
        conn.close()
        return True, "Compte créé avec succès !"
    except sqlite3.IntegrityError:
        return False, "Ce nom d'utilisateur existe déjà."

def login_user(username: str, password: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id, username FROM users WHERE username=? AND password=?",
              (username.strip(), hash_pw(password)))
    row = c.fetchone()
    conn.close()
    return row  # (user_id, username) or None

# ── Data helpers (scoped to user_id) ─────────────────────────────────────────
def get_config(user_id: int, key: str, default=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE user_id=? AND key=?", (user_id, key))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else default

def set_config(user_id: int, key: str, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config (user_id, key, value) VALUES (?,?,?)",
              (user_id, key, json.dumps(value)))
    conn.commit()
    conn.close()

def upsert_entry(user_id: int, entry_date: str, income: float, expenses: float, note: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO daily_entries (user_id, entry_date, income, expenses, note)
        VALUES (?,?,?,?,?)
        ON CONFLICT(user_id, entry_date) DO UPDATE SET
            income=excluded.income,
            expenses=excluded.expenses,
            note=excluded.note
    """, (user_id, entry_date, income, expenses, note))
    conn.commit()
    conn.close()

def get_all_entries(user_id: int):
    conn = get_conn()
    df = pd.read_sql(
        "SELECT entry_date, income, expenses, note FROM daily_entries WHERE user_id=? ORDER BY entry_date",
        conn, params=(user_id,)
    )
    conn.close()
    return df

def get_entry(user_id: int, entry_date: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT income, expenses, note FROM daily_entries WHERE user_id=? AND entry_date=?",
              (user_id, entry_date))
    row = c.fetchone()
    conn.close()
    return row

# ── CSS ───────────────────────────────────────────────────────────────────────
def inject_css(progress_pct: float = 0):
    avatar_left = max(2, min(88, progress_pct * 88 / 100))
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Jost:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {{ font-family: 'Jost', sans-serif; }}

    .stApp {{ background-color: #f5efe6; color: #3d2b1f; }}

    section[data-testid="stSidebar"] {{
        background: #ede4d8 !important;
        border-right: 1px solid #d9cbbe;
    }}
    section[data-testid="stSidebar"] * {{ color: #5a3e2b !important; }}
    section[data-testid="stSidebar"] .stExpander {{
        background: #e8ddd0 !important;
        border: 1px solid #d0c4b0 !important;
        border-radius: 12px !important;
    }}

    h1, h2, h3 {{
        font-family: 'Cormorant Garamond', serif !important;
        color: #3d2b1f !important;
        letter-spacing: 0.02em;
    }}

    /* ── Login card ── */
    .login-wrap {{
        max-width: 420px;
        margin: 60px auto 0;
        background: #ffffff;
        border: 1px solid #e4d8c8;
        border-radius: 24px;
        padding: 40px 36px;
        box-shadow: 0 4px 32px rgba(139,90,60,0.10);
        text-align: center;
    }}
    .login-title {{
        font-family: 'Cormorant Garamond', serif;
        font-size: 2rem;
        font-weight: 700;
        color: #3d2b1f;
        margin-bottom: 4px;
    }}
    .login-sub {{
        color: #a89080;
        font-size: 0.88rem;
        margin-bottom: 28px;
    }}

    /* ── Stat cards ── */
    .stat-card {{
        background: #ffffff;
        border: 1px solid #e4d8c8;
        border-radius: 18px;
        padding: 22px 18px;
        text-align: center;
        box-shadow: 0 2px 12px rgba(139,90,60,0.07);
        transition: transform 0.25s, box-shadow 0.25s;
    }}
    .stat-card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 24px rgba(139,90,60,0.12); }}
    .stat-label {{
        font-size: 0.7rem; letter-spacing: 0.14em; text-transform: uppercase;
        color: #a89080; margin-bottom: 8px; font-weight: 500;
    }}
    .stat-value {{
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.65rem; font-weight: 700; color: #a0522d;
    }}
    .stat-value.green {{ color: #5a8a5a; }}
    .stat-value.red   {{ color: #c0504a; }}
    .stat-value.blue  {{ color: #5a7aaa; }}

    /* ── Progress ── */
    .progress-wrap {{
        background: #ffffff; border: 1px solid #e4d8c8; border-radius: 20px;
        padding: 28px 28px 22px; margin: 16px 0;
        box-shadow: 0 2px 16px rgba(139,90,60,0.07);
    }}
    .progress-title {{
        font-family: 'Cormorant Garamond', serif; font-size: 1.15rem;
        font-weight: 600; color: #7a5030; margin-bottom: 20px; letter-spacing: 0.04em;
    }}
    .road {{
        position: relative; height: 56px;
        background: linear-gradient(90deg, #e8ddd0 0%, #f0e8dc 100%);
        border-radius: 14px; overflow: visible; margin-bottom: 14px;
        border: 1px solid #d8ccc0;
    }}
    .road::before {{
        content: ''; position: absolute; top: 50%; left: 0; right: 0; height: 2px;
        background: repeating-linear-gradient(90deg,#c8b8a8 0px,#c8b8a8 16px,transparent 16px,transparent 28px);
        transform: translateY(-50%); opacity: 0.6;
    }}
    .road-fill {{
        position: absolute; top: 0; left: 0; bottom: 0;
        width: {progress_pct:.1f}%;
        background: linear-gradient(90deg, #c8956a, #e8b48a);
        border-radius: 14px; transition: width 1.4s cubic-bezier(0.4,0,0.2,1); opacity: 0.5;
    }}
    .flag {{
        position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
        font-size: 1.6rem; animation: flagWave 1.8s ease-in-out infinite alternate; z-index: 3;
    }}
    @keyframes flagWave {{
        from {{ transform: translateY(-50%) rotate(-7deg); }}
        to   {{ transform: translateY(-50%) rotate(7deg); }}
    }}
    .avatar {{
        position: absolute; left: {avatar_left:.1f}%; top: 50%;
        transform: translate(-50%,-50%); font-size: 1.9rem; z-index: 4;
        transition: left 1.4s cubic-bezier(0.4,0,0.2,1);
        animation: bounce 0.7s ease-in-out infinite alternate;
        filter: drop-shadow(0 2px 6px rgba(160,82,45,0.3));
    }}
    @keyframes bounce {{
        from {{ transform: translate(-50%,-50%); }}
        to   {{ transform: translate(-50%,-58%); }}
    }}
    .pct-bar-bg {{ height: 7px; background: #ede4d8; border-radius: 99px; overflow: hidden; }}
    .pct-bar-fill {{
        height: 100%; width: {progress_pct:.1f}%;
        background: linear-gradient(90deg, #c8956a, #e8b030);
        border-radius: 99px; transition: width 1.4s cubic-bezier(0.4,0,0.2,1);
    }}
    .pct-label {{
        display: flex; justify-content: space-between;
        font-size: 0.76rem; color: #a89080; margin-top: 7px; font-weight: 500;
    }}

    .section-title {{
        font-family: 'Cormorant Garamond', serif; font-size: 1.25rem; font-weight: 600;
        color: #7a5030; border-bottom: 1px solid #ddd0c0;
        padding-bottom: 8px; margin: 28px 0 16px; letter-spacing: 0.03em;
    }}

    .stNumberInput input, .stTextInput input, .stDateInput input {{
        background: #ffffff !important; border: 1px solid #d8ccc0 !important;
        border-radius: 10px !important; color: #3d2b1f !important;
        font-family: 'Jost', sans-serif !important;
    }}
    .stSelectbox > div > div {{
        background: #ffffff !important; border: 1px solid #d8ccc0 !important;
        border-radius: 10px !important;
    }}

    div[data-testid="stButton"] button {{
        background: linear-gradient(135deg, #c8956a, #a0652a) !important;
        color: #fff8f2 !important; border: none !important;
        border-radius: 12px !important; font-family: 'Jost', sans-serif !important;
        font-weight: 600 !important; letter-spacing: 0.05em !important;
        padding: 10px 28px !important;
        transition: opacity 0.2s, transform 0.2s !important;
        box-shadow: 0 4px 14px rgba(160,82,45,0.25) !important;
    }}
    div[data-testid="stButton"] button:hover {{
        opacity: 0.88 !important; transform: translateY(-1px) !important;
    }}

    .success-msg {{
        background: #eef5ec; border: 1px solid #8ab88a; border-radius: 10px;
        padding: 12px 16px; color: #4a7a4a; font-size: 0.88rem; font-weight: 500;
    }}
    .error-msg {{
        background: #fdf0ee; border: 1px solid #d88a8a; border-radius: 10px;
        padding: 12px 16px; color: #a04040; font-size: 0.88rem; font-weight: 500;
    }}

    .stDataFrame {{ border-radius: 14px; overflow: hidden; }}
    .stAlert {{
        background: #fdf6ee !important; border: 1px solid #e4d0b8 !important;
        border-radius: 10px !important; color: #7a5030 !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt(n: float) -> str:
    return f"{n:,.0f} Ar"

def working_days_until(target_date: date, no_income_day: int = 6) -> int:
    count, d = 0, date.today()
    while d < target_date:
        if d.weekday() != no_income_day:
            count += 1
        d += timedelta(days=1)
    return count

# ── Init DB ───────────────────────────────────────────────────────────────────
init_db()

# ── Session state ─────────────────────────────────────────────────────────────
if "user_id"   not in st.session_state: st.session_state.user_id   = None
if "username"  not in st.session_state: st.session_state.username  = None
if "auth_mode" not in st.session_state: st.session_state.auth_mode = "login"

# ─────────────────────────────────────────────────────────────────────────────
# AUTH SCREEN
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.user_id is None:
    inject_css(0)

    st.markdown("""
    <h1 style='text-align:center; font-size:2.4rem; margin-bottom:4px;
               font-family: Cormorant Garamond, serif; color:#3d2b1f;'>
        🎯 Mon Objectif Épargne
    </h1>
    <p style='text-align:center; color:#a89080; font-size:0.9rem; margin-bottom:8px;'>
        Suis ton objectif, jour après jour.
    </p>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 1.2, 1])
    with col_m:
        mode = st.radio("", ["Connexion", "Créer un compte"],
                        horizontal=True, label_visibility="collapsed")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        username_inp = st.text_input("Nom d'utilisateur", placeholder="ex: fatima", key="auth_user")
        password_inp = st.text_input("Mot de passe", type="password", placeholder="••••••••", key="auth_pw")

        if mode == "Connexion":
            if st.button("Se connecter", use_container_width=True):
                result = login_user(username_inp, password_inp)
                if result:
                    st.session_state.user_id  = result[0]
                    st.session_state.username = result[1]
                    st.rerun()
                else:
                    st.markdown('<div class="error-msg">❌ Identifiants incorrects.</div>',
                                unsafe_allow_html=True)
        else:
            if st.button("Créer mon compte", use_container_width=True):
                if len(username_inp.strip()) < 2:
                    st.markdown('<div class="error-msg">❌ Nom trop court (min 2 caractères).</div>',
                                unsafe_allow_html=True)
                elif len(password_inp) < 4:
                    st.markdown('<div class="error-msg">❌ Mot de passe trop court (min 4 caractères).</div>',
                                unsafe_allow_html=True)
                else:
                    ok, msg = register_user(username_inp, password_inp)
                    if ok:
                        st.markdown(f'<div class="success-msg">✔ {msg} Tu peux maintenant te connecter.</div>',
                                    unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="error-msg">❌ {msg}</div>',
                                    unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP (authenticated)
# ─────────────────────────────────────────────────────────────────────────────
uid = st.session_state.user_id

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    if st.button("🚪 Se déconnecter"):
        st.session_state.user_id  = None
        st.session_state.username = None
        st.rerun()

    st.markdown("---")
    st.markdown("## ⚙️ Configuration")

    saved_balance   = get_config(uid, "initial_balance", 0.0)
    saved_goal      = get_config(uid, "goal_amount",     1_200_000.0)
    saved_deadline  = get_config(uid, "deadline",        str(date(2025, 8, 31)))
    saved_daily_inc = get_config(uid, "daily_income",    10_000.0)
    saved_no_day    = get_config(uid, "no_income_day",   6)

    with st.expander("💰 Objectif & Solde initial", expanded=True):
        initial_balance = st.number_input("Solde de départ (Ar)", value=float(saved_balance), step=1000.0, format="%.0f")
        goal_amount     = st.number_input("Objectif (Ar)",        value=float(saved_goal),    step=10000.0, format="%.0f")
        deadline_str    = st.date_input("Date limite", value=date.fromisoformat(saved_deadline))
        deadline        = deadline_str if isinstance(deadline_str, date) else date.fromisoformat(str(deadline_str))

    with st.expander("📅 Revenus fixes", expanded=True):
        daily_income  = st.number_input("Revenu fixe / jour (Ar)", value=float(saved_daily_inc), step=500.0, format="%.0f")
        day_labels    = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
        no_income_day = st.selectbox("Jour sans revenu", options=list(range(7)),
                                     format_func=lambda x: day_labels[x], index=int(saved_no_day))

    if st.button("💾 Enregistrer la config"):
        set_config(uid, "initial_balance", initial_balance)
        set_config(uid, "goal_amount",     goal_amount)
        set_config(uid, "deadline",        str(deadline))
        set_config(uid, "daily_income",    daily_income)
        set_config(uid, "no_income_day",   no_income_day)
        st.success("Configuration sauvegardée !")
    else:
        initial_balance = float(saved_balance)
        goal_amount     = float(saved_goal)
        deadline        = date.fromisoformat(saved_deadline)
        daily_income    = float(saved_daily_inc)
        no_income_day   = int(saved_no_day)

# ── Compute ───────────────────────────────────────────────────────────────────
df = get_all_entries(uid)
total_income   = df["income"].sum()   if not df.empty else 0.0
total_expenses = df["expenses"].sum() if not df.empty else 0.0
current_balance = initial_balance + total_income - total_expenses
progress_pct    = min(100.0, max(0.0, current_balance / goal_amount * 100)) if goal_amount else 0
remaining       = max(0.0, goal_amount - current_balance)
work_days_left  = working_days_until(deadline, no_income_day)
projected_final = current_balance + work_days_left * daily_income
on_track        = projected_final >= goal_amount

# ── CSS ───────────────────────────────────────────────────────────────────────
inject_css(progress_pct)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<h1 style='text-align:center; font-size:2.4rem; margin-bottom:4px;
           font-family: Cormorant Garamond, serif; color:#3d2b1f;'>
    🎯 Mon Objectif Épargne
</h1>
<p style='text-align:center; color:#a89080; font-size:0.9rem; margin-bottom:28px;'>
    Bonjour <strong style="color:#a0522d">{st.session_state.username}</strong> — Chaque jour compte, reste focalisée. 💪
</p>
""", unsafe_allow_html=True)

# ── Avatar progress ───────────────────────────────────────────────────────────
st.markdown(f"""
<div class="progress-wrap">
    <div class="progress-title">📍 Progression vers l'objectif</div>
    <div class="road">
        <div class="road-fill"></div>
        <div class="avatar">🏃‍♀️</div>
        <div class="flag">🏁</div>
    </div>
    <div class="pct-bar-bg"><div class="pct-bar-fill"></div></div>
    <div class="pct-label">
        <span>0 Ar</span>
        <span style="color:#c8956a; font-weight:600;">{progress_pct:.1f}% atteint</span>
        <span>{fmt(goal_amount)}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── KPI Cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="stat-card"><div class="stat-label">Solde actuel</div><div class="stat-value">{fmt(current_balance)}</div></div>', unsafe_allow_html=True)
with c2:
    col = "red" if remaining > 0 else "green"
    st.markdown(f'<div class="stat-card"><div class="stat-label">Reste à épargner</div><div class="stat-value {col}">{fmt(remaining)}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="stat-card"><div class="stat-label">Jours ouvrés restants</div><div class="stat-value blue">{work_days_left} j</div></div>', unsafe_allow_html=True)
with c4:
    tc = "green" if on_track else "red"
    ti = "✅" if on_track else "⚠️"
    st.markdown(f'<div class="stat-card"><div class="stat-label">Projection finale</div><div class="stat-value {tc}">{ti} {fmt(projected_final)}</div></div>', unsafe_allow_html=True)

# ── Daily Entry ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📝 Saisie du jour</div>', unsafe_allow_html=True)
col_a, col_b = st.columns([1, 2])

with col_a:
    entry_date   = st.date_input("Date", value=date.today(), key="entry_date")
    is_no_income = entry_date.weekday() == no_income_day
    existing     = get_entry(uid, str(entry_date))
    if existing:
        def_income, def_exp, def_note = existing
    else:
        def_income = 0.0 if is_no_income else daily_income
        def_exp, def_note = 0.0, ""
    if is_no_income:
        st.info(f"📅 {day_labels[no_income_day]} — pas de revenu fixe.")

with col_b:
    income_in  = st.number_input("Revenu du jour (Ar)",   value=float(def_income), step=500.0,  format="%.0f", key="inc")
    expense_in = st.number_input("Dépenses du jour (Ar)", value=float(def_exp),    step=100.0,  format="%.0f", key="exp")
    note_in    = st.text_input("Note (optionnel)", value=def_note, placeholder="ex: courses, transport…", key="note")

    net_day   = income_in - expense_in
    net_color = "#5a8a5a" if net_day >= 0 else "#c0504a"
    st.markdown(f"<p style='color:{net_color}; font-weight:600;'>Net du jour : {fmt(net_day)}</p>", unsafe_allow_html=True)

    if st.button("✅ Enregistrer cette journée"):
        upsert_entry(uid, str(entry_date), income_in, expense_in, note_in)
        st.markdown('<div class="success-msg">✔ Journée enregistrée avec succès !</div>', unsafe_allow_html=True)
        st.rerun()

# ── History ───────────────────────────────────────────────────────────────────
if not df.empty:
    st.markdown('<div class="section-title">📊 Historique</div>', unsafe_allow_html=True)
    df_d = df.copy()
    df_d["net"] = df_d["income"] - df_d["expenses"]
    df_d.columns = ["Date","Revenu (Ar)","Dépenses (Ar)","Note","Net (Ar)"]
    st.dataframe(df_d.sort_values("Date", ascending=False), use_container_width=True, hide_index=True,
                 column_config={
                     "Revenu (Ar)":   st.column_config.NumberColumn(format="%,.0f"),
                     "Dépenses (Ar)": st.column_config.NumberColumn(format="%,.0f"),
                     "Net (Ar)":      st.column_config.NumberColumn(format="%,.0f"),
                 })

    st.markdown('<div class="section-title">📈 Évolution du solde cumulé</div>', unsafe_allow_html=True)
    df_c = df.sort_values("entry_date").copy()
    df_c["solde"] = initial_balance + (df_c["income"] - df_c["expenses"]).cumsum()
    st.line_chart(df_c.set_index("entry_date")["solde"], height=220)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<p style='text-align:center; color:#c8b0a0; font-size:0.75rem; margin-top:48px;'>
    Objectif {fmt(goal_amount)} avant le {deadline.strftime('%d %B %Y')} — Tu peux le faire 💪
</p>
""", unsafe_allow_html=True)
