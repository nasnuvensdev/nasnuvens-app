import streamlit as st
import pandas as pd
from io import BytesIO
import zipfile
import locale
import unicodedata
import re
import os
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_br(value):
    # Converte para string com 2 casas decimais, usando vírgula como decimal e ponto como separador de milhar
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_fx_rate(value):
    # Formata a taxa de câmbio com 4 casas decimais
    return f"{value:.4f}".replace(".", ",")

#----------------------------------
# Ingrooves Breaker
#----------------------------------

st.title("Ingrooves Breaker")
st.caption("Desconta 30% das receitas EUA do relatório Ingrooves e separa por artista usando mapeamento externo.")

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
if 'matched_artists' not in st.session_state:
    st.session_state['matched_artists'] = {}
if 'debug_mode' not in st.session_state:
    st.session_state['debug_mode'] = False
if 'mapping_df' not in st.session_state:
    st.session_state['mapping_df'] = None
if 'processed_df' not in st.session_state:
    st.session_state['processed_df'] = None

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
    st.session_state['matched_artists'] = {}
    st.session_state['processed_df'] = None
    # Não resetamos o mapping_df para manter o mapeamento carregado

def normalize_text(s):
    """
    Função para normalizar texto:
    - Remove acentos
    - Converte para minúsculas
    - Remove caracteres especiais mantendo apenas letras, números e espaços
    - Remove espaços extras
    """
    if not isinstance(s, str):
        return ''
    
    # Remover acentos
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('ASCII')
    # Converter para minúsculas
    s = s.lower()
    # Remover caracteres especiais mantendo letras, números e espaços
    s = re.sub(r'[^\w\s]', '', s)
    # Remover espaços extras e normalizar espaços
    s = ' '.join(s.split())
    
    return s

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

def match_artist_from_mapping(artist_name, mapping_df, debug=False):
    """
    Função para correspondência de artistas usando a planilha de mapeamento
    Retorna o valor da coluna Tag_Artista se encontrar correspondência ou None
    """
    if not isinstance(artist_name, str) or mapping_df is None:
        return None
    
    # Versão exata - correspondência direta
    exact_match = mapping_df[mapping_df['Artist'] == artist_name]
    if not exact_match.empty:
        tag = exact_match.iloc[0]['Tag_Artista']
        if debug:
            logger.info(f"Match exato: '{artist_name}' -> '{tag}'")
        return tag
    
    # Versão normalizada para correspondências parciais
    normalized_artist = normalize_text(artist_name)
    
    # Verificar se o artista normalizado está contido em algum dos valores normalizados da coluna Artist
    for idx, row in mapping_df.iterrows():
        map_artist = row['Artist']
        map_tag = row['Tag_Artista']
        
        # Pular valores nulos
        if not isinstance(map_artist, str) or not isinstance(map_tag, str):
            continue
            
        normalized_map_artist = normalize_text(map_artist)
        
        # Verificar se há correspondência nos dois sentidos
        if normalized_artist in normalized_map_artist or normalized_map_artist in normalized_artist:
            if debug:
                logger.info(f"Match parcial: '{artist_name}' -> '{map_tag}' (via '{map_artist}')")
            return map_tag
    
    return None

def unclassified_artists_to_dataframe(unclassified_list):
    """
    Converte a lista de artistas não classificados para um DataFrame
    """
    if not unclassified_list:
        return pd.DataFrame()
    
    data = []
    for artist_info in unclassified_list:
        data.append({
            "Artist": artist_info['artist'],
            "Total Net Dollars": artist_info['net_dollars'],
            "Total BRL": artist_info['brl']
        })
    
    return pd.DataFrame(data)

def load_mapping_file():
    """
    Carrega a planilha de mapeamento do local padrão
    """
    # Caminho para o arquivo de mapeamento
    mapping_path = os.path.join("data", "mapping-rubricas.xlsx")
    
    try:
        mapping_df = pd.read_excel(mapping_path)
        if 'Artist' in mapping_df.columns and 'Tag_Artista' in mapping_df.columns:
            st.success(f"✅ Arquivo de mapeamento carregado com sucesso: {mapping_path}")
            return mapping_df
        else:
            st.error(f"❌ O arquivo de mapeamento não contém as colunas necessárias (Artist, Tag_Artista)")
            return None
    except Exception as e:
        st.error(f"❌ Erro ao carregar arquivo de mapeamento: {str(e)}")
        return None

