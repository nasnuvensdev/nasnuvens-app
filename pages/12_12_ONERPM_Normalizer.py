import streamlit as st
import pandas as pd
import io
from typing import Dict, List, Set

# Configuração da página
st.set_page_config(
    page_title="NN App",
    layout="wide"
)

# Estruturas de dados
estrutura_final = [
    "Album Title",
    "Track Title", 
    "Artists",
    "Label",
    "UPC",
    "ISRC",
    "Product Type",
    "Store",
    "Territory",
    "Sale Type",
    "Transaction Month",
    "Accounted Date",
    "Original Currency",
    "Gross (Original Currency)",
    "Exchange Rate",
    "Currency",
    "Gross",
    "Quantity",
    "Average Unit Gross",
    "% Share",
    "Fees",
    "Net",
    "Gross BRL",   # Nova coluna calculada
    "Net BRL",
    "Payer Name",  # Nova coluna
    "Origem"  # Nova coluna para identificar planilha de origem
]

mapeamento_masters = {
    'Album Title': 'Album Title',
    'Track Title': 'Track Title',
    'Artists': 'Artists',
    'Label': 'Label',
    'UPC': 'UPC',
    'ISRC': 'ISRC',
    'Product Type': 'Product Type',
    'Store': 'Store',
    'Territory': 'Territory',
    'Sale Type': 'Sale Type',
    'Transaction Month': 'Transaction Month',
    'Accounted Date': 'Accounted Date',
    'Original Currency': 'Original Currency',
    'Gross (Original Currency)': 'Gross (Original Currency)',
    'Exchange Rate': 'Exchange Rate',
    'Currency': 'Currency',
    'Gross': 'Gross',
    'Quantity': 'Quantity',
    'Average Unit Gross': 'Average Unit Gross',
    '% Share': '% Share',
    'Fees': 'Fees',
    'Net': 'Net'
}

mapeamento_youtube_channels = {
    'Video Title': 'Track Title',
    'Channel Name': 'Artists',
    'Channel ID': 'UPC',
    'Video ID': 'ISRC',
    'Store': 'Store',
    'Territory': 'Territory',
    'Sale Type': 'Sale Type',
    'Transaction Month': 'Transaction Month',
    'Accounted Date': 'Accounted Date',
    'Original Currency': 'Original Currency',
    'Gross (Original Currency)': 'Gross (Original Currency)',
    'Exchange Rate': 'Exchange Rate',
    'Currency': 'Currency',
    'Gross': 'Gross',
    'Quantity': 'Quantity',
    'Average Unit Gross': 'Average Unit Gross',
    '% Share': '% Share',
    'Fees': 'Fees',
    'Net': 'Net'
}

mapeamento_shares_in_out = {
    'Title': 'Album Title',
    'Artists': 'Artists',
    'Parent ID': 'UPC',
    'ID': 'ISRC',
    'Product Type': 'Product Type',
    'Store': 'Store',
    'Territory': 'Territory',
    'Sale Type': 'Sale Type',
    'Transaction Month': 'Transaction Month',
    'Accounted Date': 'Accounted Date',
    'Currency': 'Currency',
    'Quantity': 'Quantity',
    '% Share In/Out': '% Share',
    'Net': 'Net',
    'Payer Name': 'Payer Name'  # Nova coluna mapeada
}

def identificar_moedas(dfs: Dict[str, pd.DataFrame]) -> Set[str]:
    """Identifica todas as moedas únicas nas planilhas"""
    moedas = set()
    for nome_planilha, df in dfs.items():
        if 'Currency' in df.columns:
            moedas_planilha = df['Currency'].dropna().unique()
            moedas.update(moedas_planilha)
    return moedas

