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

# Prioriza st.fragment (roda só um pedaço da página a cada tick, sem reler a
# planilha nem redesenhar os gráficos). Cai para streamlit-autorefresh (reroda
# a página inteira) apenas se a versão do Streamlit for antiga demais.
if hasattr(st, "fragment"):
    _FRAGMENT_DECORATOR = st.fragment
elif hasattr(st, "experimental_fragment"):
    _FRAGMENT_DECORATOR = st.experimental_fragment
else:
    _FRAGMENT_DECORATOR = None

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_DISPONIVEL = True
except ImportError:
    AUTOREFRESH_DISPONIVEL = False

# Configuração da página
st.set_page_config(page_title="Heatmap de Estudos", layout="wide")
st.title("📚 Meu Painel de Estudos com IA (TRANSPETRO - Ênfase 17: Automação)")

# ==========================================
# DATA DA PROVA / CONTAGEM REGRESSIVA
# ==========================================
DATA_PROVA = datetime(2026, 11, 30)

# ==========================================
# CRONOGRAMA OFICIAL (13 semanas, realinhado com o edital da Ênfase 17)
# Cada tarefa tem um ID único usado como chave do checkbox e como
# identificador de linha na aba "Checklist" do Google Sheets.
# ==========================================
CRONOGRAMA = [
    {
        "semana": 1, "periodo": "01/09 a 07/09",
        "foco": "🔴 Circuitos Elétricos e Medidas — Parte 1",
        "tarefas": [
            ("S1-E1", "ELET", "Teoria dos Circuitos Elétricos: Leis de Ohm e Kirchhoff"),
            ("S1-E2", "ELET", "Resistores em Série e Paralelo, Análise Nodal"),
            ("S1-E3", "ELET", "Transformação de Fontes, Teorema de Thévenin e Norton"),
            ("S1-E4", "ELET", "Teorema da Superposição e Teoremas Adicionais"),
            ("S1-P1", "PORT", "Fonologia (Fonética, Fonemas, Dígrafos, Encontros Vocálicos/Consonantais, Tonicidade)"),
            ("S1-P2", "PORT", "Acentuação Gráfica"),
            ("S1-I1", "ING", "Alphabet / vocabulário básico"),
            ("S1-I2", "ING", "Articles and Nouns"),
            ("S1-S1", "SIM", "Simulado Diagnóstico (foco em Português e Inglês)"),
            ("S1-S2", "SIM", "Simulado temático da semana (plataforma própria)"),
        ],
    },
    {
        "semana": 2, "periodo": "08/09 a 14/09",
        "foco": "🔴 Circuitos Elétricos e Medidas — Parte 2",
        "tarefas": [
            ("S2-E1", "ELET", "Circuitos em Corrente Alternada (fasores, potência ativa/reativa/aparente)"),
            ("S2-E2", "ELET", "Circuitos Trifásicos"),
            ("S2-E3", "ELET", "Elementos Armazenadores de Energia, Circuitos de 1ª e 2ª Ordem"),
            ("S2-E4", "ELET", "Filtros e Quadripolos"),
            ("S2-P1", "PORT", "Ortografia e Significação das Palavras (Parônimos, Homônimos)"),
            ("S2-P2", "PORT", "Uso do Hífen"),
            ("S2-I1", "ING", "Nouns — Syntactic Function / Genitive Case"),
            ("S2-I2", "ING", "Personal Pronouns"),
            ("S2-S1", "SIM", "Simulado temático da semana"),
        ],
    },
    {
        "semana": 3, "periodo": "15/09 a 21/09",
        "foco": "🔴 Eletrônica Analógica e Digital — Parte 1",
        "tarefas": [
            ("S3-E1", "ELET", "Fundamentos de Circuitos Digitais, Sistema de Numeração (BCD, Gray)"),
            ("S3-E2", "ELET", "Circuitos Lógicos Combinacionais, Teoremas Booleanos e Portas Lógicas"),
            ("S3-E3", "ELET", "Amplificadores Operacionais (base de eletrônica analógica)"),
            ("S3-P1", "PORT", "Estrutura e Processo de Formação das Palavras"),
            ("S3-P2", "PORT", "Morfologia — Substantivos e Adjetivos"),
            ("S3-I1", "ING", "Reflexive, Demonstrative and Possessive Pronouns"),
            ("S3-I2", "ING", "Indefinite, Relative and Interrogative Pronouns"),
            ("S3-S1", "SIM", "Simulado temático da semana"),
        ],
    },
    {
        "semana": 4, "periodo": "22/09 a 28/09",
        "foco": "🔴 Eletrônica Analógica e Digital — Parte 2",
        "tarefas": [
            ("S4-E1", "ELET", "Flip-Flops, Contadores Assíncronos e Síncronos, Registradores"),
            ("S4-E2", "ELET", "Conversores A-D e D-A"),
            ("S4-E3", "ELET", "Bateria de questões — Eletrônica Digital completo"),
            ("S4-P1", "PORT", "Morfologia — Numerais, Artigos e Interjeições"),
            ("S4-P2", "PORT", "Morfologia — Conjunções e Preposições"),
            ("S4-I1", "ING", "Determiners and Numerals"),
            ("S4-I2", "ING", "Adjectives (Cardinal/Ordinal, Comparative/Superlative)"),
            ("S4-S1", "SIM", "Simulado temático da semana"),
        ],
    },
    {
        "semana": 5, "periodo": "29/09 a 05/10",
        "foco": "🔴 Sistemas de Controle Linear/Não-linear/Digital + Conceitos de Estabilidade",
        "tarefas": [
            ("S5-E1", "ELET", "Problema Geral de Controle, Realimentação, Servossistemas Lineares"),
            ("S5-E2", "ELET", "Função de Transferência, Diagramas de Blocos, Equação de Estado"),
            ("S5-E3", "ELET", "Estabilidade: Lugar das Raízes, Resposta em Frequência (Bode)"),
            ("S5-P1", "PORT", "Morfologia — Pronomes"),
            ("S5-P2", "PORT", "Morfologia — Advérbios"),
            ("S5-I1", "ING", "Adverbs and Verbal Phrases (Comparative/Superlative)"),
            ("S5-I2", "ING", "Prepositions"),
            ("S5-S1", "SIM", "Simulado temático da semana"),
        ],
    },
    {
        "semana": 6, "periodo": "06/10 a 12/10",
        "foco": "🟢 Controle e Servomecanismos + Controle Discreto (itens oficiais sem histórico)",
        "tarefas": [
            ("S6-E1", "ELET", "Fundamentos de Controle Discreto (amostragem, Transformada Z)"),
            ("S6-E2", "ELET", "Equações a Diferenças, Sistemas em Tempo Discreto"),
            ("S6-E3", "ELET", "Servomecanismos: conceitos e aplicações práticas"),
            ("S6-P1", "PORT", "Morfologia — Verbo (classificação, tempos, vozes)"),
            ("S6-P2", "PORT", "Função do \"Que\" e do \"Se\""),
            ("S6-I1", "ING", "Conjunctions"),
            ("S6-I2", "ING", "Subordinate Clauses"),
            ("S6-R1", "REV", "Revisão geral — Semanas 1 a 6"),
            ("S6-S1", "SIM", "SIMULADO 1 COMPLETO (prova inteira, tempo cronometrado) + correção"),
        ],
    },
    {
        "semana": 7, "periodo": "13/10 a 19/10",
        "foco": "🔴 Sistemas de Atuação Hidráulicos e Pneumáticos (item que estava zerado)",
        "tarefas": [
            ("S7-E1", "ELET", "Fundamentos de hidráulica e pneumática aplicadas à automação"),
            ("S7-E2", "ELET", "Válvulas de controle e de bloqueio, atuadores hidráulicos e pneumáticos"),
            ("S7-E3", "ELET", "Acumuladores, relação pressão x vazão, aplicação em dutos e terminais"),
            ("S7-P1", "PORT", "Sintaxe do Período Simples — Termos Essenciais (Sujeito, Predicado)"),
            ("S7-P2", "PORT", "Termos Integrantes e Acessórios da Oração"),
            ("S7-I1", "ING", "Simple Present"),
            ("S7-I2", "ING", "Present Continuous / Simple Past"),
            ("S7-R1", "REV", "Correção dos erros do Simulado 1"),
            ("S7-S1", "SIM", "Simulado temático da semana"),
        ],
    },
    {
        "semana": 8, "periodo": "20/10 a 26/10",
        "foco": "🔴 Redes de Computadores e Comunicação de Dados",
        "tarefas": [
            ("S8-E1", "ELET", "Modelo de Camadas ISO/OSI, Arquitetura TCP/IP"),
            ("S8-E2", "ELET", "Protocolos e Topologias de Rede, Redes de \"Chão de Fábrica\" (Fieldbus, Profibus)"),
            ("S8-E3", "ELET", "Conceito de Comunicação Digital, Segurança de Redes — noções básicas"),
            ("S8-P1", "PORT", "Sintaxe do Período Composto — Coordenação e Subordinadas Adverbiais"),
            ("S8-P2", "PORT", "Subordinadas Substantivas, Adjetivas e Reduzidas"),
            ("S8-I1", "ING", "Past Continuous / Present Perfect"),
            ("S8-I2", "ING", "Present Perfect Continuous / Past Perfect"),
            ("S8-S1", "SIM", "Simulado temático da semana"),
        ],
    },
    {
        "semana": 9, "periodo": "27/10 a 02/11",
        "foco": "🟡 Ferramentas Matemáticas Aplicadas + Modelagem e Simulação de Sistemas Dinâmicos",
        "tarefas": [
            ("S9-E1", "ELET", "Transformadas de Laplace e Z, Métodos Numéricos"),
            ("S9-E2", "ELET", "Linearização de sistemas não-lineares, Espaço de Estados"),
            ("S9-E3", "ELET", "Dinâmica de Sistemas: massa-mola-amortecedor (base física para modelagem)"),
            ("S9-P1", "PORT", "Regência Verbal e Nominal"),
            ("S9-P2", "PORT", "Concordância Verbal e Nominal"),
            ("S9-I1", "ING", "Past Perfect Continuous / Passive Voice"),
            ("S9-I2", "ING", "Modal Verbs / Infinitive, Gerund and Participle"),
            ("S9-S1", "SIM", "SIMULADO 2 COMPLETO (prova inteira, tempo cronometrado) + correção"),
        ],
    },
    {
        "semana": 10, "periodo": "03/11 a 09/11",
        "foco": "🟡 Eletrônica de Potência + Conversão Eletromecânica de Energia",
        "tarefas": [
            ("S10-E1", "ELET", "Conceitos Básicos, Retificadores, Tiristor"),
            ("S10-E2", "ELET", "Chopper, Controlador CA, Inversor de Frequência, Conversores CC-CC"),
            ("S10-E3", "ELET", "Princípios de Conversão Eletromecânica: transformadores e máquinas"),
            ("S10-P1", "PORT", "Crase"),
            ("S10-P2", "PORT", "Colocação Pronominal e Pontuação"),
            ("S10-I1", "ING", "Phrasal Verbs and Prepositional Verbs / Reported Speech"),
            ("S10-I2", "ING", "Simple Future / Progressive Future / Future Perfect"),
            ("S10-R1", "REV", "Correção dos erros do Simulado 2"),
            ("S10-S1", "SIM", "Simulado temático da semana"),
        ],
    },
    {
        "semana": 11, "periodo": "10/11 a 16/11",
        "foco": "🟡 Sensores e Transdutores + Processamento de Sinais + CLP/PLC e Programação",
        "tarefas": [
            ("S11-E1", "ELET", "Instrumentação e Técnicas de Medida, Sensores de pressão/nível/temperatura/vazão"),
            ("S11-E2", "ELET", "Curvas de calibração e resposta em frequência (Bode), Filtragem de sinais"),
            ("S11-E3", "ELET", "Programação Ladder, IL-SFC, ST; Microprocessadores/Microcontroladores; Sistemas Embarcados"),
            ("S11-P1", "PORT", "Uso dos Porquês e Variação Linguística"),
            ("S11-P2", "PORT", "Gênero e Tipologia Textual / Tipos de Discurso"),
            ("S11-I1", "ING", "Conditional Clauses (If Clauses)"),
            ("S11-I2", "ING", "Subjunctive Mood and Wish"),
            ("S11-S1", "SIM", "SIMULADO 3 COMPLETO (prova inteira, tempo cronometrado) + correção"),
        ],
    },
    {
        "semana": 12, "periodo": "17/11 a 23/11",
        "foco": "🟢 Robótica + Automação da Manufatura/Industrial + Revisão de Português/Inglês",
        "tarefas": [
            ("S12-E1", "ELET", "Fundamentos de Robótica: cinemática básica, tipos de manipuladores"),
            ("S12-E2", "ELET", "Integração e Automação da Manufatura, Automação Industrial (segurança ICS)"),
            ("S12-E3", "ELET", "Revisão de Dinâmica de Sistemas e Estabilidade (reforço)"),
            ("S12-P1", "PORT", "Funções da Linguagem e Figuras de Linguagem"),
            ("S12-P2", "PORT", "Polissemia, Ambiguidade, Coesão e Coerência"),
            ("S12-I1", "ING", "Tag Questions"),
            ("S12-I2", "ING", "Reading Techniques (técnicas de leitura e interpretação)"),
            ("S12-P3", "PORT", "Interpretação de Texto — prática intensiva com textos de prova (PORT e ING)"),
            ("S12-S1", "SIM", "SIMULADO 4 COMPLETO (prova inteira, tempo cronometrado) + correção"),
            ("S12-R1", "REV", "Revisão geral de todo o Português e Inglês (focar no que errou nos simulados)"),
        ],
    },
    {
        "semana": 13, "periodo": "24/11 a 30/11 — RETA FINAL",
        "foco": "🔵 Revisão final e prova",
        "tarefas": [
            ("S13-1", "REV", "24-25/11: Revisão ativa dos 5 Temas de Alta Frequência de ELET"),
            ("S13-2", "REV", "26/11: Revisão ativa de Português e Inglês (foco nos erros dos 4 simulados)"),
            ("S13-3", "SIM", "27/11: Refazer prova anterior completa (2023), tempo oficial"),
            ("S13-4", "REV", "28/11: Revisão dos pontos fracos da prova de 2023"),
            ("S13-5", "REV", "29/11: Revisão leve de resumos/fórmulas + logística da prova"),
            ("S13-6", "FINAL", "30/11: DIA DA PROVA"),
        ],
    },
]

