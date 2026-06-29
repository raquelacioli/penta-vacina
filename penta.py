import streamlit as st
import pandas as pd
import numpy as np

# Configuração da página do Streamlit
st.set_page_config(page_title="monitoramento vacina_penta Raquel. Acioli", layout="wide")

# Login simples
VALID_USER = "raquelmlacioli@gmail.com"
VALID_PASSWORD = "teste"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "password" not in st.session_state:
    st.session_state.password = ""
if "login_error" not in st.session_state:
    st.session_state.login_error = ""

def login():
    if st.session_state.username == VALID_USER and st.session_state.password == VALID_PASSWORD:
        st.session_state.logged_in = True
        st.session_state.login_error = ""
    else:
        st.session_state.logged_in = False
        st.session_state.login_error = "Usuário ou senha incorretos"

if not st.session_state.logged_in:
    st.image("VIGIPENTA.png", width=800)
    st.title("🔐 Acesso ao Painel")
    st.text_input("E-mail", key="username")
    st.text_input("Senha", type="password", key="password")
    st.button("Entrar", on_click=login)
    if st.session_state.login_error:
        st.error(st.session_state.login_error)
    st.stop()

st.title("📊 Painel de Monitoramento - Vacinação Pentavalente")
st.image("VIGIPENTA.png", caption="VIGIPENTA", width=800)
st.markdown("Insira o banco de dados de vacinação para calcular automaticamente os indicadores de saúde.")

# Upload do arquivo (Aceita CSV ou Excel)
uploaded_file = st.file_uploader("Selecione o arquivo do banco de dados (.csv ou .xlsx)", type=["csv", "xlsx"])