def processar_planilha(df: pd.DataFrame, mapeamento: Dict[str, str], nome_planilha: str) -> pd.DataFrame:
    """Processa uma planilha aplicando o mapeamento de colunas"""
    # Filtra apenas "In" para Shares In & Out
    if nome_planilha == "Shares In & Out" and 'Share Type' in df.columns:
        df = df[df['Share Type'] == 'In'].copy()
    
    # Renomeia as colunas conforme o mapeamento
    df_processado = df.rename(columns=mapeamento)
    
    # Adiciona "Video" na coluna Product Type para YouTube Channels
    if nome_planilha == "Youtube Channels":
        df_processado['Product Type'] = 'Video'
    
    # Adiciona a coluna "Origem" com o nome da planilha
    df_processado['Origem'] = nome_planilha
    
    # Garante que todas as colunas da estrutura final existam
    for coluna in estrutura_final:
        if coluna not in df_processado.columns:
            df_processado[coluna] = None
    
    # Reordena as colunas conforme a estrutura final
    df_processado = df_processado[estrutura_final]
    
    return df_processado

def processar_shares_out(df: pd.DataFrame, taxas_cambio: Dict[str, float]) -> pd.DataFrame:
    """Processa os dados de Share Out separadamente"""
    if 'Share Type' not in df.columns:
        return pd.DataFrame()
    
    # Filtra apenas "Out"
    df_out = df[df['Share Type'] == 'Out'].copy()
    
    if df_out.empty:
        return pd.DataFrame()
    
    # Calcula Net BRL para Share Out
    def converter_para_brl(row):
        if pd.isna(row['Net']) or pd.isna(row['Currency']):
            return None
        
        moeda = row['Currency']
        valor_net = row['Net']
        
        if moeda == 'BRL':
            return valor_net
        elif moeda in taxas_cambio:
            return valor_net * taxas_cambio[moeda]
        else:
            return None
    
    df_out['Net BRL'] = df_out.apply(converter_para_brl, axis=1)
    
    # Seleciona apenas as colunas necessárias para análise
    colunas_share_out = ['Receiver Name', 'Net', 'Currency', 'Net BRL', 'Artists', 'Title']
    colunas_existentes = [col for col in colunas_share_out if col in df_out.columns]
    
    return df_out[colunas_existentes]

def calcular_gross_brl(df: pd.DataFrame, taxas_cambio: Dict[str, float]) -> pd.DataFrame:
    """Calcula a coluna Gross BRL baseada nas taxas de câmbio"""
    df = df.copy()
    
    def converter_gross_para_brl(row):
        if pd.isna(row['Gross']) or pd.isna(row['Currency']):
            return None
        
        moeda = row['Currency']
        valor_gross = row['Gross']
        
        if moeda == 'BRL':
            return valor_gross
        elif moeda in taxas_cambio:
            return valor_gross * taxas_cambio[moeda]
        else:
            return None
    
    df['Gross BRL'] = df.apply(converter_gross_para_brl, axis=1)
    return df

def calcular_net_brl(df: pd.DataFrame, taxas_cambio: Dict[str, float]) -> pd.DataFrame:
    """Calcula a coluna Net BRL baseada nas taxas de câmbio"""
    df = df.copy()
    
    def converter_para_brl(row):
        if pd.isna(row['Net']) or pd.isna(row['Currency']):
            return None
        
        moeda = row['Currency']
        valor_net = row['Net']
        
        if moeda == 'BRL':
            return valor_net
        elif moeda in taxas_cambio:
            return valor_net * taxas_cambio[moeda]
        else:
            return None
    
    df['Net BRL'] = df.apply(converter_para_brl, axis=1)
    return df

def criar_resumo_financeiro_por_origem(df_final: pd.DataFrame) -> pd.DataFrame:
    """Cria um resumo financeiro por origem das planilhas"""
    resumo_data = []
    
    # Agrupa por origem e calcula totais
    for origem in df_final['Origem'].dropna().unique():
        df_origem = df_final[df_final['Origem'] == origem]
        total_net_brl = df_origem['Net BRL'].sum()
        registros = len(df_origem)
        
        resumo_data.append({
            'Origem': origem,
            'Registros': registros,
            'Total Net BRL': total_net_brl
        })
    
    resumo_df = pd.DataFrame(resumo_data)
    # Adiciona linha de total
    total_registros = resumo_df['Registros'].sum()
    total_net_brl = resumo_df['Total Net BRL'].sum()
    
    resumo_df = pd.concat([
        resumo_df,
        pd.DataFrame([{
            'Origem': 'TOTAL',
            'Registros': total_registros,
            'Total Net BRL': total_net_brl
        }])
    ], ignore_index=True)
    
    return resumo_df

