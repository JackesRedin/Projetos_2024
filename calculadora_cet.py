import pandas as pd
import numpy as np
import numpy_financial as npf
import streamlit as st
from datetime import datetime, timedelta, date
import locale
from dateutil.relativedelta import relativedelta
import json
import requests
from GoogleNews import GoogleNews
import time

st.set_page_config(
    page_title="Simmulador de Capital de Giro",
    page_icon=":fast_forward:",
    layout="wide",    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/JackesRedin',
        'Report a bug': "https://github.com/JackesRedin",
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
#codigo celic api 1178 	Taxa de juros - Selic anualizada base 252
#codigo celic api 432 Taxa de juros - Meta Selic definida pelo Copom
#codigo IPCA 433
#codigo IGP-M 189
#codigo 1 - Taxa de câmbio - Livre - Dólar americano (venda) - diário R$/US$ https://www.bcb.gov.br/estatisticas/detalhamentoGrafico/graficosestatisticas/cambio
# 20635

# api_selic = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1178/dados?formato=json&dataInicial=01/01/2024"



@st.cache_data
def consulta_api(codigo_bacen):
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_bacen}/dados?formato=json&dataInicial=01/01/2024"
    global dados_bacen
    retorno = requests.get(url=url)
    dados_bacen = retorno.json()

    return dados_bacen

#armazenando consultas api bacen
with st.spinner("Aguarde... Atualizando Api Bacen"):
    dados_selic = consulta_api(432)
    time.sleep(1)
    dados_ipca = consulta_api(433)
    dados_igpm = consulta_api(189)
    dados_usd = consulta_api(1)

@st.cache_data    
def consulta_news(assunto):
    
    googlenews = GoogleNews(period='d')
    googlenews.clear()
    
    googlenews.set_lang("pt")
    #limpa consulta anterior
        
    googlenews.search(assunto)
    
    news = googlenews.result()
    
    return news
    


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
usd_atual = np.round(float(dados_usd[-1]["valor"]),2)
usd_dt = dados_usd[-1]["data"]
usd_anterior = np.round(float(dados_usd[-2]["valor"]), 2)


# Calculando a variação
variacao_selic = selic_atual - selic_anterior
variacao_usd = np.round((usd_atual - usd_anterior), 2)


#dados para minigráficos


df_selic = pd.DataFrame(dados_selic)
df_selic["valor"] = df_selic["valor"].astype(float)
df_selic['data'] = pd.to_datetime(df_selic['data'], format="%d/%m/%Y")
df_selic = df_selic.set_index("data")

df_usd = pd.DataFrame(dados_usd)
df_usd["valor"] = df_usd["valor"].astype(float)
df_usd['data'] = pd.to_datetime(df_usd['data'], format="%d/%m/%Y")
df_usd = df_usd.set_index("data")

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




with st.expander("Índices de Mercado", icon="📈"):
    coll1, coll2, coll3, coll4 = st.columns(4)
    #quadrinhos  de indicadores e métricas
    # coll1.metric(label="Taxa Meta Selic Anterior¹", value=f"{selic_anterior}%")
    coll1.metric(label="Taxa Meta Selic Atual¹", value=f"{selic_atual}%", delta=f"{variacao_selic}%")
    coll1.caption("¹% a.a., dados diários ")
    
    coll2.metric(label=f"US$ {usd_dt}", value=f"{usd_atual}", delta=f"{variacao_usd}", delta_color = "inverse")   
    
    coll3.metric(label=f"IPCA Índice Geral {ipca_atual_dt}", value=f"{ipca_atual}%")
    
    coll4.metric(label=f"IGP-M {ipca_atual_dt}", value=f"{igpm_atual}%")
    
    st.write("**Notícias**")


    #ATUALIZAR noticias para container

    #tabela para ordenar noticias
    # tabela_news = pd.DataFrame(columns=["title", "media", "date", "desc", "link"])
    tabela_news = []
    
    opcoes_busca = ["Mercado", "Combustiveis", "Juros", "Finanças", "Tecnologia", "Esportes", "Educação"]
    
    colll1, colll2 = st.columns(2)

    # Inicializar a lista de opções de busca no session state
    if 'opcoes_busca' not in st.session_state:
        st.session_state.opcoes_busca = ["Economia", "Mercado", "Combustiveis", "Juros", "Finanças", "Tecnologia", "Esportes", "Educação"]
        
    # Inicializar a lista de seleção padrão (termos previamente selecionados)
    if 'default_busca' not in st.session_state:
        st.session_state.default_busca = st.session_state.opcoes_busca[1:3]

    novo_assunto = colll1.text_input("*Digite para adicionar uma palavra na lista:*")
    
    # Se houver um novo assunto e ele não estiver na lista, adicioná-lo e atualizar o default
    if novo_assunto and novo_assunto not in st.session_state.opcoes_busca:
        st.session_state.opcoes_busca.insert(0, novo_assunto)
        # Atualizar os termos padrão com o novo assunto
        st.session_state.default_busca = [novo_assunto] + st.session_state.default_busca[:2]  # Manter os dois últimos defaults anteriores

    # Exibir o multiselect com as opções atualizadas
    busca_news = colll1.multiselect(
        "*Selecione os assuntos das notícias*",
        options=st.session_state.opcoes_busca,
        default=st.session_state.default_busca,
        max_selections=5
    )

   
    # st.write(busca_news)        


    # ajustar lOOP INTERATIVO
      
    # for i in busca_news:
    #     st.write(i)
    
    #     st.write(busca_news[i]) 
    #     time.sleep(1) 
      
            
    # mercado = consulta_news("mercado financeiro")
    # juros = consulta_news("juros")
    # combustivel = consulta_news("combustivel") 
    # busca = consulta_news(busca_news)
    
    
    for assunto in busca_news:
            
        busca = consulta_news(assunto) 
          
        for i in range(1, 3):
            if busca_news:
                titulo = busca[i]["title"]
                fonte = busca[i]["media"]
                quando = busca[i]["date"]
                noticia = busca[i]["desc"]
                link = busca[i]["link"]
                         
                tabela_news.append([titulo, fonte, quando, noticia, link, assunto])
                pass
            
                    
        
    df_news = pd.DataFrame(tabela_news, columns=["Título", "Fonte", "Quando", "Noticia", "Link", "Assunto"])
    
    # ajusta link
    df_news['Link'] = df_news['Link'].apply(lambda x: x.split('&')[0])
    
    
    # st.write(df_news) #COMENTAR   


     
    
    conteiner_vazio = st.container(height=400)
    
    for index, row in df_news.iterrows():
        with conteiner_vazio:
            link1 = row["Link"]
            
            st.write(f'''{row["Assunto"]}: **{row["Título"]}**   -  
                     {row["Noticia"]}      *{row["Quando"]}*
                    
                                    ''')
            st.link_button(f"Link: {row["Fonte"]}", link1)
    
    
    indice_bacen = ("Selic", "US$", "IPCA/IGP-M")

    
    # indice_bacen = st.selectbox(f"Indicador Bacen", indice_bacen)

    if indice_bacen == "Selic":
        base_graf = df_selic
        
    elif indice_bacen == "US$":
        base_graf = df_usd

    elif indice_bacen == "IPCA/IGP-M":
        base_graf = df_unificado        
        #mostra grafico na barra lateral
    # st.sidebar.line_chart(base_graf, height=200 )
    # st.line_chart(base_graf, height=200 )
            
            
    
    
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