if uploaded_file is not None:
    # Identificar formato e carregar os dados
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    required_columns = ['data_nascimento', 'penta_1a_dose', 'penta_2a_dose', 'penta_3a_dose', 'unidade_referencia', 'equipe_referencia']
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        st.error(f"O arquivo está sem as colunas necessárias: {', '.join(missing_columns)}")
        st.stop()
        
    # Limpeza inicial: remove linhas sem data de nascimento
    df = df.dropna(subset=['data_nascimento'])
    
    # Conversão das colunas para formato de Data correto
    df['data_nascimento'] = pd.to_datetime(df['data_nascimento'], errors='coerce')
    df['penta_1a_dose'] = pd.to_datetime(df['penta_1a_dose'], errors='coerce')
    df['penta_2a_dose'] = pd.to_datetime(df['penta_2a_dose'], errors='coerce')
    df['penta_3a_dose'] = pd.to_datetime(df['penta_3a_dose'], errors='coerce')
    
    # Cálculo das idades em dias na data de cada dose (Conforme solicitado)
    df['idade_dose1'] = (df['penta_1a_dose'] - df['data_nascimento']).dt.days
    df['idade_dose2'] = (df['penta_2a_dose'] - df['data_nascimento']).dt.days
    df['idade_dose3'] = (df['penta_3a_dose'] - df['data_nascimento']).dt.days
    
    # Cálculo dos intervalos entre as doses em dias
    df['intervalo_1_2'] = (df['penta_2a_dose'] - df['penta_1a_dose']).dt.days
    df['intervalo_2_3'] = (df['penta_3a_dose'] - df['penta_2a_dose']).dt.days

    # --- ANÁLISE DE DATAS EM BRANCO E ORDEM CRONOLÓGICA ---
    st.divider()
    st.subheader("📅 Análise das datas das doses")

    blank_1 = df['penta_1a_dose'].isna().sum()
    blank_2 = df['penta_2a_dose'].isna().sum()
    blank_3 = df['penta_3a_dose'].isna().sum()

    ordem_invalida_1_2 = ((df['penta_1a_dose'].notna() & df['penta_2a_dose'].notna()) & (df['penta_2a_dose'] < df['penta_1a_dose'])).sum()
    ordem_invalida_2_3 = ((df['penta_2a_dose'].notna() & df['penta_3a_dose'].notna()) & (df['penta_3a_dose'] < df['penta_2a_dose'])).sum()
    ordem_invalida_total = ordem_invalida_1_2 + ordem_invalida_2_3

    resumo_datas = pd.DataFrame({
        'Dose': ['penta_1a_dose', 'penta_2a_dose', 'penta_3a_dose'],
        'Datas em branco': [blank_1, blank_2, blank_3],
        '% em branco': [round(blank_1 / len(df) * 100, 2), round(blank_2 / len(df) * 100, 2), round(blank_3 / len(df) * 100, 2)]
    })

    resumo_ordem = pd.DataFrame({
        'Verificação': ['penta_2a_dose < penta_1a_dose', 'penta_3a_dose < penta_2a_dose'],
        'Registros inconsistentes': [ordem_invalida_1_2, ordem_invalida_2_3]
    })

    col_a, col_b, col_c = st.columns(3)
    col_a.metric('penta_1a_dose em branco', f'{blank_1} ({round(blank_1 / len(df) * 100, 1)}%)')
    col_b.metric('penta_2a_dose em branco', f'{blank_2} ({round(blank_2 / len(df) * 100, 1)}%)')
    col_c.metric('penta_3a_dose em branco', f'{blank_3} ({round(blank_3 / len(df) * 100, 1)}%)')

    if ordem_invalida_total > 0:
        st.warning(f'Foram encontradas {ordem_invalida_total} inconsistências na ordem cronológica das datas das doses.')
    else:
        st.success('As datas das doses estão em ordem crescente para todos os registros analisados.')

    st.dataframe(resumo_datas, use_container_width=True)
    st.dataframe(resumo_ordem, use_container_width=True)
    
    # --- APLICANDO AS REGRAS DOS INDICADORES ---
    
    # Indicador 1: >= 2 meses (60 dias) e < 1 ano (365 dias) com intervalo entre doses >= 60 dias
    df['ind1'] = (
        (df['idade_dose1'] >= 60) & (df['idade_dose1'] < 365) &
        (df['idade_dose2'] >= 60) & (df['idade_dose2'] < 365) &
        (df['idade_dose3'] >= 60) & (df['idade_dose3'] < 365) &
        (df['intervalo_1_2'] >= 60) & (df['intervalo_2_3'] >= 60)
    ).astype(int)
    
    # Indicador 2: Menores de 1 ano (< 365 dias) que fizeram as três doses
    df['ind2'] = (
        (df['idade_dose1'] >= 0) & (df['idade_dose1'] < 365) &
        (df['idade_dose2'] >= 0) & (df['idade_dose2'] < 365) &
        (df['idade_dose3'] >= 0) & (df['idade_dose3'] < 365)
    ).astype(int)
    
    # Indicador 3: Menores de 1 ano (< 365 dias) com registro da terceira dose
    df['ind3'] = ((df['idade_dose3'] >= 0) & (df['idade_dose3'] < 365)).astype(int)
    
    # --- VISÃO GERAL (CARD METRICS) ---
    st.subheader("📌 Indicadores Gerais Consolidados")
    
    total_nv = len(df)
    p1 = (df['ind1'].sum() / total_nv) * 100
    p2 = (df['ind2'].sum() / total_nv) * 100
    p3 = (df['ind3'].sum() / total_nv) * 100
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Nascidos Vivos (Total)", f"{total_nv:,}")
    
    # Função auxiliar para cor com base na meta de 80%
    def get_status_str(val):
        return "🟢 Atingiu a Meta" if val >= 80.0 else "🔴 Abaixo da Meta"
        
    col2.metric("Indicador 1 (Intervalo 60d)", f"{p1:.2f}%", help=get_status_str(p1))
    col3.metric("Indicador 2 (3 Doses < 1ano)", f"{p2:.2f}%", help=get_status_str(p2))
    col4.metric("Indicador 3 (Registro 3ª Dose)", f"{p3:.2f}%", help=get_status_str(p3))
    
    st.markdown(r"💡 *Meta estipulada:* **$\geq 80\%$**")
    
    # --- FILTROS E TABELAS POR UNIDADE / EQUIPE ---
    st.divider()
    st.subheader("🏢 Análise Detalhada por Unidade e Equipe")
    
    visao = st.radio("Agrupar análise por:", ["Unidade de Referência", "Equipe de Referência"])
    col_agrup = 'unidade_referencia' if visao == "Unidade de Referência" else 'equipe_referencia'
    
    # Agrupando dados dinamicamente
    df_grouped = df.groupby(col_agrup).agg(
        Nascidos_Vivos=('data_nascimento', 'count'),
        Ind1_Sucessos=('ind1', 'sum'),
        Ind2_Sucessos=('ind2', 'sum'),
        Ind3_Sucessos=('ind3', 'sum')
    ).reset_index()
    
    # Calculando as porcentagens por grupo
    df_grouped['Indicador 1 (%)'] = (df_grouped['Ind1_Sucessos'] / df_grouped['Nascidos_Vivos'] * 100).round(2)
    df_grouped['Indicador 2 (%)'] = (df_grouped['Ind2_Sucessos'] / df_grouped['Nascidos_Vivos'] * 100).round(2)
    df_grouped['Indicador 3 (%)'] = (df_grouped['Ind3_Sucessos'] / df_grouped['Nascidos_Vivos'] * 100).round(2)
    
    # Formatação visual da tabela destacando quem cumpre a meta
    def highlight_meta(val):
        color = '#d4edda' if val >= 80.0 else '#f8d7da'
        return f'background-color: {color}'
        
    st.markdown(f"A tabela abaixo exibe o percentual alcançado em cada indicador por **{visao}**:")
    
    # Exibindo tabela de resultados
    st.dataframe(
        df_grouped[[col_agrup, 'Nascidos_Vivos', 'Indicador 1 (%)', 'Indicador 2 (%)', 'Indicador 3 (%)']],
        use_container_width=True
    )
    
    # --- GRÁFICO DE COMPARAÇÃO ---
    st.divider()
    st.subheader("📊 Gráfico Comparativo")
    
    selected_ind = st.selectbox("Escolha o indicador para visualizar graficamente:", 
                                  ["Indicador 1 (%)", "Indicador 2 (%)", "Indicador 3 (%)"])
    
    # Ordenar dados para melhor visualização do gráfico de barras
    chart_data = df_grouped.sort_values(by=selected_ind, ascending=False).head(20)
    
    st.markdown(f"Top 20 maiores valores para o **{selected_ind}**:")
    st.bar_chart(data=chart_data, x=col_agrup, y=selected_ind, use_container_width=True)

else:
    st.info("Aguardando o upload do arquivo para gerar o painel automaticamente.")