def criar_resumo_share_out(df_share_out: pd.DataFrame) -> pd.DataFrame:
    """Cria resumo dos Share Out por Receiver Name"""
    if df_share_out.empty:
        return pd.DataFrame()
    
    resumo = df_share_out.groupby('Receiver Name').agg({
        'Net BRL': 'sum',
        'Net': 'sum'
    }).reset_index()
    
    resumo = resumo.sort_values('Net BRL', ascending=False)
    return resumo

# Interface Streamlit
st.title("OneRPM Normalizer")
st.caption("Prepara o relatório OneRPM para upload no Reprtoir")

st.divider()

# Upload do arquivo
uploaded_file = st.file_uploader(
    "Faça upload do arquivo Excel com as planilhas OneRPM:",
    type=['xlsx', 'xls'],
    help="O arquivo deve conter as abas: Masters, Youtube Channels, e Shares In & Out"
)

if uploaded_file is not None:
    try:
        # Lê todas as abas do arquivo
        with st.spinner("Carregando planilhas..."):
            excel_file = pd.ExcelFile(uploaded_file)
            
            # Verifica se as abas necessárias existem
            abas_necessarias = ["Masters", "Youtube Channels", "Shares In & Out"]
            abas_existentes = excel_file.sheet_names
            
            st.info(f"Abas encontradas: {', '.join(abas_existentes)}")
            
            # Carrega as planilhas
            dfs = {}
            for aba in abas_necessarias:
                if aba in abas_existentes:
                    dfs[aba] = pd.read_excel(uploaded_file, sheet_name=aba)
                    #st.success(f"✓ {aba}: {len(dfs[aba])} registros carregados")
                else:
                    st.warning(f"⚠️ Aba '{aba}' não encontrada no arquivo")
        st.divider()
        if len(dfs) > 0:
            # Identifica moedas
            moedas_encontradas = identificar_moedas(dfs)
            st.subheader("💱 Configuração de Taxas de Câmbio")
            st.write(f"Moedas encontradas: {', '.join(sorted(moedas_encontradas))}")
            
            # Cria inputs para taxas de câmbio
            taxas_cambio = {}
            col1, col2, col3 = st.columns(3)
            
            # Define valores padrão para moedas comuns
            valores_padrao = {
                'USD': 5.0,
                'EUR': 5.5,
                'GBP': 6.0,
                'CAD': 3.8,
                'AUD': 3.3,
                'JPY': 0.035
            }
            
            for i, moeda in enumerate(sorted(moedas_encontradas)):
                if moeda != 'BRL':  # BRL não precisa de conversão
                    col = [col1, col2, col3][i % 3]
                    with col1:
                        valor_padrao = valores_padrao.get(moeda, 1.0)
                        taxa = st.number_input(
                            f"Taxa {moeda} → BRL:",
                            min_value=0.0,
                            value=valor_padrao,
                            step=0.01,
                            format="%.4f",
                            key=f"taxa_{moeda}",
                            help=f"Taxa de conversão de {moeda} para Real brasileiro"
                        )
                        taxas_cambio[moeda] = taxa
                else:
                    taxas_cambio[moeda] = 1.0
            
            # Botão para processar
            if st.button("Criar Planilha", type="primary"):
                with st.spinner("Processando dados..."):
                    dfs_processados = []
                    df_share_out = pd.DataFrame()
                    
                    # Processa cada planilha
                    if "Masters" in dfs:
                        df_masters = processar_planilha(dfs["Masters"], mapeamento_masters, "Masters")
                        df_masters = calcular_net_brl(df_masters, taxas_cambio)
                        dfs_processados.append(df_masters)
                        st.success(f"✓ Masters processado: {len(df_masters)} registros")
                    
                    if "Youtube Channels" in dfs:
                        df_youtube = processar_planilha(dfs["Youtube Channels"], mapeamento_youtube_channels, "Youtube Channels")
                        df_youtube = calcular_net_brl(df_youtube, taxas_cambio)
                        dfs_processados.append(df_youtube)
                        st.success(f"✓ Youtube Channels processado: {len(df_youtube)} registros")
                    
                    if "Shares In & Out" in dfs:
                        # Processa Share In (para concatenar)
                        df_shares_in = processar_planilha(dfs["Shares In & Out"], mapeamento_shares_in_out, "Shares In & Out")
                        df_shares_in = calcular_net_brl(df_shares_in, taxas_cambio)
                        dfs_processados.append(df_shares_in)
                        st.success(f"✓ Shares In processado: {len(df_shares_in)} registros")
                        
                        # Processa Share Out (separadamente)
                        df_share_out = processar_shares_out(dfs["Shares In & Out"], taxas_cambio)
                        if not df_share_out.empty:
                            st.success(f"✓ Shares Out processado: {len(df_share_out)} registros para análise")
                    
                    # Concatena todas as planilhas
                    if dfs_processados:
                        df_final = pd.concat(dfs_processados, ignore_index=True)
                        
                        # Armazena no session_state
                        st.session_state['df_final'] = df_final
                        st.session_state['df_share_out'] = df_share_out
                        st.session_state['taxas_cambio'] = taxas_cambio
                        st.session_state['processamento_concluido'] = True
                        
                        st.success(f"🎉 Processamento concluído! Total de registros: {len(df_final)}")
                        st.rerun()  # Atualiza a página para mostrar os resultados
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")

