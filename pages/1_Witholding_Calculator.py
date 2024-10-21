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
# Função para exibir os resultados processados
#----------------------------------
def display_results(df, column):
    net_total = df[column].sum()
    
    #----------------------------------
    # Aplica a fórmula de withholding apenas para receitas dos EUA
    #----------------------------------
    withholding_total = df.apply(
        lambda row: row[column] - ((row[column] * 30) / 100) if row['Territory'] == 'US' else row[column],
        axis=1
    ).sum()
    
    total_withheld = net_total - withholding_total
    
    #----------------------------------
    # Exibe os resultados
    #----------------------------------
    st.write(f'O valor Net é **USD {net_total:,.2f}**')
    st.write(f'O valor Net menos withholding é **USD {withholding_total:,.2f}**')
    st.write(f'O total de withholding aplicado é **USD {total_withheld:,.2f}**')

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
    # Processamento dos dados
    #----------------------------------
    if st.button('Processar desconto', type='primary'):
                    
        #----------------------------------
        # Processamento THE ORCHARD
        #----------------------------------
        if report_option == 'The Orchard (Europa)':

            net_total = df['Label Share Net Receipts'].sum()

            #----------------------------------
            # Aplica a fórmula de withholding diretamente na coluna original
            #----------------------------------
            df['Label Share Net Receipts'] = df.apply(
                lambda row: row['Label Share Net Receipts'] - ((row['Label Share Net Receipts'] * 30) / 100)
                if row['Territory'] == 'USA' else row['Label Share Net Receipts'],
                axis=1
            )

            withholding_total = df['Label Share Net Receipts'].sum()
            total_withheld = net_total - withholding_total

            #----------------------------------
            # Exibe os resultados
            #----------------------------------
            st.write(f'O valor Net é **USD {net_total:,.2f}**')
            st.write(f'O valor Net menos withholding é **USD {withholding_total:,.2f}**')
            st.write(f'O total de withholding aplicado é **USD {total_withheld:,.2f}**')

            #----------------------------------
            # Preparar o arquivo para download
            #----------------------------------
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

            #----------------------------------
            # Filtra a linha de total para não somar em duplicidade
            #----------------------------------
            df = df[~df['Sales Classification'].str.contains("Total", case=False, na=False)]

            net_total = df['Net Dollars after Fees'].sum()

            #----------------------------------
            # Aplica a fórmula diretamente na coluna original
            #----------------------------------
            df['Net Dollars after Fees'] = df.apply(
                lambda row: row['Net Dollars after Fees'] - ((row['Net Dollars after Fees'] * 30) / 100)
                if row['Territory'] == 'United States' else row['Net Dollars after Fees'],
                axis=1
            )

            withholding_total = df['Net Dollars after Fees'].sum()
            total_withheld = net_total - withholding_total

            #----------------------------------
            # Exibe os resultados
            #----------------------------------
            st.write(f'O valor Net é **USD {net_total:,.2f}**')
            st.write(f'O valor Net menos withholding é **USD {withholding_total:,.2f}**')
            st.write(f'O total de withholding aplicado é **USD {total_withheld:,.2f}**')

            #----------------------------------
            # Preparar o arquivo para download
            #----------------------------------
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
        # Processamento ONERPM
        #----------------------------------
        elif report_option == 'Onerpm':
            for sheet in required_sheets:
                df_sheet = pd.read_excel(xls, sheet_name=sheet)
             
                #----------------------------------
                # Lógica para planilhas "Masters" e "Youtube Channel"
                #----------------------------------
                if sheet == 'Masters' or sheet == 'Youtube Channels':
                    
                    df_sheet['Net'] = df_sheet.apply(
                        lambda row: row['Net'] - ((row['Net'] * 30) / 100)
                        if row['Territory'] == 'US' else row['Net'],
                        axis=1
                    )
                    display_results(df_sheet, 'Net')

                #----------------------------------
                # Lógica para planilhas "Share In & Out"
                #----------------------------------
                elif sheet == 'Shares In & Out':
                    df_sheet_in = df_sheet[df_sheet['Share Type'] == 'In']

                    df_sheet_in['Net'] = df_sheet_in.apply(
                        lambda row: row['Net'] - ((row['Net'] * 30) / 100)
                        if row['Territory'] == 'US' else row['Net'],
                        axis=1
                    )

                    #----------------------------------
                    # Exibe resultados Onerpm (função)
                    #----------------------------------
                    display_results(df_sheet_in, 'Net')

                output = BytesIO()
                writer = pd.ExcelWriter(output, engine='xlsxwriter')
                df_sheet.to_excel(writer, sheet_name=sheet, index=False)
                writer.close()

                st.download_button(
                    label=f"Baixar {sheet} processado",
                    data=output.getvalue(),
                    file_name=adjust_file_name(sheet),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            st.success("Processamento concluído!")
