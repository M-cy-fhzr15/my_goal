import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
from datetime import date, timedelta
import hashlib
import os

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mon Objectif Épargne",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL = st.secrets["DATABASE_URL"]

@st.cache_resource
def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def run(sql, params=(), fetch=None):
    conn = get_conn()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        conn.commit()
        if fetch == "one":  return cur.fetchone()
        if fetch == "all":  return cur.fetchall()

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    run("""
        CREATE TABLE IF NOT EXISTS users (
            user_id  SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    run("""
        CREATE TABLE IF NOT EXISTS config (
            user_id INTEGER NOT NULL,
            key     TEXT    NOT NULL,
            value   TEXT,
            PRIMARY KEY (user_id, key)
        )
    """)
    run("""
        CREATE TABLE IF NOT EXISTS daily_entries (
            user_id    INTEGER NOT NULL,
            entry_date DATE    NOT NULL,
            income     REAL    DEFAULT 0,
            expenses   REAL    DEFAULT 0,
            note       TEXT    DEFAULT '',
            PRIMARY KEY (user_id, entry_date)
        )
    """)

# ── Auth ──────────────────────────────────────────────────────────────────────
def register_user(username, password):
    try:
        run("INSERT INTO users (username, password) VALUES (%s,%s)",
            (username.strip(), hash_pw(password)))
        return True, "Compte créé !"
    except psycopg2.errors.UniqueViolation:
        get_conn().rollback()
        return False, "Ce nom d'utilisateur existe déjà."

def login_user(username, password):
    row = run("SELECT user_id, username FROM users WHERE username=%s AND password=%s",
              (username.strip(), hash_pw(password)), fetch="one")
    return row

# ── Config helpers ────────────────────────────────────────────────────────────
def get_config(uid, key, default=None):
    row = run("SELECT value FROM config WHERE user_id=%s AND key=%s", (uid, key), fetch="one")
    return row["value"] if row else default

def set_config(uid, key, value):
    run("""
        INSERT INTO config (user_id, key, value) VALUES (%s,%s,%s)
        ON CONFLICT (user_id, key) DO UPDATE SET value=EXCLUDED.value
    """, (uid, key, str(value)))

# ── Entry helpers ─────────────────────────────────────────────────────────────
def upsert_entry(uid, entry_date, income, expenses, note):
    run("""
        INSERT INTO daily_entries (user_id, entry_date, income, expenses, note)
        VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (user_id, entry_date) DO UPDATE SET
            income=EXCLUDED.income, expenses=EXCLUDED.expenses, note=EXCLUDED.note
    """, (uid, entry_date, income, expenses, note))

def get_all_entries(uid):
    rows = run("SELECT entry_date, income, expenses, note FROM daily_entries WHERE user_id=%s ORDER BY entry_date",
               (uid,), fetch="all")
    if not rows:
        return pd.DataFrame(columns=["entry_date","income","expenses","note"])
    return pd.DataFrame([dict(r) for r in rows])

def get_entry(uid, entry_date):
    return run("SELECT income, expenses, note FROM daily_entries WHERE user_id=%s AND entry_date=%s",
               (uid, entry_date), fetch="one")

# ── CSS ───────────────────────────────────────────────────────────────────────
def inject_css(progress_pct=0):
    avatar_left = max(2, min(88, progress_pct * 88 / 100))
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Jost:wght@300;400;500;600&display=swap');
    html, body, [class*="css"] {{ font-family: 'Jost', sans-serif; }}
    .stApp {{ background-color: #f5efe6; color: #3d2b1f; }}
    section[data-testid="stSidebar"] {{ background: #ede4d8 !important; border-right: 1px solid #d9cbbe; }}
    section[data-testid="stSidebar"] * {{ color: #5a3e2b !important; }}
    h1, h2, h3 {{ font-family: 'Cormorant Garamond', serif !important; color: #3d2b1f !important; }}
    .stat-card {{ background:#fff; border:1px solid #e4d8c8; border-radius:18px; padding:22px 18px; text-align:center; box-shadow:0 2px 12px rgba(139,90,60,.07); transition:transform .25s,box-shadow .25s; }}
    .stat-card:hover {{ transform:translateY(-4px); box-shadow:0 8px 24px rgba(139,90,60,.12); }}
    .stat-label {{ font-size:.7rem; letter-spacing:.14em; text-transform:uppercase; color:#a89080; margin-bottom:8px; font-weight:500; }}
    .stat-value {{ font-family:'Cormorant Garamond',serif; font-size:1.65rem; font-weight:700; color:#a0522d; }}
    .stat-value.green {{ color:#5a8a5a; }} .stat-value.red {{ color:#c0504a; }} .stat-value.blue {{ color:#5a7aaa; }}
    .progress-wrap {{ background:#fff; border:1px solid #e4d8c8; border-radius:20px; padding:28px 28px 22px; margin:16px 0; box-shadow:0 2px 16px rgba(139,90,60,.07); }}
    .progress-title {{ font-family:'Cormorant Garamond',serif; font-size:1.15rem; font-weight:600; color:#7a5030; margin-bottom:20px; }}
    .road {{ position:relative; height:56px; background:linear-gradient(90deg,#e8ddd0,#f0e8dc); border-radius:14px; overflow:visible; margin-bottom:14px; border:1px solid #d8ccc0; }}
    .road::before {{ content:''; position:absolute; top:50%; left:0; right:0; height:2px; background:repeating-linear-gradient(90deg,#c8b8a8 0,#c8b8a8 16px,transparent 16px,transparent 28px); transform:translateY(-50%); opacity:.6; }}
    .road-fill {{ position:absolute; top:0; left:0; bottom:0; width:{progress_pct:.1f}%; background:linear-gradient(90deg,#c8956a,#e8b48a); border-radius:14px; opacity:.5; }}
    .flag {{ position:absolute; right:10px; top:50%; transform:translateY(-50%); font-size:1.6rem; animation:flagWave 1.8s ease-in-out infinite alternate; z-index:3; }}
    @keyframes flagWave {{ from{{transform:translateY(-50%) rotate(-7deg)}} to{{transform:translateY(-50%) rotate(7deg)}} }}
    .avatar {{ position:absolute; left:{avatar_left:.1f}%; top:50%; transform:translate(-50%,-50%); font-size:1.9rem; z-index:4; animation:bounce .7s ease-in-out infinite alternate; filter:drop-shadow(0 2px 6px rgba(160,82,45,.3)); }}
    @keyframes bounce {{ from{{transform:translate(-50%,-50%)}} to{{transform:translate(-50%,-58%)}} }}
    .pct-bar-bg {{ height:7px; background:#ede4d8; border-radius:99px; overflow:hidden; }}
    .pct-bar-fill {{ height:100%; width:{progress_pct:.1f}%; background:linear-gradient(90deg,#c8956a,#e8b030); border-radius:99px; }}
    .pct-label {{ display:flex; justify-content:space-between; font-size:.76rem; color:#a89080; margin-top:7px; font-weight:500; }}
    .section-title {{ font-family:'Cormorant Garamond',serif; font-size:1.25rem; font-weight:600; color:#7a5030; border-bottom:1px solid #ddd0c0; padding-bottom:8px; margin:28px 0 16px; }}
    .stNumberInput input,.stTextInput input,.stDateInput input {{ background:#fff !important; border:1px solid #d8ccc0 !important; border-radius:10px !important; color:#3d2b1f !important; }}
    .stSelectbox > div > div {{ background:#fff !important; border:1px solid #d8ccc0 !important; border-radius:10px !important; }}
    div[data-testid="stButton"] button {{ background:linear-gradient(135deg,#c8956a,#a0652a) !important; color:#fff8f2 !important; border:none !important; border-radius:12px !important; font-weight:600 !important; padding:10px 28px !important; box-shadow:0 4px 14px rgba(160,82,45,.25) !important; }}
    div[data-testid="stButton"] button:hover {{ opacity:.88 !important; transform:translateY(-1px) !important; }}
    .success-msg {{ background:#eef5ec; border:1px solid #8ab88a; border-radius:10px; padding:12px 16px; color:#4a7a4a; font-size:.88rem; }}
    .error-msg {{ background:#fdf0ee; border:1px solid #d88a8a; border-radius:10px; padding:12px 16px; color:#a04040; font-size:.88rem; }}
    .stDataFrame {{ border-radius:14px; overflow:hidden; }}
    </style>
    """, unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt(n): return f"{float(n):,.0f} Ar"

def working_days_until(target_date, no_income_day=6):
    count, d = 0, date.today()
    while d < target_date:
        if d.weekday() != no_income_day: count += 1
        d += timedelta(days=1)
    return count

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()

if "user_id"  not in st.session_state: st.session_state.user_id  = None
if "username" not in st.session_state: st.session_state.username = None

# ─────────────────────────────────────────────────────────────────────────────
# AUTH SCREEN
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.user_id is None:
    inject_css(0)
    st.markdown("""
    <h1 style='text-align:center;font-size:2.4rem;font-family:Cormorant Garamond,serif;color:#3d2b1f;'>
        🎯 Mon Objectif Épargne
    </h1>
    <p style='text-align:center;color:#a89080;font-size:.9rem;margin-bottom:8px;'>
        Suis ton objectif, jour après jour.
    </p>""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        mode = st.radio("", ["Connexion","Créer un compte"], horizontal=True, label_visibility="collapsed")
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        u = st.text_input("Nom d'utilisateur", placeholder="ex: fatima", key="au")
        p = st.text_input("Mot de passe", type="password", placeholder="••••••••", key="ap")

        if mode == "Connexion":
            if st.button("Se connecter", use_container_width=True):
                row = login_user(u, p)
                if row:
                    st.session_state.user_id  = row["user_id"]
                    st.session_state.username = row["username"]
                    st.rerun()
                else:
                    st.markdown('<div class="error-msg">❌ Identifiants incorrects.</div>', unsafe_allow_html=True)
        else:
            if st.button("Créer mon compte", use_container_width=True):
                if len(u.strip()) < 2:
                    st.markdown('<div class="error-msg">❌ Nom trop court (min 2 caractères).</div>', unsafe_allow_html=True)
                elif len(p) < 4:
                    st.markdown('<div class="error-msg">❌ Mot de passe trop court (min 4 caractères).</div>', unsafe_allow_html=True)
                else:
                    ok, msg = register_user(u, p)
                    if ok:
                        st.markdown(f'<div class="success-msg">✔ {msg} Tu peux maintenant te connecter.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="error-msg">❌ {msg}</div>', unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
uid = st.session_state.user_id

with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    if st.button("🚪 Se déconnecter"):
        st.session_state.user_id = st.session_state.username = None
        st.rerun()
    st.markdown("---")
    st.markdown("## ⚙️ Configuration")

    saved_balance  = get_config(uid, "initial_balance", "0")
    saved_goal     = get_config(uid, "goal_amount",     "1200000")
    saved_deadline = get_config(uid, "deadline",        "2025-08-31")
    saved_inc      = get_config(uid, "daily_income",    "10000")
    saved_no_day   = get_config(uid, "no_income_day",   "6")

    with st.expander("💰 Objectif & Solde initial", expanded=True):
        initial_balance = st.number_input("Solde de départ (Ar)", value=float(saved_balance), step=1000.0, format="%.0f")
        goal_amount     = st.number_input("Objectif (Ar)",        value=float(saved_goal),    step=10000.0, format="%.0f")
        deadline_inp    = st.date_input("Date limite", value=date.fromisoformat(saved_deadline))
        deadline        = deadline_inp if isinstance(deadline_inp, date) else date.fromisoformat(str(deadline_inp))

    day_labels = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
    with st.expander("📅 Revenus fixes", expanded=True):
        daily_income  = st.number_input("Revenu fixe / jour (Ar)", value=float(saved_inc), step=500.0, format="%.0f")
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
        daily_income    = float(saved_inc)
        no_income_day   = int(saved_no_day)

# ── Calculs ───────────────────────────────────────────────────────────────────
df = get_all_entries(uid)
total_income   = df["income"].sum()   if not df.empty else 0.0
total_expenses = df["expenses"].sum() if not df.empty else 0.0
current_balance = initial_balance + total_income - total_expenses
progress_pct    = min(100.0, max(0.0, current_balance / goal_amount * 100)) if goal_amount else 0
remaining       = max(0.0, goal_amount - current_balance)
work_days_left  = working_days_until(deadline, no_income_day)
projected_final = current_balance + work_days_left * daily_income
on_track        = projected_final >= goal_amount

inject_css(progress_pct)

st.markdown(f"""
<h1 style='text-align:center;font-size:2.4rem;font-family:Cormorant Garamond,serif;color:#3d2b1f;'>
    🎯 Mon Objectif Épargne
</h1>
<p style='text-align:center;color:#a89080;font-size:.9rem;margin-bottom:28px;'>
    Bonjour <strong style="color:#a0522d">{st.session_state.username}</strong> — Chaque jour compte 💪
</p>""", unsafe_allow_html=True)

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
        <span style="color:#c8956a;font-weight:600;">{progress_pct:.1f}% atteint</span>
        <span>{fmt(goal_amount)}</span>
    </div>
</div>""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(f'<div class="stat-card"><div class="stat-label">Solde actuel</div><div class="stat-value">{fmt(current_balance)}</div></div>', unsafe_allow_html=True)
with c2:
    col = "red" if remaining > 0 else "green"
    st.markdown(f'<div class="stat-card"><div class="stat-label">Reste à épargner</div><div class="stat-value {col}">{fmt(remaining)}</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-card"><div class="stat-label">Jours ouvrés restants</div><div class="stat-value blue">{work_days_left} j</div></div>', unsafe_allow_html=True)
with c4:
    tc, ti = ("green","✅") if on_track else ("red","⚠️")
    st.markdown(f'<div class="stat-card"><div class="stat-label">Projection finale</div><div class="stat-value {tc}">{ti} {fmt(projected_final)}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">📝 Saisie du jour</div>', unsafe_allow_html=True)
col_a, col_b = st.columns([1, 2])

with col_a:
    entry_date   = st.date_input("Date", value=date.today(), key="entry_date")
    is_no_income = entry_date.weekday() == no_income_day
    existing     = get_entry(uid, str(entry_date))
    if existing:
        def_income, def_exp, def_note = existing["income"], existing["expenses"], existing["note"]
    else:
        def_income, def_exp, def_note = (0.0 if is_no_income else daily_income), 0.0, ""
    if is_no_income:
        st.info(f"📅 {day_labels[no_income_day]} — pas de revenu fixe.")

with col_b:
    income_in  = st.number_input("Revenu du jour (Ar)",   value=float(def_income), step=500.0,  format="%.0f", key="inc")
    expense_in = st.number_input("Dépenses du jour (Ar)", value=float(def_exp),    step=100.0,  format="%.0f", key="exp")
    note_in    = st.text_input("Note (optionnel)", value=def_note, placeholder="ex: courses…", key="note")
    net_day    = income_in - expense_in
    net_color  = "#5a8a5a" if net_day >= 0 else "#c0504a"
    st.markdown(f"<p style='color:{net_color};font-weight:600;'>Net du jour : {fmt(net_day)}</p>", unsafe_allow_html=True)
    if st.button("✅ Enregistrer cette journée"):
        upsert_entry(uid, str(entry_date), income_in, expense_in, note_in)
        st.markdown('<div class="success-msg">✔ Journée enregistrée !</div>', unsafe_allow_html=True)
        st.rerun()

if not df.empty:
    st.markdown('<div class="section-title">📊 Historique</div>', unsafe_allow_html=True)
    df_d = df.copy()
    df_d["net"] = df_d["income"] - df_d["expenses"]
    df_d.columns = ["Date","Revenu (Ar)","Dépenses (Ar)","Note","Net (Ar)"]
    st.dataframe(df_d.sort_values("Date", ascending=False), use_container_width=True, hide_index=True,
                 column_config={"Revenu (Ar)": st.column_config.NumberColumn(format="%,.0f"),
                                "Dépenses (Ar)": st.column_config.NumberColumn(format="%,.0f"),
                                "Net (Ar)": st.column_config.NumberColumn(format="%,.0f")})
    st.markdown('<div class="section-title">📈 Évolution du solde cumulé</div>', unsafe_allow_html=True)
    df_c = df.sort_values("entry_date").copy()
    df_c["solde"] = initial_balance + (df_c["income"] - df_c["expenses"]).cumsum()
    st.line_chart(df_c.set_index("entry_date")["solde"], height=220)

st.markdown(f"""
<p style='text-align:center;color:#c8b0a0;font-size:.75rem;margin-top:48px;'>
    Objectif {fmt(goal_amount)} avant le {deadline.strftime('%d %B %Y')} — Tu peux le faire 💪
</p>""", unsafe_allow_html=True)