def add_artist_to_mapping(artist_name, tag_artista, mapping_df):
    """
    Adiciona um novo artista ao DataFrame de mapeamento
    """
    new_row = pd.DataFrame([{"Artist": artist_name, "Tag_Artista": tag_artista}])
    return pd.concat([mapping_df, new_row], ignore_index=True)

def export_mapping_df(mapping_df):
    """
    Exporta o DataFrame de mapeamento para um arquivo Excel
    """
    if mapping_df is None or mapping_df.empty:
        return None
        
    output = BytesIO()
    mapping_df.to_excel(output, index=False)
    output.seek(0)
    return output.getvalue()

def process_file(df, mapping_df, debug=False):
    """
    Processa o arquivo aplicando o desconto e o mapeamento de artistas
    """
    if df is None or mapping_df is None:
        return None, 0, 0
    
    # Valor original antes do desconto
    original_total = df['Net Dollars after Fees'].sum()
    
    # Aplica o desconto de 30% nas receitas dos EUA
    df['Net Dollars after Fees'] = df.apply(
        lambda row: row['Net Dollars after Fees'] * 0.7 if row['Territory'] == 'United States' 
        else row['Net Dollars after Fees'],
        axis=1
    )
    
    # Valor após o desconto
    discounted_total = df['Net Dollars after Fees'].sum()
    total_withheld = original_total - discounted_total
    
    # Adicionar coluna para rastreamento de processamento
    df['Processed'] = False
    
    # Aplicar o mapeamento para cada artista
    df['Matched Group'] = df['Artist'].apply(
        lambda x: match_artist_from_mapping(x, mapping_df, debug=debug)
    )
    
    return df, original_total, discounted_total, total_withheld

def generate_summary(df, fx_rate, debug=False):
    """
    Gera o resumo dos dados agrupados por artista
    """
    if df is None:
        return None, None, None, []
    
    # Processamento dos dados por artista utilizando a coluna 'Matched Group'
    grouped_df = pd.DataFrame(columns=["Artist", "Total Net Dollars", "FX Rate", "Total BRL"])
    artist_dfs = {}
    
    # Agrupar por 'Matched Group' não nulo
    df_with_group = df[df['Matched Group'].notna()]
    grouped_data = df_with_group.groupby('Matched Group')
    
    for group_name, group_data in grouped_data:
        total_net_dollars = group_data['Net Dollars after Fees'].sum()
        total_brl = total_net_dollars * fx_rate
        
        grouped_df = pd.concat([grouped_df, pd.DataFrame([{
            "Artist": group_name,
            "Total Net Dollars": round(total_net_dollars, 2),
            "FX Rate": fx_rate,
            "Total BRL": round(total_brl, 2)
        }])], ignore_index=True)
        
        artist_dfs[group_name] = group_data
        df.loc[group_data.index, 'Processed'] = True
    
    # Ordenar por valor (do maior para o menor)
    grouped_df = grouped_df.sort_values(by="Total Net Dollars", ascending=False)
    
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

    # Identificar artistas não classificados (Matched Group é nulo)
    unclassified_artists_df = df[df['Matched Group'].isna()]
    unclassified_artists = []
    
    for artist in unclassified_artists_df['Artist'].unique():
        artist_data = unclassified_artists_df[unclassified_artists_df['Artist'] == artist]
        total_net_dollars = artist_data['Net Dollars after Fees'].sum()

        if total_net_dollars > 0:  # Só inclui se tiver valor positivo
            unclassified_artists.append({
                'artist': artist,
                'net_dollars': total_net_dollars,
                'brl': total_net_dollars * fx_rate
            })

    # Ordenar artistas não classificados por valor (maior para menor)
    unclassified_artists.sort(key=lambda x: x['net_dollars'], reverse=True)
    
    # Criar DataFrame de artistas não classificados para exportação
    unclassified_df = unclassified_artists_to_dataframe(unclassified_artists)
    if not unclassified_df.empty:
        artist_dfs["_Artistas Não Classificados"] = unclassified_df

    # Calcular o total geral considerando o withholding
    total_net_dollars = df['Net Dollars after Fees'].sum()
    total_brl = total_net_dollars * fx_rate
    difference_net_dollars = total_net_dollars - total_net_dollars_df
    difference_brl = total_brl - total_brl_df

    total_geral_values = {
        'Total Net Dollars': round(total_net_dollars, 2),
        'Total BRL': round(total_brl, 2),
        'Difference Net Dollars': round(difference_net_dollars, 2),
        'Difference BRL': round(difference_brl, 2)
    }
    
    return grouped_df, artist_dfs, total_geral_values, unclassified_artists

