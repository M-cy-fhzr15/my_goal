import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta
import json
import os

# ── Page config ──────────────────────────────────────────────────────────────
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

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_entries (
            entry_date TEXT PRIMARY KEY,
            income      REAL DEFAULT 0,
            expenses    REAL DEFAULT 0,
            note        TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()

def get_config(key, default=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else default

def set_config(key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?,?)",
              (key, json.dumps(value)))
    conn.commit()
    conn.close()

def upsert_entry(entry_date: str, income: float, expenses: float, note: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO daily_entries (entry_date, income, expenses, note)
        VALUES (?,?,?,?)
        ON CONFLICT(entry_date) DO UPDATE SET
            income=excluded.income,
            expenses=excluded.expenses,
            note=excluded.note
    """, (entry_date, income, expenses, note))
    conn.commit()
    conn.close()

def get_all_entries():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM daily_entries ORDER BY entry_date", conn)
    conn.close()
    return df

def get_entry(entry_date: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM daily_entries WHERE entry_date=?", (entry_date,))
    row = c.fetchone()
    conn.close()
    return row  # (date, income, expenses, note)

# ── CSS + Animation ───────────────────────────────────────────────────────────
def inject_css(progress_pct: float):
    avatar_left = max(2, min(88, progress_pct * 88 / 100))
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500&display=swap');

    html, body, [class*="css"] {{
        font-family: 'DM Sans', sans-serif;
    }}

    .stApp {{
        background: #0f0f14;
        color: #e8e0d0;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background: #16161f !important;
        border-right: 1px solid #2a2a3a;
    }}
    section[data-testid="stSidebar"] * {{
        color: #c8c0b0 !important;
    }}

    h1, h2, h3 {{
        font-family: 'Playfair Display', serif !important;
        color: #f0e8d8 !important;
    }}

    /* Cards */
    .stat-card {{
        background: linear-gradient(135deg, #1a1a26 0%, #1e1e2e 100%);
        border: 1px solid #2e2e42;
        border-radius: 16px;
        padding: 24px 20px;
        text-align: center;
        transition: transform 0.2s;
    }}
    .stat-card:hover {{ transform: translateY(-3px); }}
    .stat-label {{
        font-size: 0.75rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #6a6a8a;
        margin-bottom: 8px;
    }}
    .stat-value {{
        font-family: 'Playfair Display', serif;
        font-size: 1.6rem;
        font-weight: 900;
        color: #f0c060;
    }}
    .stat-value.green  {{ color: #60d4a0; }}
    .stat-value.red    {{ color: #e07070; }}
    .stat-value.blue   {{ color: #70a8e0; }}

    /* Progress track */
    .progress-wrap {{
        background: #1a1a26;
        border: 1px solid #2e2e42;
        border-radius: 20px;
        padding: 28px 28px 20px;
        margin: 16px 0;
        position: relative;
        overflow: hidden;
    }}
    .progress-title {{
        font-family: 'Playfair Display', serif;
        font-size: 1.1rem;
        color: #c8b88a;
        margin-bottom: 20px;
        letter-spacing: 0.05em;
    }}

    /* Road */
    .road {{
        position: relative;
        height: 54px;
        background: linear-gradient(90deg, #1e3a2a 0%, #2a4a3a 100%);
        border-radius: 12px;
        overflow: visible;
        margin-bottom: 12px;
        border: 1px solid #3a5a4a;
    }}
    /* Dashed lane line */
    .road::before {{
        content: '';
        position: absolute;
        top: 50%;
        left: 0; right: 0;
        height: 2px;
        background: repeating-linear-gradient(
            90deg, #4a7a5a 0px, #4a7a5a 18px, transparent 18px, transparent 32px
        );
        transform: translateY(-50%);
        opacity: 0.5;
    }}
    /* Progress fill */
    .road-fill {{
        position: absolute;
        top: 0; left: 0; bottom: 0;
        width: {progress_pct:.1f}%;
        background: linear-gradient(90deg, #1a5a3a, #30c070);
        border-radius: 12px;
        transition: width 1.2s cubic-bezier(0.4, 0, 0.2, 1);
        opacity: 0.45;
    }}
    /* Flag at end */
    .flag {{
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 1.6rem;
        animation: flagWave 1.5s ease-in-out infinite alternate;
        z-index: 3;
    }}
    @keyframes flagWave {{
        from {{ transform: translateY(-50%) rotate(-8deg); }}
        to   {{ transform: translateY(-50%) rotate(8deg); }}
    }}

    /* Avatar */
    .avatar {{
        position: absolute;
        left: {avatar_left:.1f}%;
        top: 50%;
        transform: translate(-50%, -50%);
        font-size: 1.8rem;
        z-index: 4;
        transition: left 1.2s cubic-bezier(0.4, 0, 0.2, 1);
        animation: walk 0.6s steps(2) infinite;
        filter: drop-shadow(0 2px 8px #30c07088);
    }}
    @keyframes walk {{
        0%   {{ transform: translate(-50%, -50%) scaleX(1); }}
        50%  {{ transform: translate(-50%, -54%) scaleX(1); }}
        100% {{ transform: translate(-50%, -50%) scaleX(1); }}
    }}

    /* Bar below road */
    .pct-bar-bg {{
        height: 8px;
        background: #2a2a3a;
        border-radius: 99px;
        overflow: hidden;
    }}
    .pct-bar-fill {{
        height: 100%;
        width: {progress_pct:.1f}%;
        background: linear-gradient(90deg, #30c070, #f0c060);
        border-radius: 99px;
        transition: width 1.2s cubic-bezier(0.4,0,0.2,1);
    }}
    .pct-label {{
        display: flex;
        justify-content: space-between;
        font-size: 0.78rem;
        color: #6a6a8a;
        margin-top: 6px;
    }}

    /* Table */
    .stDataFrame {{ border-radius: 12px; overflow: hidden; }}

    /* Inputs */
    .stNumberInput input, .stTextInput input, .stDateInput input {{
        background: #1a1a26 !important;
        border: 1px solid #2e2e42 !important;
        border-radius: 8px !important;
        color: #e8e0d0 !important;
    }}
    .stSelectbox > div > div {{
        background: #1a1a26 !important;
        border: 1px solid #2e2e42 !important;
        border-radius: 8px !important;
    }}
    div[data-testid="stButton"] button {{
        background: linear-gradient(135deg, #30c070, #20a060) !important;
        color: #0f0f14 !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 10px 24px !important;
        transition: opacity 0.2s !important;
    }}
    div[data-testid="stButton"] button:hover {{ opacity: 0.85 !important; }}

    .section-title {{
        font-family: 'Playfair Display', serif;
        font-size: 1.3rem;
        color: #c8b88a;
        border-bottom: 1px solid #2e2e42;
        padding-bottom: 8px;
        margin: 24px 0 16px;
    }}

    .success-msg {{
        background: #1a3a2a;
        border: 1px solid #30c070;
        border-radius: 10px;
        padding: 12px 16px;
        color: #60d4a0;
        font-size: 0.9rem;
    }}
    </style>
    """, unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt(n: float) -> str:
    return f"{n:,.0f} Ar"

def days_until(target_date: date) -> int:
    return max(0, (target_date - date.today()).days)

def working_days_until(target_date: date, no_income_day: int = 6) -> int:
    """Count days from today to target_date excluding no_income_day (0=Mon…6=Sun)."""
    count = 0
    d = date.today()
    while d < target_date:
        if d.weekday() != no_income_day:
            count += 1
        d += timedelta(days=1)
    return count

# ── Init ──────────────────────────────────────────────────────────────────────
init_db()

# ── Sidebar – Configuration ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    saved_balance   = get_config("initial_balance", 0.0)
    saved_goal      = get_config("goal_amount", 1_200_000.0)
    saved_deadline  = get_config("deadline", str(date(2025, 8, 31)))
    saved_daily_inc = get_config("daily_income", 10_000.0)
    saved_no_day    = get_config("no_income_day", 6)  # 6 = Sunday

    with st.expander("💰 Objectif & Solde initial", expanded=True):
        initial_balance = st.number_input("Solde de départ (Ar)", value=float(saved_balance), step=1000.0, format="%.0f")
        goal_amount     = st.number_input("Objectif (Ar)",        value=float(saved_goal),   step=10000.0, format="%.0f")
        deadline_str    = st.date_input("Date limite", value=date.fromisoformat(saved_deadline))
        deadline        = deadline_str if isinstance(deadline_str, date) else date.fromisoformat(str(deadline_str))

    with st.expander("📅 Revenus fixes", expanded=True):
        daily_income = st.number_input("Revenu fixe / jour (Ar)", value=float(saved_daily_inc), step=500.0, format="%.0f")
        day_labels   = ["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
        no_income_day = st.selectbox("Jour sans revenu", options=list(range(7)),
                                     format_func=lambda x: day_labels[x],
                                     index=int(saved_no_day))

    if st.button("💾 Enregistrer la config"):
        set_config("initial_balance", initial_balance)
        set_config("goal_amount",     goal_amount)
        set_config("deadline",        str(deadline))
        set_config("daily_income",    daily_income)
        set_config("no_income_day",   no_income_day)
        st.success("Configuration sauvegardée !")
    else:
        # Use saved values for computation if button not pressed
        initial_balance = float(saved_balance)
        goal_amount     = float(saved_goal)
        deadline        = date.fromisoformat(saved_deadline)
        daily_income    = float(saved_daily_inc)
        no_income_day   = int(saved_no_day)

# ── Compute totals ────────────────────────────────────────────────────────────
df = get_all_entries()
total_income_logged   = df["income"].sum()   if not df.empty else 0.0
total_expenses_logged = df["expenses"].sum() if not df.empty else 0.0
current_balance = initial_balance + total_income_logged - total_expenses_logged
progress_pct    = min(100.0, max(0.0, current_balance / goal_amount * 100)) if goal_amount else 0
remaining       = max(0.0, goal_amount - current_balance)
work_days_left  = working_days_until(deadline, no_income_day)
projected_extra = work_days_left * daily_income
projected_final = current_balance + projected_extra
on_track        = projected_final >= goal_amount

# ── Inject CSS ────────────────────────────────────────────────────────────────
inject_css(progress_pct)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='text-align:center; font-size:2.2rem; margin-bottom:4px;'>
    🎯 Mon Objectif Épargne
</h1>
<p style='text-align:center; color:#6a6a8a; font-size:0.9rem; margin-bottom:28px;'>
    Chaque jour compte — reste constante, reste focalisée.
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
        <span style="color:#f0c060; font-weight:600;">{progress_pct:.1f}% atteint</span>
        <span>{fmt(goal_amount)}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── KPI Cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">Solde actuel</div>
        <div class="stat-value">{fmt(current_balance)}</div>
    </div>""", unsafe_allow_html=True)

with c2:
    color = "red" if remaining > 0 else "green"
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">Reste à épargner</div>
        <div class="stat-value {color}">{fmt(remaining)}</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">Jours ouvrés restants</div>
        <div class="stat-value blue">{work_days_left} j</div>
    </div>""", unsafe_allow_html=True)

with c4:
    track_color = "green" if on_track else "red"
    track_icon  = "✅" if on_track else "⚠️"
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">Projection finale</div>
        <div class="stat-value {track_color}">{track_icon} {fmt(projected_final)}</div>
    </div>""", unsafe_allow_html=True)

# ── Daily Entry ───────────────────────────────────────────────────────────────
st.markdown('<div class="section-title">📝 Saisie du jour</div>', unsafe_allow_html=True)

col_a, col_b = st.columns([1, 2])

with col_a:
    entry_date = st.date_input("Date", value=date.today(), key="entry_date")
    is_no_income = entry_date.weekday() == no_income_day
    default_income = 0.0 if is_no_income else daily_income

    existing = get_entry(str(entry_date))
    if existing:
        default_income   = existing[1]
        default_expenses = existing[2]
        default_note     = existing[3]
    else:
        default_expenses = 0.0
        default_note     = ""

    if is_no_income:
        st.info(f"📅 {day_labels[no_income_day]} — pas de revenu fixe ce jour.")

with col_b:
    income_in   = st.number_input("Revenu du jour (Ar)",  value=float(default_income),   step=500.0,  format="%.0f", key="inc")
    expense_in  = st.number_input("Dépenses du jour (Ar)", value=float(default_expenses), step=100.0, format="%.0f", key="exp")
    note_in     = st.text_input("Note (optionnel)", value=default_note, placeholder="ex: courses, transport…", key="note")

    net_day = income_in - expense_in
    net_color = "#60d4a0" if net_day >= 0 else "#e07070"
    st.markdown(f"<p style='color:{net_color}; font-weight:600;'>Net du jour : {fmt(net_day)}</p>", unsafe_allow_html=True)

    if st.button("✅ Enregistrer cette journée"):
        upsert_entry(str(entry_date), income_in, expense_in, note_in)
        st.markdown('<div class="success-msg">✔ Journée enregistrée avec succès !</div>', unsafe_allow_html=True)
        st.rerun()

# ── History table ─────────────────────────────────────────────────────────────
if not df.empty:
    st.markdown('<div class="section-title">📊 Historique</div>', unsafe_allow_html=True)

    df_display = df.copy()
    df_display["net"] = df_display["income"] - df_display["expenses"]
    df_display.columns = ["Date","Revenu (Ar)","Dépenses (Ar)","Note","Net (Ar)"]
    df_display = df_display.sort_values("Date", ascending=False)

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Revenu (Ar)":   st.column_config.NumberColumn(format="%,.0f"),
            "Dépenses (Ar)": st.column_config.NumberColumn(format="%,.0f"),
            "Net (Ar)":      st.column_config.NumberColumn(format="%,.0f"),
        }
    )

    # Mini chart
    st.markdown('<div class="section-title">📈 Évolution du solde cumulé</div>', unsafe_allow_html=True)
    df_chart = df.sort_values("entry_date").copy()
    df_chart["solde_cumulé"] = initial_balance + (df_chart["income"] - df_chart["expenses"]).cumsum()
    st.line_chart(df_chart.set_index("entry_date")["solde_cumulé"], height=220)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<p style='text-align:center; color:#3a3a5a; font-size:0.75rem; margin-top:48px;'>
    Objectif {fmt(goal_amount)} avant le {deadline.strftime('%d %B %Y')} — Tu peux le faire 💪
</p>
""", unsafe_allow_html=True)
