import streamlit as st
import pandas as pd
import io
from datetime import datetime

st.title("Processamento de Royalties")
st.write("Faça upload do arquivo xlsx contendo as planilhas Masters, Youtube Channels e Shares In & Out")

st.divider()

# Upload do arquivo
uploaded_file = st.file_uploader("Selecione o arquivo xlsx", type=['xlsx'])

if uploaded_file is not None:
    try:
        # Ler as planilhas
        df_masters = pd.read_excel(uploaded_file, sheet_name='Masters')
        df_youtube = pd.read_excel(uploaded_file, sheet_name='Youtube Channels')
        df_shares = pd.read_excel(uploaded_file, sheet_name='Shares In & Out')
        
        st.success("Arquivo carregado com sucesso")
        st.divider()
        
        # RESUMO 1: Soma por planilha e moeda
        st.subheader("Valores por planilha original")
        
        def show_summary_df(df, sheet_name):
            st.write(f"**{sheet_name}:**")
            if df.empty or 'Net' not in df.columns or df['Net'].isna().all() or df['Net'].sum() == 0:
                st.write("*Sem rendimentos*")
            else:
                if 'Currency' in df.columns:
                    summary = df.groupby('Currency')['Net'].sum().reset_index()
                    summary.columns = ['Moeda', 'Valor']
                    st.dataframe(summary, hide_index=True, use_container_width=True)
                else:
                    st.write(f"Total: {df['Net'].sum():,.2f}")
        
        show_summary_df(df_masters, "Masters")
        show_summary_df(df_youtube, "Youtube Channels")
        show_summary_df(df_shares, "Shares In & Out")
        
        # Análise Share-in e Share-out
        if not df_shares.empty and 'Share Type' in df_shares.columns and 'Net' in df_shares.columns:
            st.write("")
            
            share_in = df_shares[df_shares['Share Type'] == 'In']
            share_out = df_shares[df_shares['Share Type'] == 'Out']
            
            st.write("**Share-In:**")
            if share_in.empty or share_in['Net'].sum() == 0:
                st.write("*Sem rendimentos*")
            else:
                if 'Currency' in share_in.columns:
                    summary_in = share_in.groupby('Currency')['Net'].sum().reset_index()
                    summary_in.columns = ['Moeda', 'Valor']
                    st.dataframe(summary_in, hide_index=True, use_container_width=True)
            
            st.write("**Share-Out:**")
            if share_out.empty or share_out['Net'].sum() == 0:
                st.write("*Sem rendimentos*")
            else:
                if 'Currency' in share_out.columns:
                    summary_out = share_out.groupby('Currency')['Net'].sum().reset_index()
                    summary_out.columns = ['Moeda', 'Valor']
                    st.dataframe(summary_out, hide_index=True, use_container_width=True)
        
        st.divider()
        
        # Processamento dos dados
        st.subheader("Processamento dos dados")
        
        # Filtrar Shares In & Out
        # Excluir "listener-1703345420400" da coluna Receiver Name
        df_shares_filtered = df_shares[df_shares['Receiver Name'] != 'listener-1703345420400'].copy()
        
        # Separar YouTube Video para concatenar com Youtube Channels
        df_shares_youtube = df_shares_filtered[df_shares_filtered['Product Type'] == 'YouTube Video'].copy()
        
        # Excluir YouTube Video do restante (para concatenar com Masters)
        df_shares_masters = df_shares_filtered[df_shares_filtered['Product Type'] != 'YouTube Video'].copy()
        
        # Mapeamento e concatenação Masters + Shares In & Out
        df_shares_masters_mapped = df_shares_masters.rename(columns={
            'Title': 'Track Title',
            'Artists': 'Artists',
            'Product Type': 'Product Type',
            'ID': 'ISRC',
            'Parent ID': 'UPC',
            'Store': 'Store',
            'Territory': 'Territory',
            'Sale Type': 'Sale Type',
            'Transaction Month': 'Transaction Month',
            'Accounted Date': 'Accounted Date',
            'Currency': 'Currency',
            'Quantity': 'Quantity',
            'Net': 'Net'
        })
        
        # Manter apenas as colunas mapeadas
        columns_masters = ['Track Title', 'Artists', 'Product Type', 'ISRC', 'UPC', 'Store', 
                          'Territory', 'Sale Type', 'Transaction Month', 'Accounted Date', 
                          'Currency', 'Quantity', 'Net']
        
        df_shares_masters_mapped = df_shares_masters_mapped[columns_masters]
        df_masters_concat = pd.concat([df_masters, df_shares_masters_mapped], ignore_index=True)
        
        # Mapeamento e concatenação Youtube Channels + Shares In & Out (YouTube Video)
        df_shares_youtube_mapped = df_shares_youtube.rename(columns={
            'Title': 'Video Title',
            'ID': 'Video ID',
            'Parent ID': 'Channel ID',
            'Store': 'Store',
            'Territory': 'Territory',
            'Sale Type': 'Sale Type',
            'Transaction Month': 'Transaction Month',
            'Accounted Date': 'Accounted Date',
            'Currency': 'Currency',
            'Quantity': 'Quantity',
            'Net': 'Net'
        })
        
        # Manter apenas as colunas mapeadas
        columns_youtube = ['Video Title', 'Video ID', 'Channel ID', 'Store', 'Territory', 
                          'Sale Type', 'Transaction Month', 'Accounted Date', 'Currency', 
                          'Quantity', 'Net']
        
        df_shares_youtube_mapped = df_shares_youtube_mapped[columns_youtube]
        df_youtube_concat = pd.concat([df_youtube, df_shares_youtube_mapped], ignore_index=True)
        
        st.success("Dados concatenados com sucesso")
        st.divider()
        
        # RESUMO 2: Valores após concatenação
        st.subheader("Valores após concatenação")
        
        st.write("**Masters + Shares In & Out:**")
        if df_masters_concat.empty or df_masters_concat['Net'].sum() == 0:
            st.write("*Sem rendimentos*")
        else:
            summary_masters = df_masters_concat.groupby('Currency')['Net'].sum().reset_index()
            summary_masters.columns = ['Moeda', 'Valor']
            st.dataframe(summary_masters, hide_index=True, use_container_width=True)
        
        st.write("**Youtube Channels:**")
        if df_youtube_concat.empty or df_youtube_concat['Net'].sum() == 0:
            st.write("*Sem rendimentos*")
        else:
            summary_youtube = df_youtube_concat.groupby('Currency')['Net'].sum().reset_index()
            summary_youtube.columns = ['Moeda', 'Valor']
            st.dataframe(summary_youtube, hide_index=True, use_container_width=True)
        
        st.divider()
        
        # Inputs para taxas bancárias
        st.subheader("Taxas bancárias")
        
        col1, col2 = st.columns(2)
        with col1:
            taxa_brl = st.number_input("Taxa BRL", min_value=0.0, value=0.0, step=0.01, format="%.2f", help="Valor da taxa bancária a ser descontada proporcionalmente")
        with col2:
            taxa_usd = st.number_input("Taxa USD", min_value=0.0, value=0.0, step=0.01, format="%.2f", help="Valor da taxa bancária a ser descontada proporcionalmente")
        
        st.divider()
        
        # Aplicar descontos proporcionais
        def apply_discount(df, currency, discount_amount):
            if df.empty or discount_amount == 0:
                return df
            
            df_currency = df[df['Currency'] == currency].copy()
            if df_currency.empty or df_currency['Net'].sum() == 0:
                return df
            
            total = df_currency['Net'].sum()
            df.loc[df['Currency'] == currency, 'Net'] = df.loc[df['Currency'] == currency, 'Net'] * (1 - discount_amount / total)
            
            return df
        
        # Criar cópias para aplicar os descontos
        df_masters_final = df_masters_concat.copy()
        df_youtube_final = df_youtube_concat.copy()
        
        # Aplicar descontos
        if taxa_brl > 0 and 'BRL' in df_masters_final['Currency'].values:
            total_brl = df_masters_final[df_masters_final['Currency'] == 'BRL']['Net'].sum()
            if total_brl > 0:
                df_masters_final.loc[df_masters_final['Currency'] == 'BRL', 'Net'] = \
                    df_masters_final.loc[df_masters_final['Currency'] == 'BRL', 'Net'] - \
                    (df_masters_final.loc[df_masters_final['Currency'] == 'BRL', 'Net'] / total_brl * taxa_brl)
        
        if taxa_usd > 0 and 'USD' in df_masters_final['Currency'].values:
            total_usd = df_masters_final[df_masters_final['Currency'] == 'USD']['Net'].sum()
            if total_usd > 0:
                df_masters_final.loc[df_masters_final['Currency'] == 'USD', 'Net'] = \
                    df_masters_final.loc[df_masters_final['Currency'] == 'USD', 'Net'] - \
                    (df_masters_final.loc[df_masters_final['Currency'] == 'USD', 'Net'] / total_usd * taxa_usd)
        
        if taxa_brl > 0 and 'BRL' in df_youtube_final['Currency'].values:
            total_brl = df_youtube_final[df_youtube_final['Currency'] == 'BRL']['Net'].sum()
            if total_brl > 0:
                df_youtube_final.loc[df_youtube_final['Currency'] == 'BRL', 'Net'] = \
                    df_youtube_final.loc[df_youtube_final['Currency'] == 'BRL', 'Net'] - \
                    (df_youtube_final.loc[df_youtube_final['Currency'] == 'BRL', 'Net'] / total_brl * taxa_brl)
        
        if taxa_usd > 0 and 'USD' in df_youtube_final['Currency'].values:
            total_usd = df_youtube_final[df_youtube_final['Currency'] == 'USD']['Net'].sum()
            if total_usd > 0:
                df_youtube_final.loc[df_youtube_final['Currency'] == 'USD', 'Net'] = \
                    df_youtube_final.loc[df_youtube_final['Currency'] == 'USD', 'Net'] - \
                    (df_youtube_final.loc[df_youtube_final['Currency'] == 'USD', 'Net'] / total_usd * taxa_usd)
        
        # RESUMO 3: Valores após descontos
        st.subheader("Valores após descontos das taxas")
        
        st.write("**Masters + Shares In & Out:**")
        if df_masters_final.empty or df_masters_final['Net'].sum() == 0:
            st.write("*Sem rendimentos*")
        else:
            summary_masters_final = df_masters_final.groupby('Currency')['Net'].sum().reset_index()
            summary_masters_final.columns = ['Moeda', 'Valor']
            st.dataframe(summary_masters_final, hide_index=True, use_container_width=True)
        
        st.write("**Youtube Channels:**")
        if df_youtube_final.empty or df_youtube_final['Net'].sum() == 0:
            st.write("*Sem rendimentos*")
        else:
            summary_youtube_final = df_youtube_final.groupby('Currency')['Net'].sum().reset_index()
            summary_youtube_final.columns = ['Moeda', 'Valor']
            st.dataframe(summary_youtube_final, hide_index=True, use_container_width=True)
        
        st.divider()
        
        # Downloads
        st.subheader("Download dos resultados finais")
        
        # Função para criar arquivo Excel
        def to_excel(df):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            return output.getvalue()
        
        col1, col2 = st.columns(2)
        
        # Downloads Masters por moeda
        with col1:
            st.write("**Masters + Shares In & Out:**")
            if not df_masters_final.empty:
                currencies_masters = df_masters_final['Currency'].unique()
                for currency in currencies_masters:
                    df_download = df_masters_final[df_masters_final['Currency'] == currency]
                    excel_data = to_excel(df_download)
                    st.download_button(
                        label=f"Download Masters {currency}",
                        data=excel_data,
                        file_name=f"Masters_{currency}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
        
        # Downloads Youtube por moeda
        with col2:
            st.write("**Youtube Channels:**")
            if not df_youtube_final.empty:
                currencies_youtube = df_youtube_final['Currency'].unique()
                for currency in currencies_youtube:
                    df_download = df_youtube_final[df_youtube_final['Currency'] == currency]
                    excel_data = to_excel(df_download)
                    st.download_button(
                        label=f"Download Youtube {currency}",
                        data=excel_data,
                        file_name=f"Youtube_{currency}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
        
        st.divider()
        
        # RESUMO 4: Valores finais
        st.subheader("Valores finais por moeda e dataframe")
        
        st.write("**Masters + Shares In & Out:**")
        if df_masters_final.empty or df_masters_final['Net'].sum() == 0:
            st.write("*Sem rendimentos*")
        else:
            summary_masters_final = df_masters_final.groupby('Currency')['Net'].sum().reset_index()
            summary_masters_final.columns = ['Moeda', 'Valor']
            st.dataframe(summary_masters_final, hide_index=True, use_container_width=True)
        
        st.write("**Youtube Channels:**")
        if df_youtube_final.empty or df_youtube_final['Net'].sum() == 0:
            st.write("*Sem rendimentos*")
        else:
            summary_youtube_final = df_youtube_final.groupby('Currency')['Net'].sum().reset_index()
            summary_youtube_final.columns = ['Moeda', 'Valor']
            st.dataframe(summary_youtube_final, hide_index=True, use_container_width=True)
        
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
        st.write("Certifique-se de que o arquivo contém as planilhas Masters, Youtube Channels e Shares In & Out")

else:
    st.info("Aguardando upload do arquivo")