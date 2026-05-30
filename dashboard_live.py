"""
Dashboard V2X em Tempo Real — Demonstração

Mostra as métricas de uma simulação MOSAIC/SUMO a evoluir ENQUANTO esta corre.
Lê o ficheiro metrics_live.json escrito pelas RSUs (Java) a cada ciclo (~2s).

Autoria: Goncalo Ferreira, Gustavo Castro, Matilde Oliveira

Como correr:
    /home/netsim/opt/tpnpr/.venv/bin/streamlit run dashboard_live.py
"""

import json
import os
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Configuracao da pagina
# ---------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="V2X — Tempo Real", page_icon="🔴")

LIVE_FILE = os.environ.get("NPR_LIVE_FILE", "/home/netsim/opt/tpnpr/metrics_live.json")

# Cores fixas por RSU para manter consistencia entre refreshs
CORES_RSU = {
    "rsu_zona1": "#1f77b4",
    "rsu_zona2": "#ff7f0e",
    "rsu_zona3": "#2ca02c",
}


def cor_rsu(nome):
    return CORES_RSU.get(nome, "#888888")


# ---------------------------------------------------------------------------
# Sidebar — controlos
# ---------------------------------------------------------------------------
st.sidebar.header("⚙️ Controlos")

intervalo_s = st.sidebar.slider(
    "Intervalo de atualizacao (s)", min_value=1, max_value=10, value=2
)
pausa = st.sidebar.checkbox("⏸️ Pausar atualizacao", value=False)

# ---------------------------------------------------------------------------
# Auto-refresh (~2s por defeito)
# ---------------------------------------------------------------------------
if not pausa:
    try:
        from streamlit_autorefresh import st_autorefresh

        st_autorefresh(interval=intervalo_s * 1000, key="live")
    except Exception:
        # Fallback simples por meta-refresh do HTML
        st.markdown(
            f'<meta http-equiv="refresh" content="{intervalo_s}">',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Titulo
# ---------------------------------------------------------------------------
st.title("🔴 Dashboard V2X em Tempo Real — Demonstracao")


# ---------------------------------------------------------------------------
# Leitura dos dados (SEM cache, a cada refresh)
# ---------------------------------------------------------------------------
def ler_metricas(caminho):
    """Le o JSON ao vivo. Devolve (dados, erro).

    Trata ficheiro inexistente e JSON meio-escrito (escrita concorrente do Java).
    """
    if not os.path.exists(caminho):
        return None, "inexistente"
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f), None
    except json.JSONDecodeError:
        # Ficheiro a ser escrito neste exato momento
        return None, "incompleto"
    except OSError:
        return None, "incompleto"


dados, erro = ler_metricas(LIVE_FILE)

# ---------------------------------------------------------------------------
# Sidebar — estado da simulacao
# ---------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("📡 Estado")

ativa = False
if os.path.exists(LIVE_FILE):
    idade = time.time() - os.path.getmtime(LIVE_FILE)
    ativa = idade <= 10
    if ativa:
        st.sidebar.success("🟢 simulacao ativa")
    else:
        st.sidebar.info("⚪ inativa/terminada")
    st.sidebar.caption(f"Ultima escrita ha {idade:.0f}s")
else:
    st.sidebar.info("⚪ inativa/terminada")

st.sidebar.caption(f"Ficheiro: `{LIVE_FILE}`")

st.sidebar.markdown("---")
st.sidebar.caption(
    "👥 **Autoria**  \nGoncalo Ferreira  \nGustavo Castro  \nMatilde Oliveira"
)

