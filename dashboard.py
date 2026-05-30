"""
Dashboard de análise pós-run da pipeline de testes V2X (Eclipse MOSAIC + SUMO).
Autoria: Gonçalo Ferreira, Gustavo Castro, Matilde Oliveira
Mestrado EI - Novos Paradigmas de Rede.
"""

import math
import os
import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------- #
# Configuração da página e Tema
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="V2X Analytics | Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injeção de CSS para um Design Dark Premium
st.markdown("""
<style>
    /* Estilo das métricas (Cartões Escuros) */
    div[data-testid="metric-container"] {
        background-color: #181825;
        border: 1px solid #313244;
        border-left: 5px solid #E63946;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 2px 4px 10px rgba(0,0,0,0.2);
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 2px 6px 15px rgba(0,0,0,0.4);
    }
    div[data-testid="metric-container"] label {
        color: #A6ADC8 !important;
        font-weight: bold;
        font-size: 1.1rem;
    }
    div[data-testid="metric-container"] div[data-testid="metric-value"] {
        color: #FFFFFF !important;
        font-size: 1.8rem;
    }
    /* Ocultar delta na aba Live Demo para ficar mais limpo */
    .hide-delta div[data-testid="metric-container"] div[data-testid="stMetricDelta"] {
        display: none;
    }
    /* Títulos principais adaptados ao tema base */
    h1, h2, h3, h4 {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        color: #FFFFFF;
    }
</style>
""", unsafe_allow_html=True)

# Caminhos absolutos
RESULTADOS_CSV = "/home/netsim/tpnpr/Resultados_Pipeline.csv"
SIGNIFICANCIA_CSV = "/home/netsim/tpnpr/Significancia_Pipeline.csv"
LIVE_JSON_PATH = "/home/netsim/tpnpr/results/run_test/metrics_test.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Paleta de Cores (Contraste para Fundo Escuro)
COR_COM = "#E63946"   # Vermelho (Sistema V2X)
COR_SEM = "#457B9D"   # Azul claro (Baseline)
PALETA_V2X = ["#457B9D", "#E63946", "#F4A261", "#2A9D8F", "#A8DADC"]

# Fundos dos Gráficos Escuros
BG_CHART = "#181825"
GRID_COLOR = "#313244"
TEXT_COLOR = "#CDD6F4"

# Dicionários e Rótulos
DESC_TESTES = {1: "T1 (40% Coop)", 2: "T2 (25% Perfis)", 3: "T3 (50% Coop)", 4: "T4 (100% Coop)"}
ROTULOS_METRICAS = {
    "tempoMedioViagem_real": "Tempo Médio (s)", "tempoViagem_P95_real": "Tempo P95 (s)",
    "throughput_vps": "Throughput (v/s)", "throughput_total": "Throughput Total",
    "velMediaGargalo_kmh": "Vel Gargalo (km/h)", "co2Medio_real_g": "CO2 Médio (g)",
    "suppressionRatio": "Rácio de Supressão", "totalDenmsReceived": "DENMs Recebidas",
    "totalCamsReceived": "CAMs Recebidas", "combustivelMedio_real_ml": "Combustível (ml)"
}

def rotulo_metrica(m: str) -> str: return ROTULOS_METRICAS.get(m, m)

# --------------------------------------------------------------------------- #
# Leitura de dados CSV
# --------------------------------------------------------------------------- #
@st.cache_data
def carregar_csv(caminho: str) -> pd.DataFrame:
    return pd.read_csv(caminho)

faltam = []
if not os.path.exists(RESULTADOS_CSV): faltam.append("Resultados_Pipeline.csv")
if faltam:
    st.error(f"⚠️ Ficheiros base não encontrados: {faltam}. Corre a pipeline primeiro.")
    st.stop()

df = carregar_csv(RESULTADOS_CSV)
df_sig = carregar_csv(SIGNIFICANCIA_CSV) if os.path.exists(SIGNIFICANCIA_CSV) else None

