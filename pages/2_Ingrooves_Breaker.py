import streamlit as st
import pandas as pd
from io import BytesIO

#----------------------------------
# Ingrooves Breaker
#----------------------------------

st.title("Ingrooves Breaker")
st.caption("Desconta 30% das receitas EUA do relatório Ingrooves e separa por artista.")

#----------------------------------
# Inicializa variáveis de estado da sessão
#----------------------------------
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'net_dollars' not in st.session_state:
    st.session_state.net_dollars = None
if 'net_withholding_total' not in st.session_state:
    st.session_state.net_withholding_total = None
if 'total_withheld' not in st.session_state:
    st.session_state.total_withheld = None
if 'processed_data' not in st.session_state:  # Adicionando esta linha
    st.session_state.processed_data = None
if 'show_summary_button' not in st.session_state:
    st.session_state.show_summary_button = False
if 'summary_df' not in st.session_state:
    st.session_state.summary_df = None
if 'total_geral_values' not in st.session_state:
    st.session_state.total_geral_values = None

#----------------------------------
# Função para resetar estado ao carregar novo arquivo
#----------------------------------

def reset_state():
    st.session_state.net_dollars = None
    st.session_state.net_withholding_total = None
    st.session_state.total_withheld = None
    st.session_state.processed_data = None
    st.session_state.show_summary_button = False
    st.session_state.summary_df = None
    st.session_state.total_geral_values = None
    st.session_state.uploaded_file = None

#----------------------------------
# Inicializa as variáveis no session_state
#----------------------------------

if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None

# Upload do arquivo
uploaded_file = st.file_uploader("Selecione o relatório Ingrooves", key="file_uploader")

# Se um novo arquivo for carregado, resetar o estado
if uploaded_file:
    if st.session_state.uploaded_file != uploaded_file:
        reset_state()
        st.session_state.uploaded_file = uploaded_file

# Leitura do arquivo e processamento
if uploaded_file is not None:
    sheet_name = 'Digital Sales Details'
    df = pd.read_excel(uploaded_file, sheet_name=sheet_name)

    # Exclui linha com Total para não somar em duplicidade
    df = df[~df['Sales Classification'].str.contains("Total", case=False, na=False)]

    # Soma da coluna Net Dollars after Fees antes do ajuste
    st.session_state.net_dollars = df['Net Dollars after Fees'].sum()

    if st.button('Processar desconto', type='primary'):

        # Aplica o desconto de 30% nas receitas dos EUA
        df['Net Dollars after Fees'] = df.apply(
            lambda row: row['Net Dollars after Fees'] - ((row['Net Dollars after Fees'] * 30) / 100)
            if row['Territory'] == 'United States' else row['Net Dollars after Fees'],
            axis=1
        )

        # Soma da coluna Net Dollars after Fees após o ajuste
        st.session_state.net_withholding_total = df['Net Dollars after Fees'].sum()

        # Valor total de withholding aplicado
        st.session_state.total_withheld = st.session_state.net_dollars - st.session_state.net_withholding_total

        # Após o processamento dos dados
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        writer.close()
        st.session_state.processed_data = output.getvalue()

        # Ativa o botão "Exibir resumo" após o processamento
        st.session_state.show_summary_button = True

# Verifica se há dados processados e mantém os valores na tela
if st.session_state.processed_data:

    # Exibe os valores processados
    st.write(f'O valor Net é **USD {st.session_state.net_dollars:,.2f}**')
    st.write(f'O total de withholding aplicado é **USD {st.session_state.total_withheld:,.2f}**')
    st.write(f':red[O valor Net menos withholding é **USD {st.session_state.net_withholding_total:,.2f}**]')
    

    st.divider()

    # Adiciona campo para a taxa de câmbio (FX rate)
    fx_rate = st.number_input("Adicione aqui a taxa de câmbio (FX rate)", value=0.0, format="%.4f")

    # Exibe o botão "Exibir resumo" apenas se o processamento foi realizado
    if st.session_state.show_summary_button:
        if st.button('Exibir resumo'):

            # Definir os grupos alvo para agrupamento por artista
            target_groups = ["Cláudio Noam", "Planta E Raiz", "Pollo", "Dom Silver", "Carlinhos Brown"]
            marcelo_menezes_keywords = ["Tchakabum", "Marcela Jardim", "Tubarão"]

            # Função para agrupar valores por artistas
            def group_artists(df, target_groups, marcelo_menezes_keywords, fx_rate):
                grouped_df = pd.DataFrame(columns=["Artist", "Total Net Dollars", "FX Rate", "Total BRL"])

                for artist in target_groups:
                    artist_group = df[df['Artist'].apply(lambda x: isinstance(x, str) and artist.lower() in x.lower())]
                    total_net_dollars = artist_group['Net Dollars after Fees'].sum()
                    total_brl = total_net_dollars * fx_rate

                    if not artist_group.empty:
                        grouped_df = pd.concat([grouped_df, pd.DataFrame([{"Artist": artist, "Total Net Dollars": round(total_net_dollars, 2), "FX Rate": fx_rate, "Total BRL": round(total_brl, 2)}])], ignore_index=True)

                condition = df['Artist'].apply(lambda x: isinstance(x, str) and any(keyword in x for keyword in marcelo_menezes_keywords))
                artist_group = df[condition]
                total_net_dollars = artist_group['Net Dollars after Fees'].sum()
                total_brl = total_net_dollars * fx_rate

                if not artist_group.empty:
                    grouped_df = pd.concat([grouped_df, pd.DataFrame([{"Artist": "Marcelo Menezes", "Total Net Dollars": round(total_net_dollars, 2), "FX Rate": fx_rate, "Total BRL": round(total_brl, 2)}])], ignore_index=True)

                total_net_dollars = df['Net Dollars after Fees'].sum()
                total_brl = total_net_dollars * fx_rate
                st.session_state.total_geral_values = {"Total Net Dollars": round(total_net_dollars, 2), "Total BRL": round(total_brl, 2)}

                return grouped_df

            # Agrupar os valores por artista e armazenar no session_state
            st.session_state.summary_df = group_artists(df, target_groups, marcelo_menezes_keywords, fx_rate)

            st.divider()

            if st.session_state.summary_df is not None:
                st.write("Agrupamento por artista:")
                st.dataframe(st.session_state.summary_df)

# Exibe os valores do total geral abaixo do DataFrame
if st.session_state.total_geral_values is not None and st.session_state.processed_data:
    st.markdown(
        f"### Total Geral\n"
        f"**Total Net Dollars:** USD {st.session_state.total_geral_values['Total Net Dollars']:,.2f}\n\n"
        f"**Total BRL:** BRL {st.session_state.total_geral_values['Total BRL']:,.2f}"
    )
