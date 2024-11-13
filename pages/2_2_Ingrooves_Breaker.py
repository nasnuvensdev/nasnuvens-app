import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile
import locale
import unicodedata


def format_br(value):
    # Converte para string com 2 casas decimais, usando vírgula como decimal e ponto como separador de milhar
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_fx_rate(value):
    # Formata a taxa de câmbio com 4 casas decimais
    return f"{value:.4f}".replace(".", ",")

#----------------------------------
# Configuração dos Agrupamentos
#----------------------------------
# Artistas que serão buscados diretamente no campo Artist
TARGET_GROUPS = [
    "Cláudio Noam",
    "Planta E Raiz",
    "Pollo",
    "Dom Silver"
]

# Artistas que possuem múltiplos nomes/projetos para agrupar
ARTIST_KEYWORDS = {
    "Marcelo Menezes": [
        "tchakabum",
        "marcela jardim",
        "tubarao",  # Removido o acento para maior flexibilidade
        
    ],

    "Carlinhos Brown": [
        "heloa",  # Removido o acento
        "carlinhos brown",
        "timbalada"
    ],

    "Rodolfo Abrantes": [
        "raimundos",  # Removido o acento
        
    ]
}

#----------------------------------
# Ingrooves Breaker
#----------------------------------

st.title("Ingrooves Breaker")
st.caption("Desconta 30% das receitas EUA do relatório Ingrooves e separa por artista.")

#----------------------------------
# Inicializa variáveis de estado da sessão
#----------------------------------
if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None
if 'net_dollars' not in st.session_state:
    st.session_state['net_dollars'] = None
if 'net_withholding_total' not in st.session_state:
    st.session_state['net_withholding_total'] = None
if 'total_withheld' not in st.session_state:
    st.session_state['total_withheld'] = None
if 'processed_data' not in st.session_state:
    st.session_state['processed_data'] = None
if 'show_fx_rate' not in st.session_state:
    st.session_state['show_fx_rate'] = False
if 'show_summary' not in st.session_state:
    st.session_state['show_summary'] = False
if 'summary_df' not in st.session_state:
    st.session_state['summary_df'] = None
if 'total_geral_values' not in st.session_state:
    st.session_state['total_geral_values'] = {
        'Total Net Dollars': 0,
        'Total BRL': 0,
        'Difference Net Dollars': 0,
        'Difference BRL': 0
    }
if 'artist_dataframes' not in st.session_state:
    st.session_state['artist_dataframes'] = {}

#----------------------------------
# Funções auxiliares
#----------------------------------
def reset_state():
    st.session_state['net_dollars'] = None
    st.session_state['net_withholding_total'] = None
    st.session_state['total_withheld'] = None
    st.session_state['processed_data'] = None
    st.session_state['show_fx_rate'] = False
    st.session_state['show_summary'] = False
    st.session_state['summary_df'] = None
    st.session_state['total_geral_values'] = {
        'Total Net Dollars': 0,
        'Total BRL': 0,
        'Difference Net Dollars': 0,
        'Difference BRL': 0
    }
    st.session_state['uploaded_file'] = None
    st.session_state['artist_dataframes'] = {}

def normalize_text(s):
    s = s.lower()
    nfkd_form = unicodedata.normalize('NFKD', s)
    return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])


def format_br(value):
    try:
        return locale.format_string('%.2f', value, grouping=True)
    except:
        return str(value)

def format_fx_rate(value):
    return str(value).replace('.', ',')

def create_excel_with_formatted_numbers(df, filename):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    num_format = workbook.add_format({'num_format': '#,##0.00'})
    
    for idx, col in enumerate(df.columns):
        if df[col].dtype in ['float64', 'int64']:
            worksheet.set_column(idx, idx, 18, num_format)
    
    writer.close()
    return output.getvalue()

#----------------------------------
# Interface principal
#----------------------------------
# Upload do arquivo
uploaded_file = st.file_uploader("Selecione o relatório Ingrooves", key="file_uploader")

# Reset de estado quando um novo arquivo é carregado
if uploaded_file and st.session_state.uploaded_file != uploaded_file:
    reset_state()
    st.session_state.uploaded_file = uploaded_file

# Processamento inicial do arquivo
if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, sheet_name='Digital Sales Details')
    df = df[~df['Sales Classification'].str.contains("Total", case=False, na=False)]
    st.session_state.net_dollars = df['Net Dollars after Fees'].sum()

    # Botão de processamento
    if st.button('Processar desconto', type='primary'):
        # Aplica o desconto de 30% nas receitas dos EUA
        df['Net Dollars after Fees'] = df.apply(
            lambda row: row['Net Dollars after Fees'] * 0.7 if row['Territory'] == 'United States' 
            else row['Net Dollars after Fees'],
            axis=1
        )
       
        st.session_state.net_withholding_total = df['Net Dollars after Fees'].sum()
        st.session_state.total_withheld = st.session_state.net_dollars - st.session_state.net_withholding_total
        
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Digital Sales Details', index=False)
        writer.close()
        st.session_state.processed_data = output.getvalue()
        st.session_state.show_fx_rate = True
        
# Exibe os valores processados
if st.session_state.net_dollars is not None and st.session_state.net_withholding_total is not None:
    st.write(f'O valor Original é **USD {format_br(st.session_state.net_dollars)}**')
    st.write(f'O total de withholding aplicado é **USD {format_br(st.session_state.total_withheld)}**')
    st.write(f':red[O valor Net menos withholding é **USD {format_br(st.session_state.net_withholding_total)}**]')
    st.divider()

# Área de taxa de câmbio e resumo
if st.session_state.show_fx_rate:
    fx_rate = st.number_input("Adicione aqui a taxa de câmbio (FX rate)", value=0.0, format="%.4f")
    
    if st.button('Exibir resumo'):
        st.session_state.show_summary = True
        
        # Processamento dos dados por artista
        grouped_df = pd.DataFrame(columns=["Artist", "Total Net Dollars", "FX Rate", "Total BRL"])
        artist_dfs = {}
        processed_artists = set()  # Conjunto para rastrear artistas já processados

        # Processamento de artistas diretos (TARGET_GROUPS)
        for artist in TARGET_GROUPS:
            artist_group = df[df['Artist'].apply(lambda x: isinstance(x, str) and artist.lower() in x.lower())]
            if not artist_group.empty:
                # Aplicar o desconto de 30% para registros dos EUA
                total_net_dollars = artist_group.apply(
                    lambda row: row['Net Dollars after Fees'] * 0.7 if row['Territory'] == 'United States' 
                    else row['Net Dollars after Fees'],
                    axis=1
                ).sum()

                total_brl = total_net_dollars * fx_rate
                grouped_df = pd.concat([grouped_df, pd.DataFrame([{
                    "Artist": artist,
                    "Total Net Dollars": round(total_net_dollars, 2),
                    "FX Rate": fx_rate,
                    "Total BRL": round(total_brl, 2)
                }])], ignore_index=True)
                artist_dfs[artist] = artist_group
                processed_artists.update(artist_group['Artist'].unique())

        # Processamento de artistas com keywords
        for main_artist, keywords in ARTIST_KEYWORDS.items():
            condition = df['Artist'].apply(
                lambda x: isinstance(x, str) and any(
                    normalize_text(keyword) in normalize_text(x)
                    for keyword in keywords
                )
            )
                                            
                 
            artist_group = df[condition]
            if not artist_group.empty:
                # Aplicar o desconto de 30% para registros dos EUA
                total_net_dollars = artist_group.apply(
                    lambda row: row['Net Dollars after Fees'] * 0.7 if row['Territory'] == 'United States' 
                    else row['Net Dollars after Fees'],
                    axis=1
                ).sum()

                total_brl = total_net_dollars * fx_rate
                grouped_df = pd.concat([grouped_df, pd.DataFrame([{
                    "Artist": main_artist,
                    "Total Net Dollars": round(total_net_dollars, 2),
                    "FX Rate": fx_rate,
                    "Total BRL": round(total_brl, 2)
                }])], ignore_index=True)
                artist_dfs[main_artist] = artist_group
                processed_artists.update(artist_group['Artist'].unique())

        # Linha de total
        total_net_dollars_df = grouped_df['Total Net Dollars'].sum()
        total_brl_df = grouped_df['Total BRL'].sum()
        total_row = pd.DataFrame([{
            "Artist": "TOTAL",
            "Total Net Dollars": round(total_net_dollars_df, 2),
            "FX Rate": fx_rate,
            "Total BRL": round(total_brl_df, 2)
        }])
        grouped_df = pd.concat([grouped_df, total_row], ignore_index=True)

        # Identificar artistas não classificados
        all_artists = df[df['Artist'].notna()]['Artist'].unique()
        unclassified_artists = []
        
        for artist in all_artists:
            if artist not in processed_artists:
                artist_data = df[df['Artist'] == artist]
                # Aplicar o desconto de 30% para registros dos EUA
                total_net_dollars = artist_data.apply(
                    lambda row: row['Net Dollars after Fees'] * 0.7 if row['Territory'] == 'United States' 
                    else row['Net Dollars after Fees'],
                    axis=1
                ).sum()

                if total_net_dollars > 0:  # Só inclui se tiver valor positivo
                    unclassified_artists.append({
                        'artist': artist,
                        'net_dollars': total_net_dollars,
                        'brl': total_net_dollars * fx_rate
                    })

        # Ordenar artistas não classificados por valor (maior para menor)
        unclassified_artists.sort(key=lambda x: x['net_dollars'], reverse=True)
        
        # Salvar na sessão para exibição posterior
        st.session_state['unclassified_artists'] = unclassified_artists

        # Calcular o total geral considerando o withholding
        total_net_dollars = df.apply(
            lambda row: row['Net Dollars after Fees'] * 0.7 if row['Territory'] == 'United States' 
            else row['Net Dollars after Fees'],
            axis=1
        ).sum()

        total_brl = total_net_dollars * fx_rate
        difference_net_dollars = total_net_dollars - total_net_dollars_df
        difference_brl = total_brl - total_brl_df

        st.session_state.total_geral_values = {
            'Total Net Dollars': round(total_net_dollars, 2),
            'Total BRL': round(total_brl, 2),
            'Difference Net Dollars': round(difference_net_dollars, 2),
            'Difference BRL': round(difference_brl, 2)
        }
        st.session_state.artist_dataframes = artist_dfs
        st.session_state.summary_df = grouped_df

# Exibição do resumo e download
if st.session_state.show_summary and st.session_state.summary_df is not None:
    st.divider()
    st.write("Agrupamento por artista:")
    
    # DataFrame formatado para exibição
    display_df = st.session_state.summary_df.copy()
    display_df['Total Net Dollars'] = display_df['Total Net Dollars'].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    display_df['FX Rate'] = display_df['FX Rate'].apply(lambda x: f"{x:.4f}".replace(".", ","))
    display_df['Total BRL'] = display_df['Total BRL'].apply(lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    st.dataframe(display_df)

    # Botão de download das planilhas
    if st.session_state.artist_dataframes:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for artist, artist_df in st.session_state.artist_dataframes.items():
                excel_data = create_excel_with_formatted_numbers(artist_df, f"{artist}.xlsx")
                zip_file.writestr(f"{artist}.xlsx", excel_data)
        
        zip_buffer.seek(0)
        st.download_button(
            label="Baixar planilhas por artista",
            data=zip_buffer.getvalue(),
            file_name="planilhas_por_artista.zip",
            mime="application/zip"
        )
    st.divider()
    # Total Geral
    st.markdown(
        f"### Total Geral\n"
        f"**Total Net Dollars:** USD {format_br(st.session_state.total_geral_values['Total Net Dollars'])}\n\n"
        f"**Total BRL:** BRL {format_br(st.session_state.total_geral_values['Total BRL'])}\n\n"
        f":red[**Diferença Net Dollars: USD {format_br(st.session_state.total_geral_values['Difference Net Dollars'])}**]\n\n"
        f":red[**Diferença BRL: BRL {format_br(st.session_state.total_geral_values['Difference BRL'])}**]"
    )

    # Lista de artistas não classificados
    if 'unclassified_artists' in st.session_state and st.session_state['unclassified_artists']:
        st.markdown("### Artistas não classificados ⚠️")
        for artist_info in st.session_state['unclassified_artists']:
            st.markdown(
                f"- {artist_info['artist']}: USD {format_br(artist_info['net_dollars'])} "
                f"(BRL {format_br(artist_info['brl'])})"
            )