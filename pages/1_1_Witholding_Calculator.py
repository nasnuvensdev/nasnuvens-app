import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile

#----------------------------------
# Função para ajustar nomes dos arquivos, mantendo o nome original e adicionando o sufixo
#----------------------------------
def adjust_file_name(file_name):
    suffix = "_withholding_excluded"
    return f"{file_name}{suffix}.xlsx"

def adjust_file_name_onerpm(file_name):
    suffix = "_fee_excluded"
    return f"{file_name}{suffix}.xlsx"

#----------------------------------
# Withholding Calculator
#----------------------------------
st.title("Withholding Calculator")
st.caption("Desconta 30% das receitas dos EUA.")

#----------------------------------
# Inicializa variáveis de estado da sessão
#----------------------------------

# The Orchard
#-------------
if 'uploaded_file_name' not in st.session_state:
    st.session_state['uploaded_file_name'] = None
if 'orchard_net_total' not in st.session_state:
    st.session_state['orchard_net_total'] = None
if 'orchard_withholding_total' not in st.session_state:
    st.session_state['orchard_withholding_total'] = None
if 'orchard_total_withheld' not in st.session_state:
    st.session_state['orchard_total_withheld'] = None
if 'orchard_processed_data' not in st.session_state:
    st.session_state['orchard_processed_data'] = None

# Ingrooves
# -------------

if 'ingrooves_net_total' not in st.session_state:
    st.session_state['ingrooves_net_total'] = None
if 'ingrooves_withholding_total' not in st.session_state:
    st.session_state['ingrooves_withholding_total'] = None
if 'ingrooves_total_withheld' not in st.session_state:
    st.session_state['ingrooves_total_withheld'] = None
if 'ingrooves_processed_data' not in st.session_state:
    st.session_state['ingrooves_processed_data'] = None

# Onerpm
# -------------

if 'onerpm_results' not in st.session_state:
    st.session_state['onerpm_results'] = []
if 'total_by_currency' not in st.session_state:
    st.session_state['total_by_currency'] = {}
if 'share_out_by_currency' not in st.session_state:
    st.session_state['share_out_by_currency'] = {}
if 'total_net_usd' not in st.session_state:
    st.session_state['total_net_usd'] = 0
if 'total_net_brl' not in st.session_state:
    st.session_state['total_net_brl'] = 0
if 'total_usd_fee_applied' not in st.session_state:
    st.session_state['total_usd_fee_applied'] = 0
if 'total_brl_fee_applied' not in st.session_state:
    st.session_state['total_brl_fee_applied'] = 0
if 'share_out_usd' not in st.session_state:
    st.session_state['share_out_usd'] = 0