# --------------------------------------------------------------------------- #
# Motores de Gráficos (Design Escuro e Títulos Brancos)
# --------------------------------------------------------------------------- #
def aplicar_estilo_layout(fig, titulo, eixo_y, barmode="group"):
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=18, family="Arial", color="#FFFFFF"), x=0.02),
        barmode=barmode,
        xaxis_title="", 
        yaxis_title=dict(text=eixo_y, font=dict(color=TEXT_COLOR)),
        xaxis=dict(tickfont=dict(color=TEXT_COLOR)),
        yaxis=dict(tickfont=dict(color=TEXT_COLOR), showgrid=True, gridwidth=1, gridcolor=GRID_COLOR, zeroline=True, zerolinecolor="#555555"),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1, font=dict(color=TEXT_COLOR), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=40, r=20, t=80, b=30),
        plot_bgcolor=BG_CHART, paper_bgcolor=BG_CHART,
        height=380,
        hovermode="x unified"
    )
    return fig

def _serie_por_teste(df: pd.DataFrame, metrica: str, rsu: str):
    sub = df[(df["metrica"] == metrica) & (df["rsu"] == rsu)].sort_values("teste")
    testes = [DESC_TESTES.get(int(t), f"T{int(t)}") for t in sub["teste"]]
    media = sub["Media"].tolist()
    low = (sub["Media"] - sub["IC95_low"]).clip(lower=0).tolist()
    high = (sub["IC95_high"] - sub["Media"]).clip(lower=0).tolist()
    return testes, media, low, high

def grafico_linha_tendencia(df: pd.DataFrame, metrica: str, titulo: str, eixo_y: str):
    fig = go.Figure()
    for rsu, cor, nome in (("sem", COR_SEM, "Baseline (Sem RSU)"), ("com", COR_COM, "Sistema V2X (Com RSU)")):
        testes, media, low, high = _serie_por_teste(df, metrica, rsu)
        if not media: continue
        fig.add_trace(go.Scatter(
            name=nome, x=testes, y=media, mode='lines+markers',
            marker=dict(color=cor, size=10, symbol="circle", line=dict(width=1, color="white")),
            line=dict(width=3, color=cor),
            error_y=dict(type="data", symmetric=False, array=high, arrayminus=low, color=cor, thickness=1.5, width=4)
        ))
    return aplicar_estilo_layout(fig, titulo, eixo_y)

def grafico_barras_com_erros(df: pd.DataFrame, metrica: str, titulo: str, eixo_y: str):
    fig = go.Figure()
    for rsu, cor, nome in (("sem", COR_SEM, "Baseline"), ("com", COR_COM, "Sistema V2X")):
        testes, media, low, high = _serie_por_teste(df, metrica, rsu)
        if not media: continue
        fig.add_trace(go.Bar(
            name=nome, x=testes, y=media, marker_color=cor, marker_line_width=0, opacity=0.95,
            error_y=dict(type="data", symmetric=False, array=high, arrayminus=low, color="#FFFFFF", thickness=1.5)
        ))
    return aplicar_estilo_layout(fig, titulo, eixo_y)

def grafico_area(df: pd.DataFrame, metrica: str, titulo: str, eixo_y: str):
    fig = go.Figure()
    testes, media, _, _ = _serie_por_teste(df, metrica, "com")
    if media:
        fig.add_trace(go.Scatter(
            name=rotulo_metrica(metrica), x=testes, y=media, mode='lines+markers',
            fill='tozeroy', fillcolor="rgba(230, 57, 70, 0.2)",
            line=dict(color=COR_COM, width=3), marker=dict(size=8, color=COR_COM)
        ))
    return aplicar_estilo_layout(fig, titulo, eixo_y)

def valor_medio(df: pd.DataFrame, metrica: str, rsu: str, teste=None):
    if teste:
        sub = df[(df["metrica"] == metrica) & (df["rsu"] == rsu) & (df["teste"] == teste)]
    else:
        sub = df[(df["metrica"] == metrica) & (df["rsu"] == rsu)]
    return float(sub["Media"].mean()) if not sub.empty else None

