import streamlit as st
import pandas as pd
from io import BytesIO

#----------------------------------
# Função para ajustar nomes dos arquivos, mantendo o nome original e adicionando o sufixo
#----------------------------------
def adjust_file_name(file_name):
    suffix = "_withholding_excluded"
    return f"{file_name}{suffix}.xlsx"

#----------------------------------
# Withholding Calculator
#----------------------------------
st.title("Withholding Calculator")
st.caption("Desconta 30% das receitas dos EUA.")

#----------------------------------
# Seleção do relatório
#----------------------------------
report_option = st.selectbox(
    'Selecione o relatório',
    (
        'The Orchard (Europa)',
        'Ingrooves',
        'Onerpm'
    )
)
#----------------------------------
# Upload do arquivo
#----------------------------------
uploaded_file = st.file_uploader("Faça o upload do arquivo Excel")

if uploaded_file is not None:

    #----------------------------------
    # Nome do arquivo de upload
    #----------------------------------
    original_file_name = uploaded_file.name.split(".")[0]

    #----------------------------------
    # Leitura do arquivo com base na opção selecionada
    #----------------------------------
    if report_option == 'The Orchard (Europa)':
        df = pd.read_excel(uploaded_file)

    elif report_option == 'Ingrooves':
        sheet_name = 'Digital Sales Details'
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)

    elif report_option == 'Onerpm':
        xls = pd.ExcelFile(uploaded_file)
        required_sheets = ['Masters', 'Youtube Channels', 'Shares In & Out']

    #----------------------------------
    # Inicializa dicionários para armazenar os totais por moeda e share-out
    #----------------------------------
    total_by_currency = {}
    share_out_by_currency = {}

    #----------------------------------
    # Processamento dos dados
    #----------------------------------
    if st.button('Processar desconto', type='primary'):

        #----------------------------------
        # Processamento THE ORCHARD
        #----------------------------------
        if report_option == 'The Orchard (Europa)':
            net_total = df['Label Share Net Receipts'].sum()

            # Aplica a fórmula de withholding diretamente na coluna original
            df['Label Share Net Receipts'] = df.apply(
                lambda row: row['Label Share Net Receipts'] - ((row['Label Share Net Receipts'] * 30) / 100)
                if row['Territory'] == 'USA' else row['Label Share Net Receipts'],
                axis=1
            )

            withholding_total = df['Label Share Net Receipts'].sum()
            total_withheld = net_total - withholding_total

            # Exibe os resultados
            st.write(f'O valor Net é **USD {net_total:,.2f}**')
            st.write(f'O valor Net menos withholding é **USD {withholding_total:,.2f}**')
            st.write(f'O total de withholding aplicado é **USD {total_withheld:,.2f}**')

            # Preparar o arquivo para download
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, index=False)
            writer.close()

            st.download_button(
                label="Baixar arquivo processado",
                data=output.getvalue(),
                file_name=adjust_file_name(original_file_name),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        #----------------------------------
        # Processamento INGROOVES
        #----------------------------------
        elif report_option == 'Ingrooves':

            # Filtra a linha de total para não somar em duplicidade
            df = df[~df['Sales Classification'].str.contains("Total", case=False, na=False)]

            net_total = df['Net Dollars after Fees'].sum()

            # Aplica a fórmula diretamente na coluna original
            df['Net Dollars after Fees'] = df.apply(
                lambda row: row['Net Dollars after Fees'] - ((row['Net Dollars after Fees'] * 30) / 100)
                if row['Territory'] == 'United States' else row['Net Dollars after Fees'],
                axis=1
            )

            withholding_total = df['Net Dollars after Fees'].sum()
            total_withheld = net_total - withholding_total

            # Exibe os resultados
            st.write(f'O valor Net é **USD {net_total:,.2f}**')
            st.write(f'O valor Net menos withholding é **USD {withholding_total:,.2f}**')
            st.write(f'O total de withholding aplicado é **USD {total_withheld:,.2f}**')

            # Preparar o arquivo para download
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            writer.close()

            st.download_button(
                label="Baixar arquivo processado",
                data=output.getvalue(),
                file_name=adjust_file_name(original_file_name),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        #----------------------------------
        # Processamento ONERPM com separação por moeda
        #----------------------------------
        elif report_option == 'Onerpm':
            for sheet in required_sheets:
                df_sheet = pd.read_excel(xls, sheet_name=sheet)

                # Identifica as moedas diferentes na planilha
                currencies = df_sheet['Currency'].unique()

                # Processa por moeda
                for currency in currencies:
                    df_sheet_currency = df_sheet[df_sheet['Currency'] == currency]

                    #----------------------------------
                    # Lógica para planilhas "Masters" e "Youtube Channel"
                    if sheet == 'Masters' or sheet == 'Youtube Channels':

                        net_total = df_sheet_currency['Net'].sum()

                        df_sheet_currency['Net'] = df_sheet_currency.apply(
                            lambda row: row['Net'] - ((row['Net'] * 30) / 100)
                            if row['Territory'] == 'US' else row['Net'],
                            axis=1
                        )

                        withholding_total = df_sheet_currency['Net'].sum()
                        total_withheld = net_total - withholding_total

                        # Atualiza os totais por moeda
                        if currency not in total_by_currency:
                            total_by_currency[currency] = net_total
                        else:
                            total_by_currency[currency] += net_total

                        # Exibe os resultados com a moeda correta
                        st.markdown(f''':blue-background[Planilha {sheet} {currency} Processada]''')
                        st.write(f'O valor Net é **{currency} {net_total:,.2f}**')
                        st.write(f'O valor Net menos withholding é **{currency} {withholding_total:,.2f}**')
                        st.write(f'O total de withholding aplicado é **{currency} {total_withheld:,.2f}**')

                    #----------------------------------
                    # Lógica para planilhas "Shares In & Out"
                    elif sheet == 'Shares In & Out':
                        df_sheet_in = df_sheet_currency[df_sheet_currency['Share Type'] == 'In']
                        df_sheet_out = df_sheet_currency[df_sheet_currency['Share Type'] == 'Out']

                        # Total para Share Type In
                        net_total_in = df_sheet_in['Net'].sum()
                        df_sheet_in['Net'] = df_sheet_in.apply(
                            lambda row: row['Net'] - ((row['Net'] * 30) / 100)
                            if row['Territory'] == 'US' else row['Net'],
                            axis=1
                        )
                        withholding_total_in = df_sheet_in['Net'].sum()

                        # Total para Share Type Out
                        share_out_total = df_sheet_out['Net'].sum()

                        # Atualiza os totais por moeda
                        if currency not in total_by_currency:
                            total_by_currency[currency] = net_total_in
                        else:
                            total_by_currency[currency] += net_total_in

                        # Atualiza os valores de Share-Out por moeda
                        if currency not in share_out_by_currency:
                            share_out_by_currency[currency] = share_out_total
                        else:
                            share_out_by_currency[currency] += share_out_total

                        # Exibe os resultados com a moeda correta
                        st.markdown(f''':blue-background[Planilha {sheet} {currency} Processada]''')
                        st.write(f'O valor Net (In) é **{currency} {net_total_in:,.2f}**')
                        st.write(f'O valor Net menos withholding (In) é **{currency} {withholding_total_in:,.2f}**')
                        st.write(f'O total de withholding aplicado (In) é **{currency} {net_total_in - withholding_total_in:,.2f}**')
                        st.write(f'Share-Out Total é **{currency} {share_out_total:,.2f}**')

                    # Exporta o resultado processado por moeda
                    output = BytesIO()
                    writer = pd.ExcelWriter(output, engine='xlsxwriter')
                    df_sheet_currency.to_excel(writer, sheet_name=f"{sheet}_{currency}", index=False)
                    writer.close()

                    # Botão para baixar o resultado processado por moeda
                    st.download_button(
                        label=f"Baixar {sheet} processado ({currency})",
                        data=output.getvalue(),
                        file_name=adjust_file_name(f"{sheet}_{currency}"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                    # Insere um divisor entre os resultados
                    st.divider()

            # Exibe os totais somados por moeda e Share-Out
            st.markdown("### Totais Processados por Moeda:")
            for currency, total in total_by_currency.items():
                st.write(f"Total em {currency} processados: **{currency} {total:,.2f}**")
                st.write(f"Share-Out {currency} Total: **{currency} {share_out_by_currency.get(currency, 0):,.2f}**")
            
            # Exibe o TOTAL GERAL
            st.markdown("### TOTAL GERAL:")
            for currency, total in total_by_currency.items():
                share_out_total = share_out_by_currency.get(currency, 0)
                total_geral = total + share_out_total
                st.write(f"Total Geral {currency}: **{currency} {total_geral:,.2f}**")

            st.success("Processamento concluído!")
