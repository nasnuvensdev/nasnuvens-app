import streamlit as st
import pandas as pd
from io import BytesIO

#----------------------------------
# Withholding App
#----------------------------------

title = st.title("Withholding App")
descritivo = st.caption("Desconta 30% das receitas EUA")
#----------------------------------
# Upload do arquivo
#----------------------------------

uploaded_file = st.file_uploader("Upload file")
sheet_name = 'Digital Sales Details'

#----------------------------------
# Inicializa as variáveis em session_state para manter os valores após o download
#----------------------------------

if 'net_dollars' not in st.session_state:
    st.session_state.net_dollars = None
if 'net_withholding_total' not in st.session_state:
    st.session_state.net_withholding_total = None
if 'total_withheld' not in st.session_state:
    st.session_state.total_withheld = None
if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None
if 'show_summary_button' not in st.session_state:
    st.session_state.show_summary_button = False  # Controla se o botão "Exibir resumo" aparece
if 'summary_df' not in st.session_state:
    st.session_state.summary_df = None  # Armazena o DataFrame do resumo
if 'total_geral_values' not in st.session_state:
    st.session_state.total_geral_values = None  # Armazena os valores do total geral

#----------------------------------
# Leitura do arquivo
#----------------------------------

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, sheet_name)

    #----------------------------------
    # Exclui linha com Total para não somar em duplicidade
    #----------------------------------

    df = df[~df['Sales Classification'].str.contains("Total", case=False, na=False)]

    #----------------------------------
    # Soma da coluna Net Dollars after Fees antes do ajuste
    #----------------------------------

    st.session_state.net_dollars = df['Net Dollars after Fees'].sum()
    
    if st.button('Processar desconto', type='primary'):

        #----------------------------------
        # Função principal
        #----------------------------------

        df['Net Dollars after Fees'] = df.apply(
            lambda row: row['Net Dollars after Fees'] - ((row['Net Dollars after Fees'] * 30) / 100)
            if row['Territory'] == 'United States' else row['Net Dollars after Fees'],
            axis=1
        )

        #----------------------------------
        # Soma da coluna Net Dollars after Fees após o ajuste
        #----------------------------------

        st.session_state.net_withholding_total = df['Net Dollars after Fees'].sum()

        #----------------------------------
        # Valor total de withholding aplicado
        #----------------------------------

        st.session_state.total_withheld = st.session_state.net_dollars - st.session_state.net_withholding_total

        #----------------------------------
        # Após o processamento dos dados
        #----------------------------------

        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        writer.close()  # Use 'close()' em vez de 'save()'
        st.session_state.processed_data = output.getvalue()

        #----------------------------------
        # Ativa o botão "Exibir resumo" após o processamento
        #----------------------------------
        st.session_state.show_summary_button = True


#----------------------------------
# Verifica se há dados processados para download e mantém os valores na tela
#----------------------------------

if st.session_state.processed_data:
    
    #----------------------------------
    # Exibe os valores processados novamente
    #----------------------------------
    st.write(f'O valor Net é **USD {st.session_state.net_dollars:,.2f}**')
    st.write(f'O valor Net menos withholding é **USD {st.session_state.net_withholding_total:,.2f}**')
    st.write(f'O total de withholding aplicado é **USD {st.session_state.total_withheld:,.2f}**')

    #----------------------------------
    # Botão para download do arquivo processado
    #----------------------------------
    st.download_button(
        label="Baixar arquivo processado",
        data=st.session_state.processed_data,
        file_name="Arquivo_Processado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.divider()
    
    #----------------------------------
    # Adiciona campo para a taxa de câmbio (FX rate)
    #----------------------------------

    fx_rate = st.number_input("Adicione aqui a taxa de câmbio (FX rate)", value=0.0, format="%.4f")

    #----------------------------------
    # Exibe o botão "Exibir resumo" apenas se o processamento do desconto foi realizado
    #----------------------------------
    if st.session_state.show_summary_button:
        if st.button('Exibir resumo'):

            #----------------------------------
            # Definir os grupos alvo para agrupamento por artista
            #----------------------------------

            target_groups = ["Cláudio Noam", "Planta E Raiz", "Pollo", "Dom Silver", "Carlinhos Brown"]
            marcelo_menezes_keywords = ["Tchakabum", "Marcela Jardim", "Tubarão"]

            #----------------------------------
            # Função para agrupar valores por artistas
            #----------------------------------
            def group_artists(df, target_groups, marcelo_menezes_keywords, fx_rate):

                #----------------------------------
                # Cria um novo dataframe para armazenar os valores agrupados
                #----------------------------------
                grouped_df = pd.DataFrame(columns=["Artist", "Total Net Dollars", "FX Rate", "Total BRL"])

                #----------------------------------
                # Agrupar pelos artistas nos target_groups
                #----------------------------------
                for artist in target_groups:
                    artist_group = df[df['Artist'].apply(lambda x: isinstance(x, str) and artist.lower() in x.lower())]
                    total_net_dollars = artist_group['Net Dollars after Fees'].sum()
                    total_brl = total_net_dollars * fx_rate

                    #----------------------------------
                    # Verifica se há valores antes de adicionar ao DataFrame
                    #----------------------------------
                    if not artist_group.empty:
                        grouped_df = pd.concat([grouped_df, pd.DataFrame([{"Artist": artist, "Total Net Dollars": round(total_net_dollars, 2), "FX Rate": fx_rate, "Total BRL": round(total_brl, 2)}])], ignore_index=True)

                #----------------------------------
                # Agrupar pelo grupo de Marcelo Menezes
                #----------------------------------
                condition = df['Artist'].apply(lambda x: isinstance(x, str) and any(keyword in x for keyword in marcelo_menezes_keywords))
                artist_group = df[condition]
                total_net_dollars = artist_group['Net Dollars after Fees'].sum()
                total_brl = total_net_dollars * fx_rate

                #----------------------------------
                # Verifica se há valores antes de adicionar ao DataFrame
                #----------------------------------
                if not artist_group.empty:
                    grouped_df = pd.concat([grouped_df, pd.DataFrame([{"Artist": "Marcelo Menezes", "Total Net Dollars": round(total_net_dollars, 2), "FX Rate": fx_rate, "Total BRL": round(total_brl, 2)}])], ignore_index=True)

                #----------------------------------
                # Calcular o total geral e armazenar no session_state
                #----------------------------------
                total_net_dollars = df['Net Dollars after Fees'].sum()
                total_brl = total_net_dollars * fx_rate
                st.session_state.total_geral_values = {"Total Net Dollars": round(total_net_dollars, 2), "Total BRL": round(total_brl, 2)}

                return grouped_df

            #----------------------------------
            # Agrupar os valores por artista e armazenar no session_state
            #----------------------------------
            st.session_state.summary_df = group_artists(df, target_groups, marcelo_menezes_keywords, fx_rate)

            st.divider()

            #----------------------------------
            # Exibe o DataFrame formatado
            #----------------------------------
            if st.session_state.summary_df is not None:
                st.write("Agrupamento por artista:")
                st.dataframe(st.session_state.summary_df)

#----------------------------------
# Exibe os valores do total geral abaixo do DataFrame com destaque
#----------------------------------
if st.session_state.total_geral_values is not None:
    st.markdown(
        f"### Total Geral\n"
        f"**Total Net Dollars:** USD {st.session_state.total_geral_values['Total Net Dollars']:,.2f}\n\n"
        f"**Total BRL:** BRL {st.session_state.total_geral_values['Total BRL']:,.2f}"
    )
#----------------------------------