valor_total_contrato = np.round(valor_parcela*parcelas, 2)


col1, col2, col3 = st.columns(3)
col1.markdown(f"*Valor Total Contrato:* **{valor_total_contrato:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
# col1.markdown(f"*Valor Total Financiado:* **{vlr_total_financiado:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
# col1.write(f"*Valor Financiado:* **{vlr_financiado:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
col1.write(f"*Valor Parcela:* **{valor_parcela:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))
# col1.write(f"Valor Total iof normal: {total_iof_normal:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
# col1.write(f"vlr total iof adicional: {total_iof_adicional:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

col2.markdown(f"*Valor IOF Total:* **{total_iof_total:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))


#multi seleção de opções
#st.sidebar.multiselect("teste", dias_iof)

# Construindo o DataFrame
tabela_parcelas = pd.DataFrame({
    "Nº Parcela": range(1, parcelas + 1),
    "Dt Vencimento": dt_vencimentos,
    "Dias IOF": dias_iof,
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
tabela_parcelas["Valor Principal"] = tabela_parcelas["Nº Parcela"].apply(calcular_vlr_principal_parcela)
tabela_parcelas["Valor de Juros"] = tabela_parcelas["Valor Parcela"] - tabela_parcelas["Valor Principal"]
tabela_parcelas["Saldo Devedor"] = np.round(vlr_total_financiado - tabela_parcelas["Valor Principal"].cumsum(), 2)

vlr_total_juros = np.round(sum(tabela_parcelas["Valor de Juros"]), 2)
col1.markdown(f"*Valor Total de Juros:* **{vlr_total_juros:,.2f}**".replace(",", "X").replace(".", ",").replace("X", "."))

# Criar fluxos de caixa
fluxos_de_caixa = [-valor_emprestimo] + [valor_parcela]*parcelas
#st.write(fluxos_de_caixa)  

# Calcular a TIR (Taxa Interna de Retorno) para o CET mensal
cet_mensal = npf.irr(fluxos_de_caixa)

# Converter para CET anual
cet_anual = (1 + cet_mensal) ** 12 - 1

# Exibir os resultados
col2.markdown(f"CET mensal: **{cet_mensal:.2%}**")
col2.markdown(f"CET anual: **{cet_anual:.2%}**")

tabela_parcelas.set_index("Nº Parcela", inplace=True)
#tabela_parcelas.reset_index(drop=True, inplace=True)



# Função para formatar os valores numéricos no padrão brasileiro
def formato_brazeiro(value):
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Aplicar a função apenas nas colunas numéricas 'col1' e 'col2'
tabela_parcelas[["Valor Principal de IOF","Valor IOF Normal",
                 "Valor IOF Adicional","Valor Principal",
                 "Valor de Juros","Valor Parcela",
                 "Saldo Devedor"]] = tabela_parcelas[["Valor Principal de IOF","Valor IOF Normal",
                                                      "Valor IOF Adicional","Valor Principal",
                                                      "Valor de Juros","Valor Parcela",
                                                      "Saldo Devedor"]].applymap(formato_brazeiro)


tabela_parcelas = tabela_parcelas.drop(columns=["Valor Principal de IOF","Valor IOF Normal","Valor IOF Adicional"])
tabela_parcelas['Dt Vencimento'] = pd.to_datetime(tabela_parcelas['Dt Vencimento']) 
tabela_parcelas['Dt Vencimento'] = tabela_parcelas['Dt Vencimento'].dt.strftime("%d/%m/%Y")

st.dataframe(tabela_parcelas, height=600)


# "Valor Principal de IOF","Valor IOF Normal","Valor IOF Adicional","Valor Principal","Valor de Juros","Valor Parcela","Saldo Devedor"



st.markdown(''' 
            
            
            
            
            ''')

"---"
st.markdown(''' 
            
            
            
            
            ''')
st.caption("Desenvolido por :blue[Jackes Redin] (https://github.com/JackesRedin)")




    
    