CORES_CATEGORIA = {
    "ELET": "#1f77b4", "PORT": "#d62728", "ING": "#2ca02c",
    "SIM": "#9467bd", "REV": "#7f7f7f", "FINAL": "#e69138",
}


def extrai_semana_num(meta_str):
    """Extrai o número da semana de valores como 'Semana 7' ou (formato antigo) 'Meta 13'."""
    m = re.search(r"(\d+)", str(meta_str))
    return int(m.group(1)) if m else 0

# ==========================================
# VARIÁVEIS DE SESSÃO E CONEXÕES
# ==========================================
if 'timer_rodando' not in st.session_state:
    st.session_state.timer_rodando = False
    st.session_state.inicio_timer = None
    st.session_state.horas_cronometradas = 0.0

# --- Estado do timer Pomodoro ---
if 'pomodoro_ativo' not in st.session_state:
    st.session_state.pomodoro_ativo = False
    st.session_state.pomodoro_modo = "foco"           # "foco" ou "pausa"
    st.session_state.pomodoro_inicio = None
    st.session_state.pomodoro_ciclos = 0               # ciclos de foco concluídos
    st.session_state.pomodoro_pausada_restante = None  # segundos restantes quando pausado manualmente
    st.session_state.pomodoro_duracao_foco = 25
    st.session_state.pomodoro_duracao_pausa = 5
    st.session_state.pomodoro_duracao_pausa_longa = 15

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
URL_PLANILHA = st.secrets["spreadsheet"]

# Conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data(ttl=30, show_spinner=False)
def carregar_dados():
    try:
        # ttl=30: reaproveita a leitura por 30s em vez de bater na API do Sheets
        # a cada rerun (evita estourar a cota de "Read requests per minute").
        df = conn.read(spreadsheet=URL_PLANILHA, worksheet="Página1", ttl=30)
        # Limpa linhas vazias caso o Sheets crie acidentalmente
        df = df.dropna(subset=["Data", "Assunto"])
        return df
    except Exception as e:
        st.error(f"Erro ao ler a planilha: {e}")
        return pd.DataFrame(columns=["Data", "Meta", "Categoria", "Assunto", "Horas"])


df = carregar_dados()


# ==========================================
# CHECKLIST DO CRONOGRAMA (nova aba "Checklist" no Google Sheets)
# ==========================================
def gerar_checklist_inicial():
    """Constrói o DataFrame base a partir do CRONOGRAMA, todas as tarefas desmarcadas."""
    linhas = []
    for semana_info in CRONOGRAMA:
        for tarefa_id, categoria, texto in semana_info["tarefas"]:
            linhas.append({
                "ID": tarefa_id,
                "Semana": semana_info["semana"],
                "Periodo": semana_info["periodo"],
                "Categoria": categoria,
                "Tarefa": texto,
                "Concluido": False,
                "DataConclusao": "",
            })
    return pd.DataFrame(linhas)


