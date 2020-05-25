import streamlit as st
import pandas as pd
import os
import base64
import datetime as datetime
from bs4 import BeautifulSoup
import codecs
import re
from PIL import Image

def get_table_download_link(df):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}">Download csv file</a>'
    return href

def main():
    st.title('CSGO')
    st.subheader('Análise do status do player')

    #video = open('v.mp4','rb').read()
    #st.video(video)

    file  = st.file_uploader('Escolha a base de dados do seu perfil')
    st.info = ("Arquivo:{}".format(file))
    if file is not None:
        st.subheader('Analisando os dados...')
        soup = BeautifulSoup(file, "html.parser")

        perfil = soup.find("span", {"class": "profile_small_header_name"})
        nome = perfil.text
        numeroId = perfil.a['href'].split("/")[-1]

        st.subheader("Player: "+nome)

        #### Partidas : Mapa, Duração e Data
        partidas = []
        for csgo_scoreboard_inner_left in soup.find_all("table", {"class": "csgo_scoreboard_inner_left"}, 'tbody'):
            partidas.append(csgo_scoreboard_inner_left.text)

        mapa = []
        duracao = []
        data = []

        for i in range(0, len(partidas)):

            # MAPAS
            if len(partidas[i].split()[2]) == 10:
                mapa.append(partidas[i].split()[1])
                data.append(partidas[i].split()[2])
                duracao.append(partidas[i].split()[12])
            else:
                mapa.append(partidas[i].split()[1] + ' ' + partidas[i].split()[2])
                data.append(partidas[i].split()[3])
                duracao.append(partidas[i].split()[13])

        #### Partidas: Placar e Localização do Jogador
        teste = []
        Placar = []
        Localizacao = []
        for p in soup.find_all("table", {"class": "csgo_scoreboard_inner_right banchecker-formatted"}):
            teste.append(p)
            # Criacao do Placar
            Placar.append(re.findall(r'([0-9]+\s:\s[0-9]+)', p.text)[0])

            # Marcar se o jogador esta na parte de cima ou de baixo da tabela resultado
            if p.text.find(re.findall(r'([0-9]+\s:\s[0-9]+)', p.text)[0]) > p.text.find(nome):
                Localizacao.append("TOP")
            else:
                Localizacao.append("BOT")

        #### Partidas : Ping, Vítimas, Assistencias, Mortes, % de HS e Pontos
        ping = []
        vitimas = []
        assistencias = []
        mortes = []
        mvp = []
        taxa_de_HS = []
        pontos = []
        status = []

        for registro in soup.find_all("tr", {"data-steamid64": numeroId}):
            # Troca o "\xa0" por 0
            p = registro.text.replace("\xa0", "0")

            status.append(p)
            ping.append(p.split()[1])
            vitimas.append(p.split()[2])
            assistencias.append(p.split()[3])
            mortes.append(p.split()[4])
            mvp.append(p.split()[5])
            taxa_de_HS.append(p.split()[6])
            pontos.append(p.split()[7])

        #### Criação do DataFrame com os dados coletados do HTML
        result = pd.DataFrame({'Mapa': mapa, 'Duração': duracao, 'Data': data, 'Ping': ping, 'Vitimas': vitimas,
                               'Assistencias': assistencias, 'Ano-Mês':'','Ano':'',
                               'Mortes': mortes, 'MVP': mvp, '% de HS': taxa_de_HS, 'Pontos': pontos, 'Placar': Placar,
                               'Localizacao': Localizacao,
                               'Rounds Ganhos': "", 'Rounds Perdidos': "", 'Rounds Jogados': '', 'Resultado': ""})

        #### Criação de novas Colunas : Rounds Ganhos, Rounds Perdidos, Resultado da partida
        for i in range(0, len(result)):
            if result.Localizacao[i] == "TOP":
                result['Rounds Ganhos'][i] = int(result.Placar[i].split()[0])
                result['Rounds Perdidos'][i] = int(result.Placar[i].split()[2])
            else:
                result['Rounds Ganhos'][i] = int(result.Placar[i].split()[2])
                result['Rounds Perdidos'][i] = int(result.Placar[i].split()[0])

            result['Rounds Jogados'][i] = result['Rounds Perdidos'][i] + result['Rounds Ganhos'][i]

            if result['Rounds Ganhos'][i] == 16:
                result['Resultado'][i] = 'Vitória'
            elif result['Rounds Ganhos'][i] == 15:
                result['Resultado'][i] = 'Empate'
            else:
                result['Resultado'][i] = "Derrota"

        #### Padronizando MVP e % de HS (Tirar o char ★ e a %)
        for i in range(0, len(result)):

            if len(result['% de HS'][i]) != 1:
                result['% de HS'][i] = result['% de HS'][i][:-1]

            if '★' in result['MVP'][i]:
                if len(result['MVP'][i]) == 1:
                    result['MVP'][i] = 1
                else:
                    result['MVP'][i] = int(result['MVP'][i][1:])

        #### Criar uma lista com os dados que serao transformados em float
        colToFloat = ['Ping', 'Vitimas', 'Assistencias', 'Mortes', 'MVP', '% de HS', 'Pontos', 'Rounds Ganhos',
                      'Rounds Perdidos','Rounds Jogados']

        for i in colToFloat:
            result[[i]] = result[[i]].astype(int)

        #### Padronizar Data
        result['Data'] = result['Data'].apply(lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").strftime("%d-%m-%Y"))

        #### Padronizar Duracao
        result['Duração'] = result['Duração'].apply(lambda x: pd.to_timedelta('00:' + x))

        #Gerar Mes-Ano
        result['Ano-Mês'] = result['Data'].apply(lambda x : x.split('-')[2])+'-'+result['Data'].apply(lambda x : x.split('-')[1])
        result['Ano'] = result['Data'].apply(lambda x: x.split('-')[2])

        #### Remover coluna Localizacao
        result.drop(['Localizacao'], axis=1, inplace=True)

        ####
        result = pd.concat([result, pd.get_dummies(result[['Resultado']])], axis=1)

        #### Lista de mapas
        lista_mapas = result.Mapa.unique().tolist()

        #### Criando DF informações Gerais
        dfif = pd.DataFrame(result[result.describe().columns.tolist()].sum()).T

        dfif = dfif.drop(['% de HS'],axis=1)
        dfif['Jogo mais Recente'] = result['Data'][0]
        dfif['Jogo mais Antigo'] = result['Data'][result.shape[0] - 1]
        dfif['Quantidade de Jogos'] = result.shape[0]
        dfif['% de HS'] = format(round(result['% de HS'].mean(), 2)) + " %"

        ### Reordenando dfif
        dfif = dfif[['Quantidade de Jogos',
                     'Jogo mais Antigo',
                     'Jogo mais Recente',
                     'Duração',
                     'Vitimas',
                     'Assistencias',
                     'Mortes',
                     'MVP',
                     'Pontos',
                     '% de HS',
                     'Rounds Jogados',
                     'Rounds Ganhos',
                     'Rounds Perdidos',
                     'Resultado_Derrota',
                     'Resultado_Empate',
                     'Resultado_Vitória']]

        dfif = dfif.T.rename(columns={0: "Informações"})

        ##############################################################################################################

        st.sidebar.title('Menu')


        data_dim = st.sidebar.radio("", ('Informações Gerais', 'Estatística do '+nome,'Estatísticas dos Mapas' ))
        if data_dim == 'Informações Gerais':
            # st.subheader('Registros de '+result.Data[result.shape[0]-1]+' a '+result.Data[0])
            # st.subheader('Jogos: {}'.format(result.shape[0]))
            # st.subheader('Vitórias: {}'.format(result['Resultado_Vitória'].sum()))
            # st.subheader('Derrotas: {}'.format(result['Resultado_Derrota'].sum()))
            # st.subheader('Empates: {}'.format(result['Resultado_Empate'].sum()))
            # st.subheader('Horas Jogadas: {}'.format(result['Duração'].sum()))
            # st.subheader('Kills: {}'.format(result.Vitimas.sum()))
            # st.subheader('Assis: {}'.format(result.Assistencias.sum()))
            # st.subheader('Deaths: {}'.format(result.Mortes.sum()))
            # st.subheader('MVP: {}'.format(result.MVP.sum()))
            # st.subheader('Pontos: {}'.format(result.Pontos.sum()))
            # st.subheader('Rounds Jogados: {}'.format(result['Rounds Jogados'].sum()))
            # st.subheader('Rounds Ganhos: {}'.format(result['Rounds Ganhos'].sum()))
            # st.subheader('Rounds Perdidos: {}'.format(result['Rounds Perdidos'].sum()))
            st.table(dfif)


        elif data_dim == 'Estatística do '+nome:
            ano_ou_mes = st.radio("", ('Ano','Ano-Mês'))

            #if ano_ou_mes == 'Ano':
            #    st.text("Ano")
            #else:
            #    st.text('Ano-Mês')

            #Escolher se quer ver os valores pela soma ou pela media
            sum_ou_mean = st.radio("Escolha forma de avaliar", ('Soma', 'Média'))
            # se for soma, remove a % de HS
            if sum_ou_mean == 'Soma':
                #### Lista de Numerais
                col_num = result.drop(['Duração','% de HS','Ping'],axis=1).describe().columns.tolist()

            else:
                #### Lista de Numerais
                col_num =  result.drop(['Duração','Ping'],axis=1).describe().columns.tolist()

            #Seleciona os valores das colunas que ele quer ver
            selected_columns_names = st.multiselect("Selecionar as características", col_num)

            if st.button("Gerar Gráfico"):
                st.success("Generating Customizable Plot for {}".format(selected_columns_names))

                if sum_ou_mean == 'Soma':
                    cust_data = result.groupby(ano_ou_mes)[selected_columns_names].sum()

                else:
                    cust_data = result.groupby(ano_ou_mes)[selected_columns_names].mean()


                if cust_data is not None:
                    st.line_chart(cust_data)

        else:

            #ano_ou_mes = st.radio("", ('Ano', 'Ano-Mês'))

            #if ano_ou_mes == 'Ano':
            #    st.text("Ano")
            #else:
            #    st.text('Ano-Mês')

            map_contagem = result.groupby('Mapa')['Mapa'].count()

            # Escolher se quer ver os valores pela soma ou pela media
            sum_ou_mean = st.radio("Escolha forma de avaliar", ('Soma', 'Média'))
            # se for soma, remove a % de HS
            if sum_ou_mean == 'Soma':
                #### Lista de Numerais
                col_num = result.drop(['% de HS','Ping'],axis=1).describe().columns.tolist()
                map_soma = result.groupby('Mapa')[col_num].sum()
                map_calculo = map_soma

            else:
                #### Lista de Numerais
                col_num = result.drop(['Ping'],axis=1).describe().columns.tolist()
                map_media = result.groupby('Mapa')[col_num].mean().round(2)
                map_calculo = map_media

            for m in lista_mapas:
                #Criando a caption
                Frase = ''
                for i, c in enumerate(map_calculo.loc[m]):
                    Frase += '\n'+map_calculo.loc[m].index[i] + ': {}'.format(c)

                img = Image.open(m+'.jpg')
                st.image(img,width = 200,
                         caption= 'Quantidade de jogos: {}'.format(map_contagem[m]),
                         use_column_width=True)
                st.table(map_calculo.loc[m])



        #if st.sidebar.checkbox("Informações Gerais"):
            #number = st.number_input("Number of Rows to View")
            #st.dataframe(df.head(number))


if __name__ == '__main__':
	main()