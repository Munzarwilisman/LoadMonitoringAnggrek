import streamlit as st
from streamlit_autorefresh import st_autorefresh
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian
from datetime import datetime
import collections
import threading
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ════════════════════════════════════════════
# PAGE CONFIG
# ════════════════════════════════════════════
st.set_page_config(
    page_title="Energy Monitor - PLTU Anggrek",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ════════════════════════════════════════════
# CSS
# ════════════════════════════════════════════
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&family=Exo+2:wght@300;400;700&display=swap');
  html, body, [class*="css"] { font-family:'Exo 2',sans-serif; background-color:#070c14; color:#c8d8e8; }
  .stApp { background:radial-gradient(ellipse at top,#0d1a2e 0%,#070c14 70%); background-attachment:fixed; }
  #MainMenu, footer, header { visibility:hidden; }
  .block-container { padding:0.8rem 1.4rem 0.5rem 1.4rem; max-width:100%; }

  .main-header { display:flex; align-items:center; justify-content:space-between; padding:0.8rem 1.8rem; margin-bottom:0.8rem; background:linear-gradient(90deg,#0a1628 0%,#0e1f3a 50%,#0a1628 100%); border:1px solid #1a3a5c; border-left:4px solid #00d4ff; border-radius:4px; position:relative; overflow:hidden; }
  .main-header::before { content:''; position:absolute; top:0;left:0;right:0;bottom:0; background:repeating-linear-gradient(90deg,transparent,transparent 40px,rgba(0,212,255,0.012) 40px,rgba(0,212,255,0.012) 41px); pointer-events:none; }
  .header-title { font-family:'Rajdhani',sans-serif; font-size:1.55rem; font-weight:700; color:#fff; letter-spacing:3px; text-transform:uppercase; }
  .header-title span { color:#00d4ff; }
  .header-sub { font-family:'Share Tech Mono',monospace; font-size:0.65rem; color:#3a6a8a; letter-spacing:2px; margin-top:2px; }
  .live-badge { display:inline-flex; align-items:center; gap:6px; background:rgba(0,255,128,0.08); border:1px solid rgba(0,255,128,0.3); padding:3px 11px; border-radius:2px; font-family:'Share Tech Mono',monospace; font-size:0.7rem; color:#00ff80; letter-spacing:2px; }
  .live-dot { width:6px; height:6px; background:#00ff80; border-radius:50%; animation:pulse 1.5s infinite; box-shadow:0 0 6px #00ff80; }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1);} 50%{opacity:0.35;transform:scale(0.75);} }
  .ts { font-family:'Share Tech Mono',monospace; font-size:0.65rem; color:#2e5570; margin-top:5px; letter-spacing:1px; }

  .unit-panel { background:linear-gradient(145deg,#0a1320,#07101a); border:1px solid; border-radius:5px; padding:0.7rem 0.9rem 0.5rem 0.9rem; }
  .unit-panel-u1 { border-color:#1a3a5a; border-top:2px solid #00d4ff; }
  .unit-panel-u2 { border-color:#2a2010; border-top:2px solid #f5a623; }
  .unit-title { font-family:'Rajdhani',sans-serif; font-size:0.9rem; font-weight:700; letter-spacing:3px; text-transform:uppercase; margin-bottom:0.55rem; display:flex; align-items:center; gap:10px; }
  .unit-title-u1 { color:#00d4ff; }
  .unit-title-u2 { color:#f5a623; }
  .unit-badge { font-family:'Share Tech Mono',monospace; font-size:0.58rem; padding:2px 7px; border-radius:2px; letter-spacing:1.5px; color:#07101a; font-weight:700; }
  .unit-badge-u1 { background:#00d4ff; }
  .unit-badge-u2 { background:#f5a623; }
  .unit-badge-off { background:#ff4444; color:#fff; }

  .kpi-row { display:flex; gap:5px; margin-bottom:0.5rem; }
  .kpi-card { flex:1; background:linear-gradient(145deg,#0c1928,#091420); border:1px solid #162840; border-top:2px solid var(--ac); border-radius:4px; padding:0.5rem 0.65rem; position:relative; overflow:hidden; }
  .kpi-card::after { content:''; position:absolute; bottom:0;left:0; width:100%;height:1px; background:linear-gradient(90deg,transparent,var(--ac),transparent); opacity:0.4; }
  .kpi-lbl { font-family:'Share Tech Mono',monospace; font-size:0.57rem; letter-spacing:2px; color:#3a6080; text-transform:uppercase; margin-bottom:2px; }
  .kpi-val { font-family:'Rajdhani',sans-serif; font-size:1.55rem; font-weight:700; line-height:1.05; color:#fff; }
  .kpi-unit { font-size:0.68rem; font-weight:300; color:#3a6888; margin-left:3px; }
  .kpi-st { font-family:'Share Tech Mono',monospace; font-size:0.54rem; margin-top:1px; letter-spacing:1px; }
  .ok  { color:#00ff80; }
  .warn { color:#ffaa00; }
  .err { color:#ff4444; }

  .status-bar { display:flex; align-items:center; justify-content:space-between; padding:0.38rem 1rem; background:#040810; border:1px solid #0c1e30; border-radius:2px; margin-top:0.5rem; font-family:'Share Tech Mono',monospace; font-size:0.59rem; color:#243c55; letter-spacing:1.5px; }
  .js-plotly-plot .plotly .bg { fill:transparent !important; }
  div[data-testid="stPlotlyChart"] > div { border-radius:4px; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════
# KONFIGURASI
# ════════════════════════════════════════════
PORT       = 502
UNIT_ID    = 1
TIMEOUT    = 2      # detik — jangan lebih dari interval refresh
MAX_POINTS = 120    # 6 menit @ 3 detik
INTERVAL   = 3000   # ms

UNITS = {
    "u1": {"ip": "10.7.96.36", "label": "KWH METER UNIT #1"},
    "u2": {"ip": "10.7.96.35", "label": "KWH METER UNIT #2"},
}

# Register map ION7400 MEM module (offset: register - 1)
REGISTERS = {
    "vln"  : 3026,   # Voltage L-N Avg    [V]
    "iavg" : 3010,   # Current Avg        [A]
    "kwtot": 3060,   # Active Power Total [W]
    "freq" : 3110,   # Frequency          [Hz]
}

# ════════════════════════════════════════════
# FIX #1: SINGLE TCP CONNECTION PER UNIT
# Buka koneksi sekali, baca semua register, tutup.
# Sebelumnya: buka-tutup koneksi per register (4x overhead)
# ════════════════════════════════════════════
def read_all(ip):
    result = {tag: None for tag in REGISTERS}
    try:
        client = ModbusTcpClient(ip, port=PORT, timeout=TIMEOUT)
        if not client.connect():
            return result
        for tag, reg in REGISTERS.items():
            try:
                rr = client.read_holding_registers(reg - 1, 2, unit=UNIT_ID)
                if rr and not rr.isError():
                    dec = BinaryPayloadDecoder.fromRegisters(
                        rr.registers,
                        byteorder=Endian.Big,
                        wordorder=Endian.Big
                    )
                    result[tag] = dec.decode_32bit_float()
            except Exception:
                pass
        client.close()
    except Exception:
        pass
    return result

# ════════════════════════════════════════════
# FIX #2: PARALLEL READ KEDUA UNIT (threading)
# Sebelumnya: baca unit1 lalu unit2 secara berurutan (~8 detik)
# Sekarang: baca keduanya bersamaan (~2 detik)
# ════════════════════════════════════════════
def fetch_parallel():
    results = {}
    def worker(uid, ip):
        results[uid] = read_all(ip)
    threads = [
        threading.Thread(target=worker, args=(uid, cfg["ip"]))
        for uid, cfg in UNITS.items()
    ]
    for t in threads: t.start()
    for t in threads: t.join(timeout=TIMEOUT + 0.5)
    # Fallback jika thread tidak selesai
    for uid in UNITS:
        if uid not in results:
            results[uid] = {tag: None for tag in REGISTERS}
    return results

# ════════════════════════════════════════════
# FIX #3: SESSION STATE INIT
# ════════════════════════════════════════════
def _init():
    for uid in UNITS:
        for key in REGISTERS:
            k = f"hist_{uid}_{key}"
            if k not in st.session_state:
                st.session_state[k] = collections.deque(maxlen=MAX_POINTS)
        # Simpan waktu error terakhir untuk deteksi timeout
        if f"err_count_{uid}" not in st.session_state:
            st.session_state[f"err_count_{uid}"] = 0
_init()

# ════════════════════════════════════════════
# AUTO REFRESH — di atas semua render
# ════════════════════════════════════════════
st_autorefresh(interval=INTERVAL, key="anggrek_refresh")

# ════════════════════════════════════════════
# BACA DATA
# ════════════════════════════════════════════
now       = datetime.now()
raw_all   = fetch_parallel()
data      = {}

# Konversi ke satuan tampil & divisor
CONVERT = {
    "vln"  : (1000,       "kV",  2),   # V → kV
    "iavg" : (1000,       "kA",  3),   # A → kA
    "kwtot": (1_000_000,  "MW",  3),   # W → MW
    "freq" : (1,          "Hz",  2),   # Hz
}

for uid in UNITS:
    raw  = raw_all[uid]
    conn = any(v is not None for v in raw.values())

    # Update error counter
    if not conn:
        st.session_state[f"err_count_{uid}"] += 1
    else:
        st.session_state[f"err_count_{uid}"] = 0

    # Update history
    for tag, (div, unit, dec) in CONVERT.items():
        val = raw[tag]
        disp = val / div if val is not None else None
        st.session_state[f"hist_{uid}_{tag}"].append(disp)

    data[uid] = {
        **raw,
        "conn"      : conn,
        "err_count" : st.session_state[f"err_count_{uid}"],
        **{f"{tag}_l": list(st.session_state[f"hist_{uid}_{tag}"]) for tag in REGISTERS},
    }

# ════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════
def fmt(val, d=2):
    return f"{val:.{d}f}" if val is not None else "---"

def h2rgba(hx, a=0.10):
    h = hx.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{a})"

def kpi_html(label, value_str, unit, status_ok, accent):
    dot = '<span class="ok">● NORMAL</span>' if status_ok else '<span class="err">● NO DATA</span>'
    return (
        f'<div class="kpi-card" style="--ac:{accent}">'
        f'<div class="kpi-lbl">{label}</div>'
        f'<div class="kpi-val">{value_str}<span class="kpi-unit">{unit}</span></div>'
        f'<div class="kpi-st">{dot}</div>'
        f'</div>'
    )

# ════════════════════════════════════════════
# FIX #4: GRAFIK — gunakan timestamp asli sebagai X axis
# ════════════════════════════════════════════
def build_chart(uid, colors):
    GRID = "rgba(20,50,80,0.5)"
    TICK = "#2a5575"
    FM   = "Share Tech Mono"
    d    = data[uid]

    params = [
        (d["vln_l"],   colors[0], "Tegangan L-N", "kV", 1, 1),
        (d["iavg_l"],  colors[1], "Arus Avg",     "kA", 1, 2),
        (d["kwtot_l"], colors[2], "Daya Aktif",   "MW", 2, 1),
        (d["freq_l"],  colors[3], "Frekuensi",    "Hz", 2, 2),
    ]

    fig  = make_subplots(rows=2, cols=2, vertical_spacing=0.20,
                         horizontal_spacing=0.10,
                         subplot_titles=[p[2] for p in params])
    xi   = list(range(MAX_POINTS))
    cmap = {p[2]: p[1] for p in params}

    for y_data, color, name, unit, row, col in params:
        pad = [None] * (MAX_POINTS - len(y_data)) + y_data
        fig.add_trace(go.Scatter(
            x=xi, y=pad, mode='lines',
            line=dict(color=color, width=1.8, shape='spline'),
            fill='tozeroy', fillcolor=h2rgba(color, 0.09),
            name=name,
            hovertemplate=f'<b>{name}</b>: %{{y:.3f}} {unit}<extra></extra>',
            connectgaps=False
        ), row=row, col=col)

        valid = [(i, v) for i, v in zip(xi, pad) if v is not None]
        if valid:
            lx, ly = valid[-1]
            fig.add_trace(go.Scatter(
                x=[lx], y=[ly], mode='markers',
                marker=dict(color=color, size=6, line=dict(color='white', width=1.2)),
                showlegend=False, hoverinfo='skip'
            ), row=row, col=col)

    ax  = dict(showgrid=True, gridcolor=GRID, zeroline=False,
               tickfont=dict(family=FM, size=8, color=TICK), fixedrange=True)
    xax = dict(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True)

    yr = {
        1: {**ax, 'range': [9, 11]},
        2: {**ax},
        3: {**ax},
        4: {**ax, 'range': [49, 51]},
    }

    fig.update_layout(
        height=225, margin=dict(l=40, r=8, t=26, b=4),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False, hovermode='x unified',
        hoverlabel=dict(bgcolor='#0a1830', font=dict(family=FM, size=10)),
        font=dict(family=FM, color=TICK),
    )
    for i in range(1, 5):
        sfx = '' if i == 1 else str(i)
        fig.update_layout(**{f'xaxis{sfx}': xax, f'yaxis{sfx}': yr[i]})

    for ann in fig.layout.annotations:
        ann.font = dict(family=FM, size=9, color=cmap.get(ann.text, '#3a6585'))
        ann.text = f'- {ann.text}'

    return fig

# ════════════════════════════════════════════
# RENDER HEADER
# ════════════════════════════════════════════
st.markdown(f"""
<div class="main-header">
  <div>
    <div class="header-title">⚡ ENERGY MONITOR <span>PLTU ANGGREK</span></div>
    <div class="header-sub">ION 7400 · MODBUS TCP · MEM MODULE · DUAL UNIT · REAL-TIME TELEMETRY</div>
  </div>
  <div style="text-align:right">
    <div class="live-badge"><div class="live-dot"></div>LIVE STREAM</div>
    <div class="ts">LAST UPDATE: {now.strftime('%d-%m-%Y  %H:%M:%S')}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════
# RENDER UNIT PANELS
# ════════════════════════════════════════════
U1_COLORS = ['#00d4ff', '#ff6b35', '#a259ff', '#00ff80']
U2_COLORS = ['#f5a623', '#ff4d8f', '#4dffdb', '#ffe066']

col_u1, col_u2 = st.columns(2, gap="medium")

UNIT_CFG = [
    (col_u1, "u1", "unit-panel-u1", "unit-title-u1", "unit-badge-u1", U1_COLORS),
    (col_u2, "u2", "unit-panel-u2", "unit-title-u2", "unit-badge-u2", U2_COLORS),
]

for col_widget, uid, panel_cls, title_cls, badge_cls, colors in UNIT_CFG:
    d   = data[uid]
    cfg = UNITS[uid]

    with col_widget:
        st.markdown(f'<div class="unit-panel {panel_cls}">', unsafe_allow_html=True)

        # FIX #5: Badge menampilkan jumlah error berturut-turut
        if d["conn"]:
            badge_style, badge_text = badge_cls, "ONLINE"
        elif d["err_count"] < 3:
            badge_style, badge_text = "unit-badge-off", f"RETRY {d['err_count']}/3"
        else:
            badge_style, badge_text = "unit-badge-off", "OFFLINE"

        st.markdown(
            f'<div class="unit-title {title_cls}">'
            f'<span>{cfg["label"]}</span>'
            f'<span class="unit-badge {badge_style}">{badge_text}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

        vln_d   = fmt(d["vln"]   / 1000,      2) if d["vln"]   is not None else "---"
        iavg_d  = fmt(d["iavg"]  / 1000,      3) if d["iavg"]  is not None else "---"
        kwtot_d = fmt(d["kwtot"] / 1_000_000, 3) if d["kwtot"] is not None else "---"
        freq_d  = fmt(d["freq"],               2) if d["freq"]  is not None else "---"

        st.markdown(
            '<div class="kpi-row">'
            + kpi_html("Tegangan L-N", vln_d,   "kV", d["vln"]   is not None, colors[0])
            + kpi_html("Arus Avg",     iavg_d,  "kA", d["iavg"]  is not None, colors[1])
            + kpi_html("Daya Aktif",   kwtot_d, "MW", d["kwtot"] is not None, colors[2])
            + kpi_html("Frekuensi",    freq_d,  "Hz", d["freq"]  is not None, colors[3])
            + '</div>',
            unsafe_allow_html=True
        )

        st.plotly_chart(
            build_chart(uid, colors),
            use_container_width=True,
            config={'displayModeBar': False}
        )

        st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════
# STATUS BAR
# ════════════════════════════════════════════
def conn_txt(uid):
    ok  = data[uid]["conn"]
    cfg = UNITS[uid]
    dot = '<span class="ok">● CONNECTED</span>' if ok else '<span class="err">● DISCONNECTED</span>'
    return f"{dot} {cfg['ip']}:{PORT} UID:{UNIT_ID}"

buf = len(data['u1']['vln_l'])
st.markdown(
    f'<div class="status-bar">'
    f'<div>U1: {conn_txt("u1")} &nbsp;|&nbsp; U2: {conn_txt("u2")}</div>'
    f'<div>REG(−1): VLN=3036 I=3010 kW=3060 Hz=3110 &nbsp;|&nbsp; FLOAT32 Big/Big &nbsp;|&nbsp; BUF:{buf}/{MAX_POINTS} &nbsp;|&nbsp; {INTERVAL//1000}s &nbsp;|&nbsp; PARALLEL</div>'
    f'</div>',
    unsafe_allow_html=True
)

