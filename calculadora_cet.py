import pandas as pd
import numpy as np
import numpy_financial as npf
import streamlit as st
from datetime import datetime, timedelta, date
import locale
from dateutil.relativedelta import relativedelta
import json
import requests

st.set_page_config(
    page_title="Simmulador de Capital de Giro",
    page_icon=":fast_forward:",
    layout="wide",    initial_sidebar_state="expanded",
    menu_items={
        # 'Get Help': 'https://www.google.com',
        # 'Report a bug': "https://www.google.com",
        'About': "# Simulador de Capital de Giro - V1 *by JR*"
    }
)

#cabeçalhos
st.sidebar.header("Simulação Capital de Giro	:fast_forward:")



#CONSULTA API BANCO CENTRAL
#O serviço permite também recuperar os N últimos valores de uma determinada série:
#
#https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_serie}/dados/ultimos/{N}?formato=json
#https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json&dataInicial=01/01/2024
#codigo celic api 1178 dia
#codigo celic api 432 META
#codigo IPCA 433
#codigo IGP-M 189


# api_selic = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1178/dados?formato=json&dataInicial=01/01/2024"


@st.cache_data
def consulta_api(codigo_bacen):
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_bacen}/dados?formato=json&dataInicial=01/01/2023"
    global dados_bacen
    retorno = requests.get(url=url)
    dados_bacen = retorno.json()

    return dados_bacen

#armazenando consultas api bacen

dados_selic = consulta_api(1178)
dados_ipca = consulta_api(433)
dados_igpm = consulta_api(189)

#selic

ultima_selic = dados_selic[-1]

valor_anterior_diferente = None

selic_atual = ultima_selic["valor"]  # Valor atual da Taxa Selic

for dado in reversed(dados_selic):
    if dado['valor'] != selic_atual:
        valor_anterior_diferente = dado
        break
    
selic_atual = float(selic_atual)
selic_anterior = float(valor_anterior_diferente["valor"])  # Valor anterior da Taxa Selic

#dados para minigráficos


df_selic = pd.DataFrame(dados_selic)
df_selic["valor"] = df_selic["valor"].astype(float)
df_selic['data'] = pd.to_datetime(df_selic['data'], format="%d/%m/%Y")
df_selic = df_selic.set_index("data")

df_ipca = pd.DataFrame(dados_ipca)
df_ipca["valor"] = df_ipca["valor"].astype(float)
df_ipca['data'] = pd.to_datetime(df_ipca['data'], format="%d/%m/%Y")
df_ipca = df_ipca.set_index("data")

df_igpm = pd.DataFrame(dados_igpm)
df_igpm["valor"] = df_igpm["valor"].astype(float)
df_igpm['data'] = pd.to_datetime(df_igpm['data'], format="%d/%m/%Y")
df_igpm = df_igpm.set_index("data")

#unindo ipca e igpm
df_ipca.rename(columns={"valor": "IPCA"}, inplace=True)
df_igpm.rename(columns={"valor": "IGP-M"}, inplace=True)

df_unificado = pd.merge(df_igpm, df_ipca, on="data", how="outer")

ipca_atual = df_unificado["IPCA"][-1]
ipca_atual_dt = df_unificado.index[-1]
igpm_atual = df_unificado["IGP-M"][-1]
ipca_atual_dt = pd.to_datetime(ipca_atual_dt).strftime('%d/%m/%Y')

# Calculando a variação
variacao_selic = selic_atual - selic_anterior

with st.expander("Índices de Mercado", icon="📈"):
    coll1, coll2, coll3, coll4 = st.columns(4)
    #quadrinhos  de indicadores e métricas
    coll1.metric(label="Taxa Selic Anterior", value=f"{selic_anterior}%")
    coll2.metric(label="Taxa Selic Atual", value=f"{selic_atual}%", delta=f"{variacao_selic}%")
    coll3.metric(label=f"IPCA {ipca_atual_dt}", value=f"{ipca_atual}%")
    coll4.metric(label=f"IGP-M {ipca_atual_dt}", value=f"{igpm_atual}%")

st.header("Resultado da Simulação")


#valores de entrada - barra lateral
valor_emprestimo = st.sidebar.number_input("Valor do Empréstimo", value= 129918.46,
                                           placeholder="Digite o valor inicial", 
                                           help = "Valor inicial da Simulação", 
                                           ) #format="%0.2f"
taxa_am = st.sidebar.number_input("Taxa ao mês", value=2.7, placeholder="2,7", help="%taxa Ao Mês")
taxa_am = taxa_am/100
parcelas = st.sidebar.number_input("Parcelas", value=18, placeholder="12", step=1, max_value=60)
tac = st.sidebar.number_input("TAC", value=3000, placeholder="1000", step=100)
dt_inicio = st.sidebar.date_input("Data Empréstimo", format="DD/MM/YYYY" ) 

st.sidebar.divider()
st.sidebar.subheader("Gráfico")


indice_bacen = ("Selic", "IPCA/IGP-M")

indice_bacen = st.sidebar.selectbox(f"Indicador Bacen", indice_bacen)

if indice_bacen == "Selic":
    base_graf = df_selic

elif indice_bacen == "IPCA/IGP-M":
    base_graf = df_unificado


#mostra grafico na barra lateral
st.sidebar.line_chart(base_graf, height=200 )