#----------------------------------
# Interface principal
#----------------------------------
# Opção de modo debug
st.sidebar.title("Configurações")
st.session_state['debug_mode'] = st.sidebar.checkbox("Modo Debug", value=st.session_state['debug_mode'])

# Carregar arquivo de mapeamento (apenas uma vez)
if st.session_state['mapping_df'] is None:
    st.session_state['mapping_df'] = load_mapping_file()
    
    # Em modo debug, mostrar informações sobre o mapeamento
    if st.session_state['debug_mode'] and st.session_state['mapping_df'] is not None:
        st.write(f"### Mapeamento carregado com {len(st.session_state['mapping_df'])} entradas")
        st.dataframe(st.session_state['mapping_df'])

# Upload do arquivo
uploaded_file = st.file_uploader("Selecione o relatório Ingrooves", key="file_uploader")

# Reset de estado quando um novo arquivo é carregado
if uploaded_file and st.session_state.uploaded_file != uploaded_file:
    reset_state()
    st.session_state.uploaded_file = uploaded_file

# Processamento do arquivo (automático quando temos o arquivo e o mapeamento)
if uploaded_file is not None and st.session_state['mapping_df'] is not None:
    try:
        # Ler o arquivo
        df = pd.read_excel(uploaded_file, sheet_name='Digital Sales Details')
        df = df[~df['Sales Classification'].str.contains("Total", case=False, na=False)]
        
        # Processar o arquivo automaticamente
        processed_df, original_total, discounted_total, total_withheld = process_file(
            df, 
            st.session_state['mapping_df'],
            debug=st.session_state['debug_mode']
        )
        
        # Armazenar os resultados no session_state
        st.session_state['processed_df'] = processed_df
        st.session_state.net_dollars = original_total
        st.session_state.net_withholding_total = discounted_total
        st.session_state.total_withheld = total_withheld
        
        # Preparar para download
        output = BytesIO()
        writer = pd.ExcelWriter(output, engine='xlsxwriter')
        processed_df.to_excel(writer, sheet_name='Digital Sales Details', index=False)
        writer.close()
        st.session_state.processed_data = output.getvalue()
        
        # Mostrar informações sobre o processamento
        st.write(f'O valor Original é **USD {format_br(original_total)}**')
        st.write(f'O total de withholding aplicado é **USD {format_br(total_withheld)}**')
        st.write(f':red[O valor Net menos withholding é **USD {format_br(discounted_total)}**]')
        
        # Se modo debug, mostrar estatísticas adicionais
        if st.session_state['debug_mode']:
            st.write("### Artistas encontrados no relatório:")
            artists_list = df['Artist'].dropna().unique().tolist()
            artists_list.sort()
            st.write(", ".join([f"'{a}'" for a in artists_list]))
            
            # Estatísticas de correspondência
            matched_count = processed_df[processed_df['Matched Group'].notna()]['Artist'].nunique()
            total_count = processed_df['Artist'].nunique()
            match_rate = (matched_count / total_count) * 100 if total_count > 0 else 0
            
            st.write(f"### Estatísticas de correspondência:")
            st.write(f"- Artistas correspondidos: {matched_count} de {total_count} ({match_rate:.1f}%)")
            
            # Distribuição por grupo
            st.write("### Distribuição de artistas por grupo:")
            group_counts = processed_df.groupby('Matched Group')['Net Dollars after Fees'].agg(['sum', 'count'])
            st.dataframe(group_counts)
        
        # Habilitar a entrada da taxa de câmbio
        st.session_state.show_fx_rate = True
        
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
elif uploaded_file is not None and st.session_state['mapping_df'] is None:
    st.warning("⚠️ Não foi possível carregar o arquivo de mapeamento. Verifique se o arquivo está no caminho correto: data/mapping-rubricas.xlsx")