# ---------------------------------------------------------------------------
# Expander — como usar na demo
# ---------------------------------------------------------------------------
with st.expander("ℹ️ Como usar na demo"):
    st.markdown(
        """
1. **Correr a simulacao** (idealmente com **SUMO-GUI**) usando o JAR atual.
   As RSUs escrevem o ficheiro `metrics_live.json` automaticamente no caminho
   default (`/home/netsim/opt/tpnpr/metrics_live.json`), ou num caminho
   personalizado via `-Dnpr.live.out=/caminho/metrics_live.json`.
2. **Abrir este dashboard:**
   ```
   /home/netsim/opt/tpnpr/.venv/bin/streamlit run dashboard_live.py
   ```
   (Para apontar a outro ficheiro: `NPR_LIVE_FILE=/caminho/metrics_live.json`.)
3. O dashboard **atualiza-se sozinho a cada ~2s** enquanto a simulacao corre.
   Pode-se ajustar o intervalo ou pausar na barra lateral.
"""
    )

# ---------------------------------------------------------------------------
# Sem dados ainda
# ---------------------------------------------------------------------------
snapshots = (dados or {}).get("snapshots") or []
if not snapshots:
    st.info("⏳ A espera de dados da simulacao...")
    if erro == "inexistente":
        st.caption(f"Ainda nao existe `{LIVE_FILE}`. Inicie a simulacao.")
    elif erro == "incompleto":
        st.caption("Ficheiro a ser escrito neste momento — aguarde o proximo ciclo.")
    st.stop()

# ---------------------------------------------------------------------------
# DataFrame
# ---------------------------------------------------------------------------
df = pd.DataFrame(snapshots)

# Garantir colunas esperadas (robustez)
for col, default in [
    ("t", 0.0),
    ("rsu", "?"),
    ("densidade", 0),
    ("velMediaGargalo_kmh", 0.0),
    ("avisoAtivo", False),
    ("totalCamsReceived", 0),
    ("totalDenmsReceived", 0),
    ("totalAlertsTriggered", 0),
    ("totalRetransmissions", 0),
    ("totalSuppressions", 0),
]:
    if col not in df.columns:
        df[col] = default

df = df.sort_values("t").reset_index(drop=True)

t_atual = df["t"].max()
df_atual = df[df["t"] == t_atual]

# ---------------------------------------------------------------------------
# KPIs de topo (estado ATUAL)
# ---------------------------------------------------------------------------
lastUpdate = (dados or {}).get("lastUpdate_s", t_atual)

dens_atual = df_atual["densidade"].mean()
vel_atual = df_atual["velMediaGargalo_kmh"].mean()
aviso_atual = bool(df_atual["avisoAtivo"].any())
# Contadores acumulados globais -> usar o maximo do instante mais recente
cams_atual = int(df_atual["totalCamsReceived"].max())
denms_atual = int(df_atual["totalDenmsReceived"].max())

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("⏱️ Tempo simulacao", f"{lastUpdate:.0f} s")
c2.metric("🚗 Densidade atual", f"{dens_atual:.1f}", help="Media entre RSUs no t mais recente")
c3.metric("🏁 Vel. gargalo", f"{vel_atual:.1f} km/h")
if aviso_atual:
    c4.metric("⚠️ Aviso", "ATIVO")
    c4.markdown(
        "<span style='color:#d62728;font-weight:bold'>● ATIVO</span>",
        unsafe_allow_html=True,
    )
else:
    c4.metric("✅ Aviso", "INATIVO")
    c4.markdown(
        "<span style='color:#2ca02c;font-weight:bold'>● INATIVO</span>",
        unsafe_allow_html=True,
    )
c5.metric("📨 DENMs recebidos", f"{denms_atual}")
c6.metric("📡 CAMs recebidos", f"{cams_atual}")

st.markdown("---")


# ---------------------------------------------------------------------------
# Helper — sombrear periodos com aviso ativo
# ---------------------------------------------------------------------------
def sombrear_avisos(fig, df_in):
    """Adiciona faixas verticais nos instantes t em que ALGUMA RSU tem aviso ativo."""
    aviso_por_t = df_in.groupby("t")["avisoAtivo"].any()
    ts_aviso = list(aviso_por_t[aviso_por_t].index)
    if not ts_aviso:
        return
    # Largura tipica de um passo
    ts_unicos = sorted(df_in["t"].unique())
    passo = (ts_unicos[1] - ts_unicos[0]) if len(ts_unicos) > 1 else 1.0
    primeiro = True
    for ti in ts_aviso:
        fig.add_vrect(
            x0=ti - passo / 2,
            x1=ti + passo / 2,
            fillcolor="rgba(214,39,40,0.12)",
            line_width=0,
            layer="below",
            annotation_text="aviso" if primeiro else None,
            annotation_position="top left",
        )
        primeiro = False


