import streamlit as st
import pandas as pd
import glob
import os
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="V2X Dashboard", layout="wide", page_icon="📡")

# Carregar dados em cache
@st.cache_data
def carregar_dados():
    caminho_pasta = "Resultados_30runs"
    padrao_busca = os.path.join(caminho_pasta, "Resultados_Cenario*.csv")
    ficheiros = glob.glob(padrao_busca)
    
    if not ficheiros:
        return pd.DataFrame()

    mapa_cooperacao = {'1': '0% (T1)', '2': '25% (T2)', '3': '50% (T3)', '4': '100% (T4)'}
    dados = []
    
    for file in ficheiros:
        nome_base = os.path.basename(file).replace('.csv', '')
        partes = nome_base.split('_')
        try:
            cenario_str = partes[1].lower() 
            rsu_str = partes[2].lower()     
            teste_str = partes[3]           
            
            cenario_label = 'Cenário 1 (Moderado)' if '1' in cenario_str else 'Cenário 2 (Saturado)'
            rsu_label = 'Sem RSU' if 'sem' in rsu_str else 'Com RSU'
            taxa_label = mapa_cooperacao[teste_str]
            grupo = f"{cenario_label} - {rsu_label}"

            df_temp = pd.read_csv(file, index_col=0)
            
            dados.append({
                'Cenário': cenario_label,
                'RSU': rsu_label,
                'Grupo': grupo,
                'Teste': int(teste_str),
                'Taxa Cooperação': taxa_label,
                'Trip_Time': df_temp.loc['Trip_Time_Avg', 'Média'],
                'P95': df_temp.loc['P95', 'Média'],
                'Queue_Max': df_temp.loc['Queue_Max_M', 'Média'],
                'Queue_Duration': df_temp.loc['Queue_Duration_S', 'Média'],
                'Throughput': df_temp.loc['Throughput', 'Média'],
                'V2X_Efficiency': df_temp.loc['V2X_Efficiency', 'Média'],
                'CO2': df_temp.loc['CO2_Avg', 'Média'],
                'Speed': df_temp.loc['Speed_Bottleneck', 'Média']
            })
        except:
            pass
    return pd.DataFrame(dados).sort_values(by=['Cenário', 'RSU', 'Teste'])

df = carregar_dados()

# Cabeçalho do Dashboard
st.title(" Dashboard de Gestão Cooperativa de Tráfego em Zona de Obras (V2X)")

if df.empty:
    st.error("Nenhum ficheiro CSV encontrado! Garante que a pasta 'Resultados_30runs' existe na raiz do projeto e contém os ficheiros.")
else:
    # Barra lateral de Filtros e Autoria
    st.sidebar.header("Painel de Controlo")
    cenario_selecionado = st.sidebar.radio("Selecione o Cenário de Teste:", df['Cenário'].unique())
    
    # Secção de Autoria
    st.sidebar.markdown("---")
    st.sidebar.subheader("Dashboard realizado por:")
    
    # Gonçalo
    col_img1, col_txt1 = st.sidebar.columns([1, 2.5])
    with col_img1:
        if os.path.exists("goncalo.png"): st.image("goncalo.png", use_container_width=True)
        elif os.path.exists("foto_goncalo.png"): st.image("foto_goncalo.png", use_container_width=True)
    with col_txt1:
        st.markdown("**Gonçalo Ferreira**")
        
    st.sidebar.markdown("") 
    
    # Gustavo
    col_img2, col_txt2 = st.sidebar.columns([1, 2.5])
    with col_img2:
        if os.path.exists("gustavo.png"): st.image("gustavo.png", use_container_width=True)
        elif os.path.exists("foto_gustavo.png"): st.image("foto_gustavo.png", use_container_width=True)
    with col_txt2:
        st.markdown("**Gustavo Castro**")

        
    st.sidebar.markdown("") 
        
    # Matilde
    col_img3, col_txt3 = st.sidebar.columns([1, 2.5])
    with col_img3:
        if os.path.exists("matilde.png"): st.image("matilde.png", use_container_width=True)
        elif os.path.exists("foto_matilde.png"): st.image("foto_matilde.png", use_container_width=True)
    with col_txt3:
        st.markdown("**Matilde Oliveira**")
        
    st.sidebar.markdown("---")
    st.sidebar.caption("Mestrado em Engenharia Informática")
    st.sidebar.caption("Novos Paradigmas de Rede")

    # Painel Principal - Gráficos
    df_filtrado = df[df['Cenário'] == cenario_selecionado]
    df_com_rsu = df_filtrado[df_filtrado['RSU'] == 'Com RSU']
    
    st.subheader(f"Métricas de Desempenho - {cenario_selecionado}")
    
    # Extração de valores para métricas do topo
    base = df_filtrado[(df_filtrado['RSU'] == 'Sem RSU') & (df_filtrado['Teste'] == 1)].iloc[0]
    best = df_com_rsu[df_com_rsu['Teste'] == 4].iloc[0]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Velocidade Alvo (100% Coop)", f"{best['Speed']:.1f} km/h", f"{best['Speed'] - base['Speed']:.1f} km/h")
    col2.metric("CO2 Emitido", f"{best['CO2']:.1f} g", f"{best['CO2'] - base['CO2']:.1f} g", delta_color="inverse")
    col3.metric("Tempo Viagem P95", f"{best['P95']:.1f} s", f"{best['P95'] - base['P95']:.1f} s", delta_color="inverse")
    col4.metric("Throughput", f"{best['Throughput']:.2f} v/s", f"{best['Throughput'] - base['Throughput']:.2f} v/s")

    st.markdown("---")

    # Gráficos Plotly
    col_a, col_b = st.columns(2)
    
    with col_a:
        fig_speed = px.line(df_filtrado, x='Taxa Cooperação', y='Speed', color='RSU', markers=True,
                            title='Convergência de Velocidade na Zona Crítica',
                            labels={'Speed': 'Velocidade Média (km/h)'},
                            color_discrete_sequence=['#E63946', '#1D3557'])
        fig_speed.add_hline(y=30, line_dash="dash", line_color="red", annotation_text="Setpoint RSU (30 km/h)")
        fig_speed.update_layout(hovermode="x unified")
        st.plotly_chart(fig_speed, use_container_width=True)
        
    with col_b:
        fig_co2 = px.bar(df_filtrado, x='Taxa Cooperação', y='CO2', color='RSU', barmode='group',
                         title='Emissões Médias de CO2',
                         labels={'CO2': 'CO2 (g/veículo)'},
                         color_discrete_sequence=['#E63946', '#2A9D8F'])
        st.plotly_chart(fig_co2, use_container_width=True)

    col_c, col_d = st.columns(2)
    
    with col_c:
        fig_queue = px.line(df_com_rsu, x='Taxa Cooperação', y='Queue_Max', markers=True,
                            title='Extensão Máxima da Fila',
                            labels={'Queue_Max': 'Comprimento (metros)'},
                            color_discrete_sequence=['#E76F51'])
        st.plotly_chart(fig_queue, use_container_width=True)
        
    with col_d:
        fig_v2x = px.bar(df_com_rsu, x='Taxa Cooperação', y='V2X_Efficiency', 
                         title='Carga no Canal Rádio (Flooding)',
                         labels={'V2X_Efficiency': 'Eficiência V2X (Menor = Melhor)'},
                         color_discrete_sequence=['#457B9D'])
        st.plotly_chart(fig_v2x, use_container_width=True)