#dados fixos
iof_dia = 0.000041
iof_max = 0.0150  #limitador de iof aplicada qdo a parcela ultrapassa o 365 dia
iof_add = 0.0038 #iof adicional

#dados calculados
#valor financiado
vlr_financiado = np.round(valor_emprestimo + tac, 2) 

vencimento = dt_inicio + relativedelta(months=1)

pmt = npf.pmt(taxa_am, parcelas, -vlr_financiado)


def iofnormal(dias):
    if dias > 365:
        vlr_iof_normal = valor_parcela * iof_max
    else:
        vlr_iof_normal = valor_parcela * (iof_dia * dias)
        
    return vlr_iof_normal   

#listas com informações
dt_vencimentos = []
dias_iof = []
vlr_principal_iof = []
vlr_iof_normal = []
vlr_iof_adicional = []
vlr_principal = []
vlr_juros = []
vlr_parcela = []
saldo_devedor = []



#loop para ajustar valor de cada parcela
for i in range(1, parcelas+1):
    #atualiza data de vencimento
    dias = (vencimento - dt_inicio).days
    
    # Calculando o valor da parcela (PMT)
    valor_parcela = npf.ppmt(taxa_am, i, parcelas, -vlr_financiado) #vlor principal iof
    
    calc_iof_normal = iofnormal(dias)
    
    calc_iof_adicional = valor_parcela*iof_add
    
    juros = 0 #ATUALIZAR
    
    
    #adicionando dados nas listas
    dt_vencimentos.append(vencimento)
    dias_iof.append(dias)
    vlr_principal_iof.append(np.round(valor_parcela,2))
    vlr_iof_normal.append(np.round(calc_iof_normal,2))
    vlr_iof_adicional.append(np.round(calc_iof_adicional,2))
    vlr_juros.append(0)
    
    
    #atualiza dt_vencimento
    vencimento = vencimento + relativedelta(months=1)


#totais
total_iof_normal = np.round(sum(vlr_iof_normal), 2)
total_iof_adicional = np.round(sum(vlr_iof_adicional), 2)
total_iof = total_iof_normal + total_iof_adicional

total_iof_total = np.round((vlr_financiado*total_iof)/(vlr_financiado-total_iof), 2)

vlr_total_financiado = np.round(tac + valor_emprestimo + total_iof_total, 2)

valor_parcela = np.round(npf.pmt(taxa_am, parcelas, -vlr_total_financiado), 2)


valor_principal = npf.ppmt(taxa_am, i, parcelas, -vlr_financiado)




col1, col2, col3, col4 = st.columns(4)
col1.markdown(f"*Valor Total Financiado:* **{vlr_total_financiado:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
# col1.write(f"*Valor Financiado:* **{vlr_financiado:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
col1.write(f"*Valor Parcela:* **{valor_parcela:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
# col1.write(f"Valor Total iof normal: {total_iof_normal:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
# col1.write(f"vlr total iof adicional: {total_iof_adicional:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

col2.markdown(f"*Valor IOF Total:* **{total_iof_total:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))


#multi seleção de opções
#st.sidebar.multiselect("teste", dias_iof)

# Construindo o DataFrame
tabela_parcelas = pd.DataFrame({
    "Número da Parcela": range(1, parcelas + 1),
    "Data de Vencimento": dt_vencimentos,
    "Dias Cobrados IOF": dias_iof,
    "Valor Principal de IOF": vlr_principal_iof,
    "Valor IOF Normal": vlr_iof_normal,
    "Valor IOF Adicional": vlr_iof_adicional,
    "Valor Principal": 0,
    "Valor de Juros": 0,
    "Valor Parcela": valor_parcela,
    "Saldo Devedor": 0
})

# Função para calcular o valor do principal da parcela usando o número da parcela
def calcular_vlr_principal_parcela(numero_parcela):
    return np.round(npf.ppmt(taxa_am, numero_parcela, parcelas, -vlr_total_financiado), 2)


# Aplicar a função diretamente na coluna "Número da Parcela" usando apply
tabela_parcelas["Valor Principal"] = tabela_parcelas["Número da Parcela"].apply(calcular_vlr_principal_parcela)
tabela_parcelas["Valor de Juros"] = tabela_parcelas["Valor Parcela"] - tabela_parcelas["Valor Principal"]
tabela_parcelas["Saldo Devedor"] = np.round(vlr_total_financiado - tabela_parcelas["Valor Principal"].cumsum(), 2)

vlr_total_juros = np.round(sum(tabela_parcelas["Valor de Juros"]), 2)
col2.markdown(f"*Valor Total de Juros:* **{vlr_total_juros:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))

# Criar fluxos de caixa
fluxos_de_caixa = [-valor_emprestimo] + [valor_parcela]*parcelas
#st.write(fluxos_de_caixa)

# Calcular a TIR (Taxa Interna de Retorno) para o CET mensal
cet_mensal = npf.irr(fluxos_de_caixa)

# Converter para CET anual
cet_anual = (1 + cet_mensal) ** 12 - 1

# Exibir os resultados
col3.markdown(f"CET mensal: **{cet_mensal:.2%}**")
col3.markdown(f"CET anual: **{cet_anual:.2%}**")

tabela_parcelas.set_index("Número da Parcela", inplace=True)
#tabela_parcelas.reset_index(drop=True, inplace=True)


st.dataframe(tabela_parcelas)