# Área de taxa de câmbio e resumo
if st.session_state.show_fx_rate:
    fx_rate = st.number_input("Adicione aqui a taxa de câmbio (FX rate)", value=0.0, format="%.4f")
    
    # Opção extra para adicionar artistas manualmente ao mapeamento (modo debug)
    if st.session_state['debug_mode'] and st.session_state['processed_df'] is not None:
        with st.expander("Adicionar correspondência manual ao mapeamento"):
            col1, col2 = st.columns(2)
            with col1:
                artist_original = st.selectbox("Selecione o artista", 
                                   options=[""] + sorted(st.session_state['processed_df'][st.session_state['processed_df']['Matched Group'].isna()]['Artist'].unique().tolist()))
            with col2:
                # Opções de tag existentes ou nova tag
                existing_tags = sorted(st.session_state['mapping_df']['Tag_Artista'].dropna().unique().tolist())
                tag_options = ["", "[Nova Tag]"] + existing_tags
                selected_tag_option = st.selectbox("Selecione ou crie uma tag", options=tag_options)
                
                if selected_tag_option == "[Nova Tag]":
                    artist_tag = st.text_input("Digite a nova tag")
                else:
                    artist_tag = selected_tag_option
                
            if st.button("Adicionar ao mapeamento") and artist_original and artist_tag and artist_tag != "":
                # Atualizar o DataFrame de mapeamento
                mapping_df = add_artist_to_mapping(artist_original, artist_tag, st.session_state['mapping_df'])
                st.session_state['mapping_df'] = mapping_df
                
                # Atualizar a correspondência no DataFrame principal
                idx = st.session_state['processed_df']['Artist'] == artist_original
                st.session_state['processed_df'].loc[idx, 'Matched Group'] = artist_tag
                
                st.success(f"Artista '{artist_original}' adicionado ao mapeamento com tag '{artist_tag}'")
                
                # Oferecer download do mapeamento atualizado
                mapping_data = export_mapping_df(mapping_df)
                if mapping_data:
                    st.download_button(
                        label="Baixar Mapeamento Atualizado",
                        data=mapping_data,
                        file_name="mapping-rubricas-atualizado.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
    
    # Gerar resumo quando a taxa de câmbio for informada
    if fx_rate > 0 and st.session_state['processed_df'] is not None:
        # Gerar o resumo
        summary_df, artist_dfs, total_geral_values, unclassified_artists = generate_summary(
            st.session_state['processed_df'],
            fx_rate,
            debug=st.session_state['debug_mode']
        )
        
        # Armazenar no session_state
        st.session_state.summary_df = summary_df
        st.session_state.artist_dataframes = artist_dfs
        st.session_state.total_geral_values = total_geral_values
        st.session_state['unclassified_artists'] = unclassified_artists
        st.session_state.show_summary = True

# Exibição do resumo e download
if st.session_state.show_summary and st.session_state.summary_df is not None:
    st.divider()
    st.write("### Agrupamento por artista:")
    
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
                # Limpar nome de arquivo
                safe_name = re.sub(r'[\\/*?:"<>|]', "", artist)
                excel_data = create_excel_with_formatted_numbers(artist_df, f"{safe_name}.xlsx")
                zip_file.writestr(f"{safe_name}.xlsx", excel_data)
            
            # Adicionar o arquivo principal processado
            if st.session_state.processed_data:
                zip_file.writestr("Relatório_Processado_Completo.xlsx", st.session_state.processed_data)
                
            # Adicionar o mapeamento atualizado
            mapping_data = export_mapping_df(st.session_state['mapping_df'])
            if mapping_data:
                zip_file.writestr("Mapeamento_Artistas.xlsx", mapping_data)
        
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
        
        # Opção para download da lista de não classificados
        unclassified_df = unclassified_artists_to_dataframe(st.session_state['unclassified_artists'])
        if not unclassified_df.empty:
            excel_data = create_excel_with_formatted_numbers(unclassified_df, "artistas_nao_classificados.xlsx")
            st.download_button(
                label="Baixar lista de artistas não classificados",
                data=excel_data,
                file_name="artistas_nao_classificados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        for artist_info in st.session_state['unclassified_artists']:
            st.markdown(
                f"- {artist_info['artist']}: USD {format_br(artist_info['net_dollars'])} "
                f"(BRL {format_br(artist_info['brl'])})"
            )
            
        # Sugestão para adicionar todos os artistas não classificados ao mapeamento (modo debug)
        if st.session_state['debug_mode'] and st.button("Adicionar todos os não classificados ao mapeamento"):
            added_count = 0
            for artist_info in st.session_state['unclassified_artists']:
                # Adiciona cada artista como sua própria tag (1:1)
                artist_name = artist_info['artist']
                st.session_state['mapping_df'] = add_artist_to_mapping(
                    artist_name, 
                    artist_name, 
                    st.session_state['mapping_df']
                )
                added_count += 1
                
            st.success(f"✅ {added_count} artistas adicionados ao mapeamento como suas próprias tags.")
            
            # Oferecer download do mapeamento atualizado
            mapping_data = export_mapping_df(st.session_state['mapping_df'])
            if mapping_data:
                st.download_button(
                    label="Baixar Mapeamento Atualizado com Todos os Artistas",
                    data=mapping_data,
                    file_name="mapping-rubricas-completo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )