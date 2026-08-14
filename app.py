import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt
import os
import json
import re
import google.generativeai as genai
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# Configuração da página
st.set_page_config(page_title="Heatmap de Estudos", layout="wide")
st.title("📚 Meu Painel de Estudos com IA (Petrobras - Ênfase 12)")

# ==========================================
# VARIÁVEIS DE SESSÃO E CONEXÕES
# ==========================================
if 'timer_rodando' not in st.session_state:
    st.session_state.timer_rodando = False
    st.session_state.inicio_timer = None
    st.session_state.horas_cronometradas = 0.0

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
URL_PLANILHA = st.secrets["spreadsheet"]

# Conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # ttl=0 obriga a ler a planilha em tempo real sempre
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet="Página1", ttl=0)
        # Limpa linhas vazias caso o Sheets crie acidentalmente
        df = df.dropna(subset=["Data", "Assunto"])
        return df
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return pd.DataFrame(columns=["Data", "Meta", "Categoria", "Assunto", "Horas"])

df = carregar_dados()

def classificar_com_ia(texto_estudo, horas_padrao, api_key):
    if not api_key:
        return [{"Meta": "Sem Meta", "Categoria": "Geral (Sem IA)", "Assunto": texto_estudo, "Horas": horas_padrao}]
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3.5-flash')
        
        prompt = f"""
        Você é um classificador rigoroso de dados para o cronograma de 60 Metas do concurso da Petrobras (Ênfase 12: Eletrônica).
        Sua missão é ler o que o usuário estudou, separar os assuntos e classificá-los EXATAMENTE de acordo com o mapeamento oficial abaixo.

        Entrada do usuário: "{texto_estudo}"

        === CRONOGRAMA OFICIAL (USE ESTAS REFERÊNCIAS PARA A "Meta" E A "Categoria") ===
        [PORTUGUÊS - Categoria: PORT]
        Metas 01 a 03: Fonologia, Acentuação Gráfica, Ortografia, Significação das Palavras, Hífen.
        Metas 04 a 18: Estrutura e Formação das Palavras, Morfologia (Substantivos, Artigos, Conjunções, Preposição, Numerais, Interjeição, Adjetivos, Pronomes, Verbos, Advérbios).
        Metas 19 a 24: Funções Sintáticas (Que, Se), Sintaxe Período Simples (Orações).
        Metas 25 a 30: Sintaxe Período Composto (Coordenação, Subordinadas, Adjetivas, Adverbiais).
        Metas 31 a 34: Regência Verbal e Nominal, Orações Reduzidas.
        Metas 37 a 42: Concordância Verbal e Nominal, Crase, Colocação Pronominal.
        Metas 43 a 45: Pontuação, Uso dos Porquês, Vozes Verbais.
        Metas 46 a 51: Variação Linguística, Gênero e Tipologia Textual, Tipos de Discurso.
        Metas 52 a 57: Funções e Figuras de Linguagem, Polissemia, Ambiguidade, Coesão e Coerência.
        Metas 58 a 60: Interpretação de Texto, Compreensão Textual.

        [INGLÊS - Categoria: ING]
        Metas 01 a 03: Alfabeto (Alphabet).
        Metas 04 a 18: Substantivos (Nouns), Caso Genitivo, Pronomes (Pronouns).
        Metas 16 a 27: Determinantes, Numerais, Adjetivos (Adjectives), Advérbios (Adverbs), Preposições.
        Metas 28 a 30: Conjunções (Conjunctions).
        Metas 34 a 51: Verbos e Tempos Verbais (Present, Past, Perfect, Continuous, Modal, Phrasal, Future, Reported Speech).
        Metas 52 a 60: Orações Condicionais (If Clauses), Tag Questions, Técnicas de Leitura (Reading).

        [ELETRÔNICA - Categoria: ELET]
        Metas 01 a 03: Circuitos Elétricos (Thevenin, Norton, Superposição, CA, CC, Leis de Kirchhoff).
        Metas 04 a 08: Eletrônica Analógica (Diodos, Transistores BJT, FET, Amplificador Operacional).
        Metas 08 a 12: Eletrônica Digital (Portas lógicas, Combinacionais, Flip-Flops, Contadores, Conversores A/D e D/A, Memórias).
        Metas 12 a 15: Sinais e Sistemas, Eletrônica de Potência (Tiristor, Inversores, Retificadores, Chopper).
        Metas 16 a 18: Máquinas Elétricas, Transformadores, Conversão de Energia.
        Metas 18 a 24: Controle (PID, Servossistemas, Estabilidade, Lugar das Raízes), Instrumentação Industrial, Automação PLC.
        Metas 25 a 27: Programação de Computadores (Algoritmos, POO, Estrutura de Dados), Arquitetura de Computadores.
        Metas 27 a 30: Sistemas Operacionais (Processos, Memória, IO, Sistemas Distribuídos, Tempo Real).
        Metas 30 a 33: Redes de Computadores (OSI, TCP/IP, Segurança, Transmissão, IoT).
        Metas 33 a 36: Medidas Elétricas, Termodinâmica (Primeira/Segunda Lei, Gases Perfeitos, Ciclos Rankine, Carnot, Refrigeração).
        Metas 37 a 42: Mecânica dos Fluidos (Trocadores de calor, Densidade, Pressão, Pascal, Empuxo, Bernoulli, Venturi, Torricelli).
        Metas 43 a 48: Eletromagnetismo (Gauss, Coulomb, Campos, Micro-ondas, Linhas de Transmissão).
        Metas 49 a 54: Princípios de Telecomunicações (Modulação), Antenas, Robótica, Optoeletrônica (LED, Laser).
        Metas 54 a 60: Sistemas de Banco de Dados (Relacional, SQL), Compiladores (Autômatos, Análise Léxica/Sintática).

        INSTRUÇÕES DE EXECUÇÃO:
        1. Identifique cada assunto estudado na "Entrada do usuário".
        2. Para cada assunto, cruze com o "CRONOGRAMA OFICIAL" para encontrar a Categoria (PORT, ING ou ELET) e estime a Meta.
        3. Identifique as horas gastas. Se não estiverem no texto, divida {horas_padrao} horas proporcionalmente.
        
        SAÍDA OBRIGATÓRIA (JSON ESTrito):
        [
          {{"Meta": "Meta 13", "Categoria": "ELET", "Assunto": "Eletrônica de Potência - Retificadores", "Horas": 2.0}}
        ]
        """
        resposta = model.generate_content(prompt).text.strip()
        match = re.search(r'\[.*\]', resposta, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            raise ValueError("JSON não encontrado na resposta.")
    except Exception as e:
        print(f"\n===== ERRO DA IA =====\n{e}\n======================\n")
        return [{"Meta": "Erro de IA", "Categoria": "Geral", "Assunto": texto_estudo, "Horas": horas_padrao}]

# ==========================================
# BARRA LATERAL: CRONÔMETRO
# ==========================================
st.sidebar.header("⏱️ Cronômetro de Estudos")
col1, col2 = st.sidebar.columns(2)

if col1.button("▶️ Iniciar", disabled=st.session_state.timer_rodando, use_container_width=True):
    st.session_state.timer_rodando = True
    st.session_state.inicio_timer = datetime.now()
    st.rerun()

if col2.button("⏹️ Parar", disabled=not st.session_state.timer_rodando, use_container_width=True):
    st.session_state.timer_rodando = False
    if st.session_state.inicio_timer:
        delta = datetime.now() - st.session_state.inicio_timer
        st.session_state.horas_cronometradas = round(delta.total_seconds() / 3600, 2)
    st.rerun()

if st.session_state.timer_rodando:
    st.sidebar.warning(f"⏳ Estudando desde as {st.session_state.inicio_timer.strftime('%H:%M:%S')}...")
elif st.session_state.horas_cronometradas > 0:
    st.sidebar.success(f"✅ Tempo cravado: {st.session_state.horas_cronometradas:.2f}h")

st.sidebar.divider()

# ==========================================
# BARRA LATERAL: ENTRADA DE DADOS
# ==========================================
st.sidebar.header("Registrar Estudo")
with st.sidebar.form("registro_form"):
    data_estudo = st.date_input("Data", datetime.today())
    texto_usuario = st.text_area("O que você estudou?", placeholder="Ex: funções sintáticas e thevenin")
    
    valor_padrao_horas = float(st.session_state.horas_cronometradas) if st.session_state.horas_cronometradas > 0 else 1.0
    horas_totais = st.number_input("Horas Totais", min_value=0.01, step=0.1, format="%.2f", value=valor_padrao_horas)
    
    submit = st.form_submit_button("Salvar Registros")

    if submit and texto_usuario:
        with st.spinner("🤖 A IA está classificando e enviando para o Sheets..."):
            registros_ia = classificar_com_ia(texto_usuario, horas_totais, GEMINI_API_KEY)
            
            novas_linhas = []
            for reg in registros_ia:
                novas_linhas.append({
                    "Data": data_estudo.strftime("%Y-%m-%d"), 
                    "Meta": reg.get("Meta", "Sem Meta"),
                    "Categoria": reg.get("Categoria", "Sem Categoria"), 
                    "Assunto": reg.get("Assunto", "Sem Assunto"), 
                    "Horas": float(reg.get("Horas", 0))
                })
            
            # Adiciona ao dataframe atual e atualiza a planilha no Google Drive
            df_atualizado = pd.concat([df, pd.DataFrame(novas_linhas)], ignore_index=True)
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Página1", data=df_atualizado)
            
        st.session_state.horas_cronometradas = 0.0
        st.success(f"Salvo no Google Sheets com sucesso!")
        st.rerun()

st.sidebar.divider()

# ==========================================
# BARRA LATERAL: GERENCIAR DADOS
# ==========================================
st.sidebar.header("⚙️ Gerenciar Dados")
if st.sidebar.button("🗑️ Apagar Último Registro", use_container_width=True):
    if not df.empty:
        df_atualizado = df.drop(df.tail(1).index)
        # Atualiza a planilha removendo a última linha
        conn.update(spreadsheet=URL_PLANILHA, worksheet="Página1", data=df_atualizado)
        st.sidebar.success("Último registro removido da nuvem!")
        st.rerun()
    else:
        st.sidebar.warning("A planilha já está vazia.")

# ==========================================
# PROCESSAMENTO: 20 SEMANAS E ALTAIR HEATMAP
# ==========================================
if not df.empty:
    df['Data'] = pd.to_datetime(df['Data'], format='mixed')
    data_inicio = df['Data'].min()
    data_fim = data_inicio + timedelta(weeks=20)
    df_20 = df[(df['Data'] >= data_inicio) & (df['Data'] < data_fim)].copy()

    if not df_20.empty:
        st.subheader(f"🔥 Mapa de Calor (20 Semanas a partir de {data_inicio.strftime('%d/%m/%Y')})")
        
        df_20['Semana_Inicio'] = df_20['Data'] - pd.to_timedelta(df_20['Data'].dt.weekday, unit='D')
        df_20['Semana_Inicio'] = df_20['Semana_Inicio'].dt.normalize()
        df_20['Dia_Semana'] = df_20['Data'].dt.weekday 
        
        heatmap_data = df_20.groupby(['Semana_Inicio', 'Dia_Semana'])['Horas'].sum().reset_index()
        
        start_date = data_inicio - timedelta(days=data_inicio.weekday())
        start_date = pd.to_datetime(start_date).normalize()
        
        grid_semanas, grid_dias = [], []
        for i in range(20):
            dt = start_date + timedelta(weeks=i)
            for d in range(7):
                grid_semanas.append(dt)
                grid_dias.append(d)
                
        df_grid = pd.DataFrame({'Semana_Inicio': grid_semanas, 'Dia_Semana': grid_dias})
        df_chart = pd.merge(df_grid, heatmap_data, on=['Semana_Inicio', 'Dia_Semana'], how='left').fillna(0)
        
        dias_map = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
        df_chart['Dia_Nome'] = df_chart['Dia_Semana'].map(dias_map)
        df_chart['Semana_Rotulo'] = df_chart['Semana_Inicio'].dt.strftime('%d/%m')
        
        dias_ordem = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        semanas_ordem = df_grid['Semana_Inicio'].dt.strftime('%d/%m').unique().tolist()
        max_horas = df_chart['Horas'].max() if df_chart['Horas'].max() > 0 else 1.0

        chart = alt.Chart(df_chart).mark_rect(cornerRadius=5).encode(
            x=alt.X('Semana_Rotulo:O', title=None, sort=semanas_ordem, axis=alt.Axis(orient='top', labelAngle=-45, tickSize=0, domain=False)),
            y=alt.Y('Dia_Nome:O', title=None, sort=dias_ordem, axis=alt.Axis(tickSize=0, domain=False)),
            color=alt.Color('Horas:Q', scale=alt.Scale(domain=[0, 0.01, max_horas], range=['#ebedf0', '#9be9a8', '#216e39']), legend=None),
            tooltip=[alt.Tooltip('Semana_Rotulo:O', title='Semana inic.'), alt.Tooltip('Dia_Nome:O', title='Dia'), alt.Tooltip('Horas:Q', title='Horas')]
        ).properties(height=280).configure_scale(bandPaddingInner=0.2).configure_view(strokeWidth=0).configure_axis(grid=False)

        st.altair_chart(chart, width='stretch')
        st.divider()

        # ==========================================
        # GRÁFICO INTERATIVO DE CATEGORIAS
        # ==========================================
        st.subheader("🎯 Distribuição por Metas e Matérias")
        df_agrupado = df.groupby(["Meta", "Categoria", "Assunto"])["Horas"].sum().reset_index()
        
        col1, col2 = st.columns([1, 1.5])
        with col1:
            st.dataframe(df_agrupado.sort_values(by=["Meta", "Horas"], ascending=[True, False]), width='stretch', hide_index=True)
            
        with col2:
            fig_sun = px.sunburst(df_agrupado, path=['Meta', 'Categoria', 'Assunto'], values='Horas', color='Categoria')
            fig_sun.update_traces(textinfo="label+value") 
            fig_sun.update_layout(margin=dict(t=0, l=0, r=0, b=0))
            st.plotly_chart(fig_sun, use_container_width=True)

    else:
        st.info("Nenhum estudo registrado neste intervalo.")
else:
    st.info("Adicione seu primeiro registro de estudo na barra lateral para ver o mapa de calor!")