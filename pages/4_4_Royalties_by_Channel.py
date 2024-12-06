import streamlit as st
import pandas as pd
import os
from io import BytesIO

#----------------------------------
# Royalties by Channel App
#----------------------------------
title = st.title("Royalties by Channel")
descritivo = st.caption("Cria a planilha Royalties by Channel para uso do financeiro.")

# Inputs do usuário para os caminhos dos arquivos
source_file = st.file_uploader('Carregar o arquivo CSV original', type=['csv',"xlsx"])  # Carregando o arquivo CSV

# Definindo caminhos fixos para as planilhas de mapeamento
target_path = 'data/mapping/planilha-target.xlsx'
mapping_file_path = 'data/mapping/mapping-rubricas.xlsx'

# Variáveis adicionais para o mês e ano
mes = st.number_input('Mês', min_value=1, max_value=12, value=1, step=1)  # Exemplo de período
ano = st.number_input('Ano', min_value=1900, max_value=2100, value=2024, step=1)
source_name = st.text_input('Nome da Fonte', value='ABRAMUS')  # Variável para a coluna Source

# Função para extrair as informações iniciais diretamente do arquivo CSV
def extract_catalog_and_period(source_file):
    metadata = [next(source_file).decode('latin1').strip() for _ in range(4)]
    
    # Extraindo "Catalog" e "Period" dos metadados
    catalog = metadata[1].split(":")[1].strip()  # Linha 2 para "Catalog"
    period = metadata[3].split(":")[1].strip()   # Linha 4 para "Period"
    
    return catalog, period

# Função para criar coluna 'Channel' baseada no arquivo de mapeamento
def map_channel(df, mapping_file_path):
    mapping_df = pd.read_excel(mapping_file_path, sheet_name='Sheet1')
    
    # Realizando o mapeamento
    df['Channel'] = df['Rubrica'].map(mapping_df.set_index('Rubrica')['Channel']).fillna("Not Mapped")
    
    return df

# Função para criar a coluna 'Key' com separador "|"
def create_key_column(df):
    df['Key'] = df.apply(lambda row: "|".join(row.values.astype(str)), axis=1)
    return df

# Função principal
def main():
    # Botão para iniciar o processamento
    if st.button('Criar arquivo', type='primary'):
        # Verifica se o arquivo CSV foi carregado
        if source_file is not None:
            try:
                # Lendo as planilhas
                st.write("Carregando os dados...")
                target_df = pd.read_excel(target_path, header=None)  # Planilha com headers padrão
                source_df = pd.read_csv(source_file, sep=';', encoding='latin1', header=4)  # Planilha com conteúdo a ser copiado
                
                # Extraindo Catalog e Period da planilha de origem
                source_file.seek(0)  # Volta ao início do arquivo carregado
                catalog, period = extract_catalog_and_period(source_file)

                # Criando o DataFrame final com os headers da target e adicionando conteúdo da source
                final_df = source_df[['RUBRICA', 'RATEIO', 'TIPO DISTRIBUIÇÃO']].copy()
                final_df.columns = ['Rubrica', 'Rendimentos', 'Tipo Distribuição']
                final_df['Catalog'] = catalog
                final_df['Period'] = f"{ano}-{str(mes).zfill(2)}"
                final_df['Source'] = source_name  # Usando a variável "Source"

                # Mapeando o Channel usando o arquivo de mapeamento
                final_df = map_channel(final_df, mapping_file_path)

                # Criando a coluna 'Key' com separador "|"
                final_df = create_key_column(final_df)

                # Reordenando as colunas
                final_df = final_df[['Catalog', 'Source', 'Period', 'Rubrica', 'Channel', 'Rendimentos', 'Tipo Distribuição', 'Key']]

                # Salvando o DataFrame final em memória (buffer)
                buffer = BytesIO()
                final_df.to_excel(buffer, index=False)
                buffer.seek(0)

                # Disponibilizando o botão de download
                st.download_button(
                    label="Baixar arquivo processado",
                    data=buffer,
                    file_name=f'Royalties_by_Channel_{catalog}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

            except Exception as e:
                st.error(f"Ocorreu um erro: {e}")

if __name__ == "__main__":
    main()