def carregar_imagem(nomes_possiveis):
    for nome in nomes_possiveis:
        caminho = os.path.join(BASE_DIR, nome)
        if os.path.exists(caminho): return caminho
    return None

# --------------------------------------------------------------------------- #
# Interface UI (Barra Lateral)
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("## ⚙️ Painel de Controlo")
    
    st.markdown("#### Modo de Operação")
    modo_operacao = st.radio(
        "Selecione o Modo de Visualização",
        ["📊 Análise Histórica", "🔴 Demonstração"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("#### Carga de Tráfego")
    cenarios_disp = sorted(df["cenario"].unique())
    cenario = st.selectbox(
        "Selecione o Cenário",
        cenarios_disp,
        format_func=lambda c: "Cenário 1" if int(c) == 1 else "Cenário 2",
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("### Dashboard realizada por:")
    for nome, imgs in [("Gonçalo Ferreira", ["goncalo.png", "foto_goncalo.png"]), 
                       ("Gustavo Castro", ["gustavo.png", "foto_gustavo.png"]), 
                       ("Matilde Oliveira", ["matilde.png", "foto_matilde.png"])]:
        col_img, col_txt = st.columns([1, 2.5])
        with col_img:
            img_path = carregar_imagem(imgs)
            # CORREÇÃO AQUI: Substituímos o use_column_width=True por uma largura fixa ajustada à coluna
            if img_path: st.image(img_path, width=80)
        with col_txt:
            st.markdown(f"**{nome}**")
        st.markdown("") 
        
    st.markdown("---")
    st.caption("Mestrado em Engenharia Informática Universidade do Minho")

df_c = df[df["cenario"] == cenario].copy()

# --------------------------------------------------------------------------- #
# RENDERIZAÇÃO: ANÁLISE HISTÓRICA (COMPACTA)
# --------------------------------------------------------------------------- #
if modo_operacao == "📊 Análise Histórica":
    st.title("📊 Análise de Desempenho V2X")
    st.markdown("Avaliação estocástica baseada em simulações com ambiente **Eclipse MOSAIC + SUMO**.")
    
    st.markdown(f"### 🎯 Indicadores Médios")
    
    def kpi(coluna, label, metrica, unidade="", menor_melhor=True, casas=1):
        com = valor_medio(df_c, metrica, "com")
        sem = valor_medio(df_c, metrica, "sem")
        if com is None or sem is None: return
        delta = com - sem
        coluna.metric(label, f"{com:.{casas}f}{unidade}", delta=f"{delta:+.{casas}f} vs Base", delta_color="inverse" if menor_melhor else "normal")

    c1, c2, c3, c4 = st.columns(4)
    kpi(c1, "Tempo P95 (Extremos)", "tempoViagem_P95_real", "s", menor_melhor=True)
    kpi(c2, "Tempo Médio", "tempoMedioViagem_real", "s", menor_melhor=True)
    kpi(c3, "Throughput", "throughput_vps", " v/s", menor_melhor=False, casas=2)
    kpi(c4, "Supressão DBCF", "suppressionRatio", "", menor_melhor=False, casas=2)

    st.markdown("---")
    st.markdown("### 📈 Visualização Compacta de Tráfego e Rede")
    
    g1, g2 = st.columns(2)
    with g1:
        st.plotly_chart(grafico_linha_tendencia(df_c, "tempoViagem_P95_real", "Evolução do Tempo P95 (Extremos)", "Tempo (s)"), width="stretch")
        st.plotly_chart(grafico_barras_com_erros(df_c, "co2Medio_real_g", "Emissões de CO2", "CO2 (g)"), width="stretch")
        st.plotly_chart(grafico_area(df_c, "suppressionRatio", "Rácio de Supressão (DBCF)", "Rácio (0-1)"), width="stretch")
        
    with g2:
        st.plotly_chart(grafico_linha_tendencia(df_c, "velMediaGargalo_kmh", "Velocidade no Gargalo", "km/h"), width="stretch")
        st.plotly_chart(grafico_barras_com_erros(df_c, "tempoMedioViagem_real", "Tempo Médio Global", "Tempo (s)"), width="stretch")
        
        # Gráfico Empilhado de Mensagens
        fig_msgs = go.Figure()
        testes, cams, _, _ = _serie_por_teste(df_c, "totalCamsReceived", "com")
        _, denms, _, _ = _serie_por_teste(df_c, "totalDenmsReceived", "com")
        if cams and denms:
            fig_msgs.add_trace(go.Bar(name="CAMs", x=testes, y=cams, marker_color=PALETA_V2X[0]))
            fig_msgs.add_trace(go.Bar(name="DENMs", x=testes, y=denms, marker_color=COR_COM))
            aplicar_estilo_layout(fig_msgs, "Composição de Tráfego V2X", "Qtd Mensagens", barmode="stack")
            st.plotly_chart(fig_msgs, width="stretch")

    st.markdown("---")
    with st.expander("📐 Ver Tabela de Validação Estatística (Teste de Welch)"):
        if df_sig is not None:
            sig_c = df_sig[df_sig["cenario"] == cenario].copy()
            sig_c["Significativo (p<0.05)"] = sig_c["welch_p"].apply(lambda p: "✅ Sim" if (isinstance(p, float) and p < 0.05) else "❌ Não")
            sig_c["Métrica"] = sig_c["metrica"].apply(rotulo_metrica)
            st.dataframe(sig_c[["teste", "Métrica", "media_com", "media_sem", "welch_p", "Significativo (p<0.05)"]], width="stretch", hide_index=True)

# --------------------------------------------------------------------------- #
# RENDERIZAÇÃO: DEMONSTRAÇÃO AO VIVO (VALORES LIMPOS)
# --------------------------------------------------------------------------- #
elif modo_operacao == "🔴 Demonstração":
    st.markdown("<h1 style='color: #E63946;'>🔴 Execução em Tempo Real</h1>", unsafe_allow_html=True)
    st.markdown("Resultados extraídos instantaneamente da última simulação (single run). Atualiza a página quando o script de simulação no terminal concluir.")

    if os.path.exists(LIVE_JSON_PATH):
        with open(LIVE_JSON_PATH, "r") as f:
            try:
                live_data = json.load(f)
            except:
                live_data = {}
            
        trips = live_data.get("trips", {})
        btnk = live_data.get("bottleneck", {})
        v2x = live_data.get("v2x", {})
        queue = live_data.get("queue", {})
        
        l_speed = btnk.get("avg_speed_kmh", 0)
        l_co2 = trips.get("avg_co2_g", 0)
        l_time = trips.get("avg_trip_time_s", 0)
        l_throughput = live_data.get("throughput", {}).get("avg_throughput_vps", 0)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📊 Desempenho Físico (Tráfego & Emissões)")
        
        st.markdown('<div class="hide-delta">', unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tempo Médio de Viagem", f"{l_time:.2f} s")
        c2.metric("Velocidade no Gargalo", f"{l_speed:.2f} km/h")
        c3.metric("Emissões de CO2", f"{l_co2:.2f} g")
        c4.metric("Throughput da Via", f"{l_throughput:.2f} v/s")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("### 📶 Dados da Rede V2X e Simulador")
        st.markdown('<div class="hide-delta">', unsafe_allow_html=True)
        
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Total de Mensagens V2X", f"{v2x.get('totalV2xMessages', 0)}")
        c6.metric("Veículos Processados", f"{trips.get('total_vehicles', 0)}")
        c7.metric("Fila Máxima Registada", f"{queue.get('max_queue_length_vehicles', 0)} veíc.")
        c8.metric("Duração da Simulação", f"{live_data.get('throughput', {}).get('simulation_duration_s', 0)} s")
        
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.warning(f"O ficheiro de métricas ao vivo não foi detetado.")
        st.info("A aguardar que o MOSAIC conclua a execução...")