if 'share_out_brl' not in st.session_state:
    st.session_state['share_out_brl'] = 0

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
    # Verifica se um novo arquivo foi carregado e reseta o estado da sessão
    #----------------------------------
    if uploaded_file.name != st.session_state['uploaded_file_name']:
        # Salva o novo nome do arquivo
        st.session_state['uploaded_file_name'] = uploaded_file.name
        
        # Reset The Orchard
        st.session_state['orchard_net_total'] = None
        st.session_state['orchard_withholding_total'] = None
        st.session_state['orchard_total_withheld'] = None
        st.session_state['orchard_processed_data'] = None
        
        # Reset Ingrooves
        st.session_state['ingrooves_net_total'] = None
        st.session_state['ingrooves_withholding_total'] = None
        st.session_state['ingrooves_total_withheld'] = None
        st.session_state['ingrooves_processed_data'] = None
        
        # Reset ONErpm
        st.session_state['onerpm_results'] = []
        st.session_state['total_by_currency'] = {}
        st.session_state['share_out_by_currency'] = {}
        st.session_state['total_net_usd'] = 0
        st.session_state['total_net_brl'] = 0
        st.session_state['total_usd_fee_applied'] = 0
        st.session_state['total_brl_fee_applied'] = 0
        st.session_state['share_out_usd'] = 0
        st.session_state['share_out_brl'] = 0

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
        
        # Solicita os valores de taxa apenas para Onerpm
        st.write("Preencha os valores fixos para taxas a serem descontadas proporcionalmente:")
        usd_tax = st.number_input('Insira o valor fixo da taxa em USD', min_value=0.0, value=20.0, step=1.0)
        brl_tax = st.number_input('Insira o valor fixo da taxa em BRL', min_value=0.0, value=0.75, step=0.01)

    #----------------------------------
    # Processamento THE ORCHARD
    #----------------------------------
    if report_option == 'The Orchard (Europa)':
        
        df = pd.read_excel(uploaded_file)
        
        if st.button('Processar desconto', type='primary', key='process_orchard'):
            net_total = df['Label Share Net Receipts'].sum()
            st.session_state['orchard_net_total'] = net_total

            # Aplica a fórmula de withholding
            df['Label Share Net Receipts'] = df.apply(
                lambda row: row['Label Share Net Receipts'] - ((row['Label Share Net Receipts'] * 30) / 100)
                if row['Territory'] == 'USA' else row['Label Share Net Receipts'],
                axis=1
            )

            withholding_total = df['Label Share Net Receipts'].sum()
            total_withheld = net_total - withholding_total

            # Salva os resultados no session_state
            st.session_state['orchard_withholding_total'] = withholding_total
            st.session_state['orchard_total_withheld'] = total_withheld

            # Prepara o arquivo para download
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, index=False)
            writer.close()
            st.session_state['orchard_processed_data'] = output.getvalue()

        # Exibe os resultados se existirem no session_state
        if st.session_state['orchard_net_total'] is not None:
            st.write(f'O valor Net é **USD {st.session_state["orchard_net_total"]:,.2f}**')
            st.write(f'O total de withholding aplicado é **USD {st.session_state["orchard_total_withheld"]:,.2f}**')
            st.write(f':red[O valor Net menos withholding é **USD {st.session_state["orchard_withholding_total"]:,.2f}**]')

            # Botão de download
            st.download_button(
                label="Baixar arquivo processado",
                data=st.session_state['orchard_processed_data'],
                file_name=adjust_file_name(original_file_name),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    #----------------------------------
    # Processamento INGROOVES
    #----------------------------------
    elif report_option == 'Ingrooves':
        
        sheet_name = 'Digital Sales Details'
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
        
        # Filtra a linha de total
        df = df[~df['Sales Classification'].str.contains("Total", case=False, na=False)]

        if st.button('Processar desconto', type='primary', key='process_ingrooves'):
            net_total = df['Net Dollars after Fees'].sum()
            st.session_state['ingrooves_net_total'] = net_total

            # Aplica a fórmula
            df['Net Dollars after Fees'] = df.apply(
                lambda row: row['Net Dollars after Fees'] - ((row['Net Dollars after Fees'] * 30) / 100)
                if row['Territory'] == 'United States' else row['Net Dollars after Fees'],
                axis=1
            )

            withholding_total = df['Net Dollars after Fees'].sum()
            total_withheld = net_total - withholding_total

            # Salva os resultados no session_state
            st.session_state['ingrooves_withholding_total'] = withholding_total
            st.session_state['ingrooves_total_withheld'] = total_withheld

            # Prepara o arquivo para download
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            writer.close()
            st.session_state['ingrooves_processed_data'] = output.getvalue()

        # Exibe os resultados se existirem no session_state
        if st.session_state['ingrooves_net_total'] is not None:
            st.write(f'O valor Net é **USD {st.session_state["ingrooves_net_total"]:,.2f}**')
            st.write(f'O total de withholding aplicado é **USD {st.session_state["ingrooves_total_withheld"]:,.2f}**')
            st.write(f':red[O valor Net menos withholding é **USD {st.session_state["ingrooves_withholding_total"]:,.2f}**]')

            # Botão de download
            st.download_button(
                label="Baixar arquivo processado",
                data=st.session_state['ingrooves_processed_data'],
                file_name=adjust_file_name(original_file_name),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    #----------------------------------
    # Processamento ONERPM com separação por moeda
    #----------------------------------
    elif report_option == 'Onerpm':
        if st.button('Processar desconto', type='primary', key='process_onerpm'):
            # Reseta as variáveis de estado da sessão
            st.session_state['total_net_usd'] = 0
            st.session_state['total_net_brl'] = 0
            st.session_state['total_usd_fee_applied'] = 0
            st.session_state['total_brl_fee_applied'] = 0
            st.session_state['share_out_usd'] = 0
            st.session_state['share_out_brl'] = 0
            st.session_state['total_by_currency'] = {}
            st.session_state['share_out_by_currency'] = {}
            st.session_state['onerpm_results'] = []

            # Primeiro passo: somar os valores de entrada nas planilhas para USD e BRL (apenas 'In' para 'Shares In & Out')
            for sheet in required_sheets:
                df_sheet = pd.read_excel(xls, sheet_name=sheet)

                # Identifica as moedas diferentes na planilha
                currencies = df_sheet['Currency'].unique()

                for currency in currencies:
                    df_sheet_currency = df_sheet[df_sheet['Currency'] == currency]

                    # Verifica se estamos na planilha 'Shares In & Out' e pega apenas o tipo 'In'
                    if sheet == 'Shares In & Out':
                        df_sheet_currency_in = df_sheet_currency[df_sheet_currency['Share Type'] == 'In']
                        df_sheet_currency_out = df_sheet_currency[df_sheet_currency['Share Type'] == 'Out']

                        # Soma os valores de Share-Out (que serão negativos)
                        if currency == 'USD':
                            st.session_state['share_out_usd'] = df_sheet[(df_sheet['Currency'] == 'USD') & (df_sheet['Share Type'] == 'Out')]['Net'].sum()
                            st.session_state['share_out_by_currency']['USD'] = st.session_state['share_out_usd']  # Atualiza o dicionário com o valor de USD
                        elif currency == 'BRL':
                            st.session_state['share_out_brl'] = df_sheet[(df_sheet['Currency'] == 'BRL') & (df_sheet['Share Type'] == 'Out')]['Net'].sum()
                            st.session_state['share_out_by_currency']['BRL'] = st.session_state['share_out_brl']  # Atualiza o dicionário com o valor de BRL

                        df_sheet_currency = df_sheet_currency_in  # Usamos apenas os valores de "In" para o total líquido

                    # Soma os valores líquidos para cada moeda
                    net_total = df_sheet_currency['Net'].sum()

                    if currency == 'USD':
                        st.session_state['total_net_usd'] += net_total
                    elif currency == 'BRL':
                        st.session_state['total_net_brl'] += net_total

            # Agora temos total_net_usd e total_net_brl somados a partir das planilhas relevantes, além dos valores de Share-Out

            # Segundo passo: aplicar o desconto proporcionalmente em cada linha com base no total líquido
            for sheet in required_sheets:
                df_sheet = pd.read_excel(xls, sheet_name=sheet)

                # Identifica as moedas diferentes na planilha
                currencies = df_sheet['Currency'].unique()

                for currency in currencies:
                    df_sheet_currency = df_sheet[df_sheet['Currency'] == currency]

                    # Verifica se estamos na planilha 'Shares In & Out' e pega apenas o tipo 'In'
                    if sheet == 'Shares In & Out':
                        df_sheet_currency = df_sheet_currency[df_sheet_currency['Share Type'] == 'In']

                    # Calcula o total líquido por planilha
                    net_total = df_sheet_currency['Net'].sum()

                    if net_total != 0:
                        # Calcula a proporção do valor total para cada linha
                        if currency == 'USD' and st.session_state['total_net_usd'] > 0:
                            df_sheet_currency['Proportion'] = df_sheet_currency['Net'] / st.session_state['total_net_usd']
                            fee_applied = df_sheet_currency['Proportion'] * usd_tax
                            st.session_state['total_usd_fee_applied'] += fee_applied.sum()
                            df_sheet_currency['Net'] = df_sheet_currency['Net'] - fee_applied
                            df_sheet_currency = df_sheet_currency.drop('Proportion', axis=1)  # Remove a coluna Proportion

                        elif currency == 'BRL' and st.session_state['total_net_brl'] > 0:
                            df_sheet_currency['Proportion'] = df_sheet_currency['Net'] / st.session_state['total_net_brl']
                            fee_applied = df_sheet_currency['Proportion'] * brl_tax
                            st.session_state['total_brl_fee_applied'] += fee_applied.sum()
                            df_sheet_currency['Net'] = df_sheet_currency['Net'] - fee_applied
                            df_sheet_currency = df_sheet_currency.drop('Proportion', axis=1)

                        withholding_total = df_sheet_currency['Net'].sum()
                        total_withheld = net_total - withholding_total

                        # Atualiza os totais por moeda
                        if currency not in st.session_state['total_by_currency']:
                            st.session_state['total_by_currency'][currency] = net_total
                        else:
                            st.session_state['total_by_currency'][currency] += net_total

                        # Prepara o arquivo para download
                        output = BytesIO()
                        writer = pd.ExcelWriter(output, engine='xlsxwriter')
                        df_sheet_currency.to_excel(writer, sheet_name=f"{sheet}_{currency}", index=False)
                        writer.close()
                        output.seek(0)

                        # Armazena os resultados na sessão
                        st.session_state['onerpm_results'].append({
                            'sheet': sheet,
                            'currency': currency,
                            'df': df_sheet_currency,
                            'net_total': net_total,
                            'withholding_total': withholding_total,
                            'total_withheld': total_withheld,
                            'output': output.getvalue()
                        })

# Após o processamento dos arquivos e antes de exibir os resultados individuais
    if st.session_state['onerpm_results']:
        # Criar um buffer para o arquivo ZIP
        zip_buffer = BytesIO()
        
        # Criar o arquivo ZIP
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for result in st.session_state['onerpm_results']:
                sheet = result['sheet']
                currency = result['currency']
                output_data = result['output']
                
                # Adicionar cada arquivo Excel ao ZIP
                file_name = adjust_file_name_onerpm(f"{sheet}_{currency}")
                zip_file.writestr(file_name, output_data)
        
        # Botão para download do ZIP
        st.download_button(
            label="📦 Baixar todos os arquivos (zip)",
            data=zip_buffer.getvalue(),
            file_name=f"onerpm_processed_files.zip",
            mime="application/zip",
            help="Clique para baixar todos os arquivos processados em um único arquivo ZIP"
        )
        
        st.divider()

    #----------------------------------
    # Exibe os resultados armazenados na sessão
    #----------------------------------
    if report_option == 'Onerpm' and st.session_state['onerpm_results']:
        for result in st.session_state['onerpm_results']:
            sheet = result['sheet']
            currency = result['currency']
            net_total = result['net_total']
            withholding_total = result['withholding_total']
            total_withheld = result['total_withheld']
            output_data = result['output']

            st.markdown(f'''##### :blue[Planilha {sheet} {currency} Processada]''')
            st.write(f'O valor Net é **{currency} {net_total:,.2f}**')
            st.write(f'O total de Fee aplicado é **{currency} {total_withheld:,.2f}**')
            st.write(f':red[O valor Net menos Fee é **{currency} {withholding_total:,.2f}**]')
            
            st.download_button(
                label=f"Baixar {sheet} processado ({currency})",
                data=output_data,
                file_name=adjust_file_name_onerpm(f"{sheet}_{currency}"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.divider()

        # Exibe os totais somados por moeda e Share-Out
        st.markdown("### Totais Processados por Moeda:")
        for currency, total in st.session_state['total_by_currency'].items():
            st.write(f"Total em {currency} processados: **{currency} {total:,.2f}**")
            st.write(f"Share-Out {currency} Total: **{currency} {st.session_state['share_out_by_currency'].get(currency, 0):,.2f}**")

        st.divider()

        # Exibe o TOTAL GERAL sem descontos (valores iguais relatório)
        st.markdown("### TOTAL GERAL (valor relatório):")
        if 'USD' in st.session_state['total_by_currency']:
            total_geral_usd = st.session_state['total_by_currency']['USD'] + st.session_state['share_out_usd']
            st.write(f"Total Geral USD (descontado apenas share-out): **USD {total_geral_usd:,.2f}**")
        if 'BRL' in st.session_state['total_by_currency']:
            total_geral_brl = st.session_state['total_by_currency']['BRL'] + st.session_state['share_out_brl']
            st.write(f"Total Geral BRL (descontado apenas share-out): **BRL {total_geral_brl:,.2f}**")

        st.divider()

        # Exibe o TOTAL GERAL com os valores descontados
        st.markdown("### TOTAL GERAL (com fees aplicados):")
        if 'USD' in st.session_state['total_by_currency']:
            total_geral_usd = st.session_state['total_by_currency']['USD'] - st.session_state['total_usd_fee_applied'] + st.session_state['share_out_usd']
            st.write(f"Total Geral USD (após descontos e share-out): **USD {total_geral_usd:,.2f}**")
        if 'BRL' in st.session_state['total_by_currency']:
            total_geral_brl = st.session_state['total_by_currency']['BRL'] - st.session_state['total_brl_fee_applied'] + st.session_state['share_out_brl']
            st.write(f"Total Geral BRL (após descontos e share-out): **BRL {total_geral_brl:,.2f}**")

        st.success("Processamento concluído!")
