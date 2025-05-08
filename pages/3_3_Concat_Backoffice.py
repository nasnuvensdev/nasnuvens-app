import streamlit as st
import pandas as pd
import os
from io import BytesIO
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
pd.set_option('display.max_colwidth', None)

#----------------------------------
# Concat & Totalize Files
#----------------------------------
st.title("Concat Backoffice")
st.caption("Concatena e totaliza os arquivos Backoffice para conferência e inclusão no Reprtoir.")
    
# Upload dos arquivos
uploaded_files = st.file_uploader("Faça o upload dos arquivos Excel", 
                                type=None, 
                                accept_multiple_files=True,
                                key="concat_files",
                               )

if uploaded_files:
    # Botões para escolher a ação
    concat_button = st.button('Concatenar arquivos', type='secondary')
    
    if concat_button:
        try:
            # Lista para armazenar os DataFrames
            dataframes = []
            
            # Processamento com barra de progresso
            progress_bar = st.progress(0)
            for i, file in enumerate(uploaded_files):
                progress = (i + 1) / len(uploaded_files)
                progress_bar.progress(progress)
                
                # Lê o arquivo e adiciona ao DataFrame
                df = pd.read_excel(file)
                dataframes.append(df)
                            
            # Concatena todos os DataFrames
            concatenated_df = pd.concat(dataframes, ignore_index=True)
            
            # Informações sobre o resultado
            st.success(f"""
            Concatenação concluída com sucesso!
            - Total de arquivos: {len(dataframes)}
            - Total de linhas: {len(concatenated_df)}
            - Total de colunas: {len(concatenated_df.columns)}
            """)
            
            # Prepara o arquivo para download
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                concatenated_df.to_excel(writer, index=False)
            
            # Botão de download
            st.download_button(
                label="📥 Baixar arquivo concatenado",
                data=buffer.getvalue(),
                file_name="arquivos_concatenados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            st.error(f"Erro ao concatenar os arquivos: {str(e)}")
    
    totals_button = st.button('Calcular totais', type='primary')
    
    if totals_button:
        try:
            # Lista para armazenar os resultados
            results = []
            
            # Processamento com barra de progresso
            progress_bar = st.progress(0)
            for i, file in enumerate(uploaded_files):
                progress = (i + 1) / len(uploaded_files)
                progress_bar.progress(progress)
                
                # Leitura do arquivo Excel
                if "ST" in file.name.upper():
                    df = pd.read_excel(file)
                    
                    if "ROYALTIES_TO_BE_PAID" in df.columns:
                        total_royalties = df["ROYALTIES_TO_BE_PAID"].sum()
                        results.append((file.name, total_royalties))
                    else:
                        st.warning(f"A coluna 'ROYALTIES_TO_BE_PAID' não foi encontrada em {file.name}")

            if results:
                # Cria o DataFrame com os resultados
                df_results = pd.DataFrame(results, columns=["Arquivo", "Soma de ROYALTIES_TO_BE_PAID"])

                # Arredonda os valores para duas casas decimais
                df_results["Soma de ROYALTIES_TO_BE_PAID"] = df_results["Soma de ROYALTIES_TO_BE_PAID"].round(2)

                # Adiciona uma linha com a soma total
                total_royalties_sum = df_results["Soma de ROYALTIES_TO_BE_PAID"].sum().round(2)
                df_results.loc[len(df_results.index)] = ["Total", total_royalties_sum]

                # Formata como moeda brasileira
                df_results["Soma de ROYALTIES_TO_BE_PAID"] = df_results["Soma de ROYALTIES_TO_BE_PAID"].apply(
                    lambda x: f"R${x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )

                # Exibe o DataFrame
                st.dataframe(df_results)

                st.write(f'Total: **{total_royalties_sum}**')
                
            else:
                st.warning("Nenhum arquivo válido para totalização encontrado.")

        except Exception as e:
            st.error(f"Erro ao processar os totais: {str(e)}")

else:
    st.info("Aguardando upload dos arquivos...")