# ---------------------------------------------------------------------------
# Grafico 1 — Velocidade no gargalo (uma linha por RSU)
# ---------------------------------------------------------------------------
st.subheader("🏁 Velocidade media no gargalo ao longo do tempo")
fig_vel = go.Figure()
for rsu, sub in df.groupby("rsu"):
    sub = sub.sort_values("t")
    fig_vel.add_trace(
        go.Scatter(
            x=sub["t"],
            y=sub["velMediaGargalo_kmh"],
            mode="lines+markers",
            name=rsu,
            line=dict(color=cor_rsu(rsu)),
        )
    )
sombrear_avisos(fig_vel, df)
fig_vel.update_layout(
    xaxis_title="Tempo (s)",
    yaxis_title="Velocidade (km/h)",
    height=360,
    margin=dict(t=30, b=10),
    legend_title="RSU",
)
st.plotly_chart(fig_vel, use_container_width=True)

# ---------------------------------------------------------------------------
# Grafico 2 — Densidade (uma linha por RSU)
# ---------------------------------------------------------------------------
st.subheader("🚗 Densidade ao longo do tempo")
fig_dens = go.Figure()
for rsu, sub in df.groupby("rsu"):
    sub = sub.sort_values("t")
    fig_dens.add_trace(
        go.Scatter(
            x=sub["t"],
            y=sub["densidade"],
            mode="lines+markers",
            name=rsu,
            line=dict(color=cor_rsu(rsu)),
        )
    )
sombrear_avisos(fig_dens, df)
fig_dens.update_layout(
    xaxis_title="Tempo (s)",
    yaxis_title="Densidade (veiculos)",
    height=360,
    margin=dict(t=30, b=10),
    legend_title="RSU",
)
st.plotly_chart(fig_dens, use_container_width=True)

# ---------------------------------------------------------------------------
# Grafico 3 — Mensagens V2X acumuladas (CAMs e DENMs)
# Contadores sao globais acumulados -> usar o maximo entre RSUs por t
# ---------------------------------------------------------------------------
st.subheader("📡 Mensagens V2X acumuladas ao longo do tempo")
agg = (
    df.groupby("t")
    .agg(
        cams=("totalCamsReceived", "max"),
        denms=("totalDenmsReceived", "max"),
        alerts=("totalAlertsTriggered", "max"),
    )
    .reset_index()
    .sort_values("t")
)
fig_msg = go.Figure()
fig_msg.add_trace(
    go.Scatter(x=agg["t"], y=agg["cams"], mode="lines+markers", name="CAMs",
               line=dict(color="#1f77b4"))
)
fig_msg.add_trace(
    go.Scatter(x=agg["t"], y=agg["denms"], mode="lines+markers", name="DENMs",
               line=dict(color="#d62728"))
)
fig_msg.add_trace(
    go.Scatter(x=agg["t"], y=agg["alerts"], mode="lines+markers", name="Alertas",
               line=dict(color="#ff7f0e", dash="dot"))
)
fig_msg.update_layout(
    xaxis_title="Tempo (s)",
    yaxis_title="Mensagens (acumuladas)",
    height=360,
    margin=dict(t=30, b=10),
    legend_title="Tipo",
)
st.plotly_chart(fig_msg, use_container_width=True)

st.caption(
    f"📦 numSnapshots={dados.get('numSnapshots', len(snapshots))} | "
    f"instante atual t={t_atual:.0f}s | "
    f"refresh a cada {intervalo_s}s" + ("  (PAUSADO)" if pausa else "")
)