# Exibe resultados somente após processamento
if 'df_final' in st.session_state and 'processamento_concluido' in st.session_state:
    df_final = st.session_state['df_final']
    df_share_out = st.session_state.get('df_share_out', pd.DataFrame())
    taxas_cambio = st.session_state['taxas_cambio']
    
    st.divider()
    
    st.subheader("📊 Prévia dos Dados Processados")
    
    # Mostra prévia
    st.dataframe(df_final.head(10), use_container_width=True, hide_index=True)
    #st.info(f"Mostrando 10 primeiros registros de {len(df_final)} total")
    st.divider()
    # Resumo financeiro por origem
    
    st.subheader("💲Resumo Financeiro por Origem")
    resumo_origem = criar_resumo_financeiro_por_origem(df_final)
    
    # Exibe métricas em colunas
    col1, col2, col3 = st.columns(3)
    for i, row in resumo_origem.iterrows():
        if row['Origem'] != 'TOTAL':
            col = [col1, col2, col3][i % 3]
            with col:
                st.metric(
                    row['Origem'], 
                    f"R$ {row['Total Net BRL']:,.2f}",
                    f"{row['Registros']:,} registros"
                )
    
    # Total geral
    total_brl = resumo_origem[resumo_origem['Origem'] == 'TOTAL']['Total Net BRL'].iloc[0]
    st.metric("**💵 Total Geral em BRL**", f"R$ {total_brl:,.2f}")
    
    st.divider()

    # Análise de Share Out
    if not df_share_out.empty:
        st.subheader("📈Análise de Share Out")
        resumo_share_out = criar_resumo_share_out(df_share_out)
        
        if not resumo_share_out.empty:
            st.dataframe(resumo_share_out, use_container_width=True, hide_index=True)
            
            # Total de Share Out
            total_share_out = resumo_share_out['Net BRL'].sum()
            st.metric("💸 Total Share Out em BRL", f"R$ {total_share_out:,.2f}")
        else:
            st.info("Nenhum dado de Share Out encontrado")
    
    st.divider()
    
    # Botão de download
    st.subheader("📥 Download da Planilha Final")
    
    # Prepara arquivo para download
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Calcula Gross BRL apenas para o download
        df_final_download = calcular_gross_brl(df_final, taxas_cambio)
        
        # Planilha principal
        df_final_download.to_excel(writer, sheet_name='Dados Processados', index=False)
        
        # Planilha de Share Out (se existir)
        if not df_share_out.empty:
            df_share_out.to_excel(writer, sheet_name='Share Out Analysis', index=False)
            resumo_share_out = criar_resumo_share_out(df_share_out)
            if not resumo_share_out.empty:
                resumo_share_out.to_excel(writer, sheet_name='Resumo Share Out', index=False)
    
    st.download_button(
        label="📄 Baixar Planilha Processada",
        data=output.getvalue(),
        file_name="onerpm_royalties_processados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    pass
    #st.info("👆 Faça upload de um arquivo Excel para começar o processamento")

# Footer
#     st.divider()

# st.markdown("*Desenvolvido para processamento de royalties OneRPM*")