def _normaliza_concluido(serie):
    """Converte a coluna Concluido (que pode vir como bool, 'TRUE'/'FALSE', 1/0, NaN...) para bool de forma robusta."""
    return (
        serie.astype(str).str.strip().str.lower()
        .isin(["true", "1", "1.0", "sim", "verdadeiro", "yes"])
    )


def _worksheet_existe(nome_aba):
    """Tenta ler a aba; retorna True se existir (mesmo vazia), False se não existir."""
    try:
        conn.read(spreadsheet=URL_PLANILHA, worksheet=nome_aba, ttl=15)
        return True
    except Exception:
        return False


def carregar_checklist():
    """Lê a aba 'Checklist'. Se não existir, CRIA (conn.create) com base no CRONOGRAMA.
    Se existir mas faltar alguma tarefa nova, completa com UPDATE (conn.update)."""
    aba_existe = _worksheet_existe("Checklist")

    if not aba_existe:
        # Primeira vez: a aba precisa ser CRIADA, não atualizada — conn.update() falha
        # silenciosamente (ou lança erro) em abas que ainda não existem.
        df_inicial = gerar_checklist_inicial()
        try:
            conn.create(spreadsheet=URL_PLANILHA, worksheet="Checklist", data=df_inicial)
            st.toast("Aba 'Checklist' criada no Google Sheets ✅")
        except Exception as e:
            st.warning(
                f"Não consegui criar a aba 'Checklist' automaticamente ({e}). "
                "Crie manualmente uma aba chamada 'Checklist' na planilha (pode deixar em branco) "
                "e recarregue a página — o app preenche o conteúdo sozinho na próxima carga."
            )
        return df_inicial

    # A aba já existe — lê o progresso salvo
    try:
        df_check = conn.read(spreadsheet=URL_PLANILHA, worksheet="Checklist", ttl=15)
        df_check = df_check.dropna(subset=["ID"])
        df_check["ID"] = df_check["ID"].astype(str).str.strip()
        df_check["Semana"] = pd.to_numeric(df_check["Semana"], errors="coerce").astype("Int64")
        df_check["Concluido"] = _normaliza_concluido(df_check["Concluido"])
        if "DataConclusao" not in df_check.columns:
            df_check["DataConclusao"] = ""
        df_check["DataConclusao"] = df_check["DataConclusao"].fillna("")

        # Garante que novas tarefas adicionadas ao CRONOGRAMA (ex: você editou o script) entrem na planilha,
        # SEM apagar o progresso já salvo das tarefas existentes.
        ids_existentes = set(df_check["ID"])
        ids_atuais = {t[0] for s in CRONOGRAMA for t in s["tarefas"]}
        ids_faltando = ids_atuais - ids_existentes
        if ids_faltando:
            df_novo = gerar_checklist_inicial()
            df_novo = df_novo[df_novo["ID"].isin(ids_faltando)]
            df_check = pd.concat([df_check, df_novo], ignore_index=True)
            conn.update(spreadsheet=URL_PLANILHA, worksheet="Checklist", data=df_check)
        return df_check
    except Exception as e:
        st.warning(f"Erro ao ler a aba 'Checklist' ({e}). Recriando localmente a partir do cronograma padrão.")
        return gerar_checklist_inicial()


if "checklist_df" not in st.session_state:
    st.session_state.checklist_df = carregar_checklist()
    st.session_state.checklist_salvo = True


def marcar_tarefa(tarefa_id):
    novo_valor = st.session_state[f"chk_{tarefa_id}"]
    df_chk = st.session_state.checklist_df
    df_chk.loc[df_chk["ID"] == tarefa_id, "Concluido"] = novo_valor
    df_chk.loc[df_chk["ID"] == tarefa_id, "DataConclusao"] = (
        datetime.now().strftime("%Y-%m-%d") if novo_valor else ""
    )
    st.session_state.checklist_salvo = False


def salvar_checklist():
    """Grava o progresso atual na aba 'Checklist'. Usa CREATE se a aba ainda não existir
    (ex.: foi apagada manualmente) e UPDATE no caso normal."""
    df_para_salvar = st.session_state.checklist_df.copy()
    # Grava o booleano como texto explícito para evitar ambiguidade na volta da leitura
    df_para_salvar["Concluido"] = df_para_salvar["Concluido"].map({True: "TRUE", False: "FALSE"})
    if _worksheet_existe("Checklist"):
        conn.update(spreadsheet=URL_PLANILHA, worksheet="Checklist", data=df_para_salvar)
    else:
        conn.create(spreadsheet=URL_PLANILHA, worksheet="Checklist", data=df_para_salvar)
    st.session_state.checklist_salvo = True


# ==========================================
# CLASSIFICAÇÃO COM IA
# ==========================================
def classificar_com_ia(texto_estudo, horas_padrao, api_key):
    if not api_key:
        return [{"Meta": "Sem Meta", "Categoria": "Geral (Sem IA)", "Assunto": texto_estudo, "Horas": horas_padrao}]

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-3.5-flash')

        prompt = f"""
        Você é um classificador rigoroso de dados para o cronograma de estudos da TRANSPETRO
        (Ênfase 17: Engenharia de Automação), organizado em 13 semanas (01/09 a 30/11/2026).
        Sua missão é ler o que o usuário estudou, separar os assuntos e classificá-los EXATAMENTE
        de acordo com o mapeamento oficial abaixo.

        Entrada do usuário: "{texto_estudo}"

        === CRONOGRAMA OFICIAL (USE ESTAS REFERÊNCIAS PARA A "Meta" E A "Categoria") ===
        A "Meta" deve ser preenchida no formato "Semana X" (X de 1 a 13).
        A "Categoria" deve ser uma destas: ELET, PORT, ING, SIM ou REV.

        [ELET - por semana]
        Semana 1-2: Circuitos Elétricos (Ohm, Kirchhoff, Thevenin, Norton, Superposição, CA/CC, Trifásicos, Filtros, Quadripolos).
        Semana 3-4: Eletrônica Analógica e Digital (portas lógicas, combinacionais, Flip-Flops, contadores, conversores A/D-D/A, amp op).
        Semana 5: Controle Linear/Não-linear/Digital, Estabilidade (Bode, Lugar das Raízes), Espaço de Estados.
        Semana 6: Controle Discreto e Servomecanismos (Transformada Z, amostragem).
        Semana 7: Sistemas de Atuação Hidráulicos e Pneumáticos (válvulas, atuadores, acumuladores).
        Semana 8: Redes de Computadores (OSI, TCP/IP, protocolos, chão de fábrica, segurança de redes).
        Semana 9: Ferramentas Matemáticas (Laplace, Z), Modelagem e Simulação de Sistemas Dinâmicos.
        Semana 10: Eletrônica de Potência (retificadores, tiristor, chopper, inversor) e Conversão Eletromecânica.
        Semana 11: Sensores e Transdutores, Processamento de Sinais, CLP/PLC (Ladder, IL-SFC, ST), Microcontroladores, Sistemas Embarcados.
        Semana 12: Robótica, Integração e Automação da Manufatura, Automação Industrial.
        Semana 13: Revisão geral e prova anterior.

        [PORT - por semana]
        Semana 1: Fonologia, Acentuação Gráfica.
        Semana 2: Ortografia, Significação das Palavras, Hífen.
        Semana 3: Estrutura/Formação de Palavras, Morfologia (Substantivos, Adjetivos).
        Semana 4: Morfologia (Numerais, Artigos, Interjeições, Conjunções, Preposições).
        Semana 5: Morfologia (Pronomes, Advérbios).
        Semana 6: Morfologia (Verbo), Função do Que/Se.
        Semana 7: Sintaxe do Período Simples (Termos Essenciais, Integrantes, Acessórios).
        Semana 8: Sintaxe do Período Composto (Coordenação, Subordinadas).
        Semana 9: Regência Verbal e Nominal, Concordância Verbal e Nominal.
        Semana 10: Crase, Colocação Pronominal, Pontuação.
        Semana 11: Uso dos Porquês, Variação Linguística, Gênero e Tipologia Textual.
        Semana 12: Funções e Figuras de Linguagem, Polissemia, Ambiguidade, Coesão, Coerência, Interpretação de Texto.

        [ING - por semana]
        Semana 1: Alphabet, Articles, Nouns.
        Semana 2: Nouns (Syntactic Function, Genitive Case), Personal Pronouns.
        Semana 3: Reflexive/Demonstrative/Possessive/Indefinite/Relative/Interrogative Pronouns.
        Semana 4: Determiners, Numerals, Adjectives (Comparative/Superlative).
        Semana 5: Adverbs, Prepositions.
        Semana 6: Conjunctions, Subordinate Clauses.
        Semana 7: Simple Present, Present Continuous, Simple Past.
        Semana 8: Present Perfect, Present Perfect Continuous, Past Perfect.
        Semana 9: Past Perfect Continuous, Passive Voice, Modal Verbs, Infinitive/Gerund/Participle.
        Semana 10: Phrasal Verbs, Reported Speech, Simple Future, Future Perfect.
        Semana 11: Conditional Clauses, Subjunctive Mood.
        Semana 12: Tag Questions, Reading Techniques.

        INSTRUÇÕES DE EXECUÇÃO:
        1. Identifique cada assunto estudado na "Entrada do usuário".
        2. Para cada assunto, cruze com o "CRONOGRAMA OFICIAL" para encontrar a Semana (Meta) e a Categoria (ELET, PORT ou ING).
        3. Se o usuário mencionar simulado, prova ou revisão, use Categoria "SIM" ou "REV" conforme o caso.
        4. Identifique as horas gastas. Se não estiverem no texto, divida {horas_padrao} horas proporcionalmente.

        SAÍDA OBRIGATÓRIA (JSON ESTRITO):
        [
          {{"Meta": "Semana 7", "Categoria": "ELET", "Assunto": "Sistemas de Atuação Hidráulicos e Pneumáticos - Válvulas", "Horas": 2.0}}
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
# CONTAGEM REGRESSIVA (topo do painel)
# ==========================================
hoje = datetime.now()
dias_restantes = (DATA_PROVA - hoje).days
semanas_restantes = dias_restantes / 7

col_cd1, col_cd2, col_cd3 = st.columns(3)
with col_cd1:
    if dias_restantes >= 0:
        st.metric("⏳ Dias até a prova", f"{dias_restantes} dias")
    else:
        st.metric("⏳ Status", "Prova já realizada")
with col_cd2:
    st.metric("📆 Semanas restantes", f"{semanas_restantes:.1f} semanas")
with col_cd3:
    total_tarefas = len(st.session_state.checklist_df)
    concluidas = int(st.session_state.checklist_df["Concluido"].sum())
    pct = concluidas / total_tarefas if total_tarefas else 0
    st.metric("✅ Progresso do cronograma", f"{concluidas}/{total_tarefas} ({pct:.0%})")

st.progress(pct)
st.caption(f"Prova: 30/11/2026 · Ênfase 17 - Engenharia de Automação (TRANSPETRO)")
st.divider()

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
# BARRA LATERAL: TIMER POMODORO
# ==========================================
def _pomodoro_duracao_modo_segundos():
    """Duração (em segundos) do modo atual do pomodoro (foco, pausa curta ou pausa longa)."""
    if st.session_state.pomodoro_modo == "foco":
        return st.session_state.pomodoro_duracao_foco * 60
    if st.session_state.pomodoro_ciclos > 0 and st.session_state.pomodoro_ciclos % 4 == 0:
        return st.session_state.pomodoro_duracao_pausa_longa * 60
    return st.session_state.pomodoro_duracao_pausa * 60


def _pomodoro_iniciar():
    st.session_state.pomodoro_ativo = True
    if st.session_state.pomodoro_pausada_restante is not None:
        # Retoma de onde parou, recalculando um "início" que já reflete o tempo decorrido
        decorrido_ja = _pomodoro_duracao_modo_segundos() - st.session_state.pomodoro_pausada_restante
        st.session_state.pomodoro_inicio = datetime.now() - timedelta(seconds=decorrido_ja)
        st.session_state.pomodoro_pausada_restante = None
    else:
        st.session_state.pomodoro_inicio = datetime.now()


def _pomodoro_pausar():
    decorrido = (datetime.now() - st.session_state.pomodoro_inicio).total_seconds()
    st.session_state.pomodoro_pausada_restante = max(0.0, _pomodoro_duracao_modo_segundos() - decorrido)
    st.session_state.pomodoro_ativo = False


def _pomodoro_resetar():
    st.session_state.pomodoro_ativo = False
    st.session_state.pomodoro_modo = "foco"
    st.session_state.pomodoro_inicio = None
    st.session_state.pomodoro_ciclos = 0
    st.session_state.pomodoro_pausada_restante = None


def _pomodoro_corpo():
    """Todo o widget do Pomodoro. Quando o navegador suporta st.fragment, só ESTA
    função reroda a cada segundo — o resto da página (planilha, gráficos,
    cronograma) fica intocado, então carregar_dados() não é chamado de novo."""
    st.sidebar.header("🍅 Timer Pomodoro")

    with st.sidebar.expander("⚙️ Configurar ciclos", expanded=False):
        st.session_state.pomodoro_duracao_foco = st.number_input(
            "Foco (min)", min_value=1, value=st.session_state.pomodoro_duracao_foco,
            step=1, disabled=st.session_state.pomodoro_ativo, key="pomo_cfg_foco",
        )
        st.session_state.pomodoro_duracao_pausa = st.number_input(
            "Pausa curta (min)", min_value=1, value=st.session_state.pomodoro_duracao_pausa,
            step=1, disabled=st.session_state.pomodoro_ativo, key="pomo_cfg_pausa",
        )
        st.session_state.pomodoro_duracao_pausa_longa = st.number_input(
            "Pausa longa (min, a cada 4 ciclos)", min_value=1, value=st.session_state.pomodoro_duracao_pausa_longa,
            step=1, disabled=st.session_state.pomodoro_ativo, key="pomo_cfg_pausa_longa",
        )

    col_pm1, col_pm2, col_pm3 = st.sidebar.columns(3)
    if col_pm1.button("▶️", key="pomo_play", disabled=st.session_state.pomodoro_ativo, use_container_width=True):
        _pomodoro_iniciar()
        st.rerun()
    if col_pm2.button("⏸️", key="pomo_pause", disabled=not st.session_state.pomodoro_ativo, use_container_width=True):
        _pomodoro_pausar()
        st.rerun()
    if col_pm3.button("🔄", key="pomo_reset", use_container_width=True):
        _pomodoro_resetar()
        st.rerun()

    duracao_modo_atual = _pomodoro_duracao_modo_segundos()

    if st.session_state.pomodoro_ativo:
        decorrido = (datetime.now() - st.session_state.pomodoro_inicio).total_seconds()
        restante = duracao_modo_atual - decorrido

        if restante <= 0:
            # Fecha o ciclo atual e alterna automaticamente para o próximo modo
            if st.session_state.pomodoro_modo == "foco":
                st.session_state.pomodoro_ciclos += 1
                # Soma o tempo de foco concluído ao "cronômetro" de horas, que já
                # é usado para pré-preencher o formulário de registro de estudo
                st.session_state.horas_cronometradas = round(
                    st.session_state.horas_cronometradas + st.session_state.pomodoro_duracao_foco / 60, 2
                )
                st.session_state.pomodoro_modo = "pausa"
                st.toast(f"🍅 Ciclo {st.session_state.pomodoro_ciclos} concluído! Hora da pausa.")
            else:
                st.session_state.pomodoro_modo = "foco"
                st.toast("☕ Pausa concluída! De volta ao foco.")
            st.session_state.pomodoro_inicio = datetime.now()
            st.rerun()
        else:
            minutos_rest, segundos_rest = int(restante // 60), int(restante % 60)
            rotulo_modo = "🎯 Foco" if st.session_state.pomodoro_modo == "foco" else "☕ Pausa"
            st.sidebar.metric(rotulo_modo, f"{minutos_rest:02d}:{segundos_rest:02d}")
            st.sidebar.progress(min(1.0, max(0.0, 1 - (restante / duracao_modo_atual))) if duracao_modo_atual else 0.0)
    elif st.session_state.pomodoro_pausada_restante is not None:
        minutos_rest = int(st.session_state.pomodoro_pausada_restante // 60)
        segundos_rest = int(st.session_state.pomodoro_pausada_restante % 60)
        rotulo_modo = "🎯 Foco" if st.session_state.pomodoro_modo == "foco" else "☕ Pausa"
        st.sidebar.metric(f"{rotulo_modo} (pausado)", f"{minutos_rest:02d}:{segundos_rest:02d}")
    else:
        st.sidebar.caption(f"Pronto para começar: {st.session_state.pomodoro_duracao_foco} min de foco")

    st.sidebar.caption(f"🔁 Ciclos de foco concluídos: {st.session_state.pomodoro_ciclos}")

    if st.session_state.pomodoro_ativo and _FRAGMENT_DECORATOR is None and not AUTOREFRESH_DISPONIVEL:
        st.sidebar.button("🔄 Atualizar contagem", key="pomo_refresh_manual")

    st.sidebar.divider()


if _FRAGMENT_DECORATOR is not None:
    # Fragmento nativo do Streamlit: só ele reroda sozinho a cada 1s enquanto
    # ativo. Fora do modo ativo, run_every=None (não fica rodando à toa).
    intervalo = 1 if st.session_state.pomodoro_ativo else None
    _FRAGMENT_DECORATOR(run_every=intervalo)(_pomodoro_corpo)()
else:
    # Streamlit desatualizado (sem st.fragment/experimental_fragment): cai para
    # o autorefresh de página inteira. carregar_dados() já está com cache de
    # 30s, então isso não deve mais estourar a cota do Sheets — mas o ideal é
    # atualizar o Streamlit (`pip install -U streamlit`) para ter os fragmentos.
    _pomodoro_corpo()
    if st.session_state.pomodoro_ativo and AUTOREFRESH_DISPONIVEL:
        st_autorefresh(interval=1000, limit=None, key="pomodoro_autorefresh")

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

if st.sidebar.button("🔄 Recarregar Checklist do Sheets", use_container_width=True):
    st.session_state.checklist_df = carregar_checklist()
    st.session_state.checklist_salvo = True
    st.sidebar.success("Checklist recarregado!")
    st.rerun()

if st.sidebar.button("📥 Atualizar Dados da Planilha Agora", use_container_width=True):
    carregar_dados.clear()
    st.sidebar.success("Cache limpo — dados atualizados!")
    st.rerun()

# ==========================================
# PROCESSAMENTO: DADOS, MÉTRICAS E GRÁFICOS
# ==========================================
if not df.empty:
    # Garantir que a coluna Data é datetime e Horas é numérico
    df['Data'] = pd.to_datetime(df['Data'], format='mixed')
    df['Horas'] = pd.to_numeric(df['Horas'], errors='coerce').fillna(0)

    # ------------------------------------------
    # 1. QUADRO DE HORAS TOTAIS
    # ------------------------------------------
    horas_totais = df['Horas'].sum()
    st.metric(label="⏳ Total de Horas Estudadas", value=f"{horas_totais:.2f}h")
    st.divider()

    # ------------------------------------------
    # 2. MAPA DE CALOR (20 SEMANAS)
    # ------------------------------------------
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

        # ------------------------------------------
        # 3. GRÁFICOS — HORAS POR CATEGORIA E POR SEMANA
        # ------------------------------------------
        st.subheader("🎯 Distribuição do Tempo de Estudo")
        st.caption("Cores padronizadas: 🔵 ELET · 🔴 PORT · 🟢 ING · 🟣 SIM · ⚪ REV")

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            # Horas por categoria — barra horizontal simples, ordenada, com % do total
            df_categoria = df.groupby("Categoria")["Horas"].sum().reset_index()
            total_horas_cat = df_categoria["Horas"].sum()
            df_categoria["Rotulo"] = df_categoria.apply(
                lambda r: f"{r['Horas']:.1f}h ({r['Horas'] / total_horas_cat:.0%})" if total_horas_cat else "0h", axis=1
            )
            df_categoria = df_categoria.sort_values("Horas", ascending=True)
            fig_bar = px.bar(
                df_categoria, x="Horas", y="Categoria", orientation="h",
                color="Categoria", color_discrete_map=CORES_CATEGORIA,
                text="Rotulo", title="Horas por Categoria",
            )
            fig_bar.update_traces(textposition="outside", cliponaxis=False)
            fig_bar.update_layout(showlegend=False, xaxis_title="Horas", yaxis_title=None)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_g2:
            # Horas por semana, empilhado por categoria — substitui o sunburst antigo
            df_sem = df.copy()
            df_sem["SemanaNum"] = df_sem["Meta"].apply(extrai_semana_num)
            df_sem_agrupado = df_sem.groupby(["SemanaNum", "Meta", "Categoria"])["Horas"].sum().reset_index()
            ordem_semanas = (
                df_sem_agrupado.drop_duplicates("SemanaNum").sort_values("SemanaNum")["Meta"].tolist()
            )
            fig_semana = px.bar(
                df_sem_agrupado, x="Horas", y="Meta", color="Categoria", orientation="h",
                color_discrete_map=CORES_CATEGORIA,
                category_orders={"Meta": ordem_semanas},
                title="Horas por Semana (empilhado por categoria)",
            )
            fig_semana.update_layout(yaxis_title=None, xaxis_title="Horas", legend_title="Categoria")
            st.plotly_chart(fig_semana, use_container_width=True)

        st.divider()

        # ------------------------------------------
        # 4. EVOLUÇÃO ACUMULADA — ritmo de estudo x tempo
        # ------------------------------------------
        st.subheader("📈 Evolução do Tempo de Estudo")
        df_evolucao = df.groupby(df["Data"].dt.date)["Horas"].sum().reset_index()
        df_evolucao.columns = ["Data", "Horas"]
        df_evolucao = df_evolucao.sort_values("Data")
        df_evolucao["Acumulado"] = df_evolucao["Horas"].cumsum()
        fig_linha = px.line(
            df_evolucao, x="Data", y="Acumulado", markers=True,
            title="Horas Acumuladas ao Longo do Tempo",
        )
        fig_linha.update_layout(yaxis_title="Horas acumuladas", xaxis_title=None)
        fig_linha.add_vline(
            x=DATA_PROVA.strftime("%Y-%m-%d"), line_dash="dash", line_color="red",
            annotation_text="Prova (30/11)", annotation_position="top right",
        )
        st.plotly_chart(fig_linha, use_container_width=True)

        st.divider()

        # ------------------------------------------
        # 5. TABELA DETALHADA — com filtro por semana (substitui o drill-down do sunburst)
        # ------------------------------------------
        st.subheader("🔍 Detalhamento por Semana e Assunto")
        semanas_disponiveis = sorted(df_sem["Meta"].dropna().unique(), key=extrai_semana_num)
        semana_filtro = st.selectbox("Filtrar por semana", ["Todas as semanas"] + semanas_disponiveis)

        df_agrupado = df.groupby(["Meta", "Categoria", "Assunto"])["Horas"].sum().reset_index()
        if semana_filtro != "Todas as semanas":
            df_agrupado = df_agrupado[df_agrupado["Meta"] == semana_filtro]

        st.dataframe(
            df_agrupado.sort_values(by=["Meta", "Horas"], ascending=[True, False]),
            width='stretch', hide_index=True,
        )

    else:
        st.info("Nenhum estudo registrado neste intervalo.")
else:
    st.info("Adicione seu primeiro registro de estudo na barra lateral para ver o painel!")

st.divider()

# ==========================================
# 4. CRONOGRAMA DETALHADO — CHECKLIST POR SEMANA
# ==========================================
st.header("📅 Cronograma de Estudos — Marque conforme for estudando")

if not st.session_state.checklist_salvo:
    st.warning("Você tem alterações não salvas neste cronograma.")

if st.button("💾 Salvar Progresso do Cronograma no Google Sheets", type="primary"):
    with st.spinner("Salvando..."):
        salvar_checklist()
    st.success("Progresso salvo na aba 'Checklist' da planilha!")

df_chk = st.session_state.checklist_df

# Determina a semana atual do plano (Semana 1 começa em 01/09/2026) para abrir o expander correspondente
INICIO_PLANO = datetime(2026, 9, 1)
if hoje < INICIO_PLANO:
    semana_atual = 1
else:
    semana_atual = min(13, ((hoje - INICIO_PLANO).days // 7) + 1)

for semana_info in CRONOGRAMA:
    semana_num = semana_info["semana"]
    df_semana = df_chk[df_chk["Semana"] == semana_num]
    concluidas_semana = int(df_semana["Concluido"].sum())
    total_semana = len(df_semana)
    rotulo_expander = f"Semana {semana_num} ({semana_info['periodo']}) — {concluidas_semana}/{total_semana} concluídas"

    with st.expander(rotulo_expander, expanded=(semana_num == semana_atual)):
        st.markdown(f"**Foco:** {semana_info['foco']}")
        for _, row in df_semana.iterrows():
            tarefa_id = row["ID"]
            categoria = row["Categoria"]
            rotulo = f"[{categoria}] {row['Tarefa']}"
            st.checkbox(
                rotulo,
                value=bool(row["Concluido"]),
                key=f"chk_{tarefa_id}",
                on_change=marcar_tarefa,
                args=(tarefa_id,),
            )