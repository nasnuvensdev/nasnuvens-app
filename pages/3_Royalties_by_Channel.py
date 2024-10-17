import streamlit as st
import pandas as pd
import os

#----------------------------------
# Royalties by Channel App
#----------------------------------
title = st.title("Royalties by Channel")
descritivo = st.caption("Cria a planilha Royalties by Channel para uso do financeiro.")

# Função para limpar as aspas que podem ser incluídas ao copiar o caminho
def clean_path(path):
    return path.strip('"')

# Inputs do usuário para os caminhos dos arquivos
source_path = clean_path(st.text_input('Caminho do arquivo CSV original'))  # O caminho do arquivo CSV original
output_file_path = clean_path(st.text_input('Caminho da pasta de saída'))  # O caminho onde o arquivo processado será salvo
target_path = 'data/planilha-target.xlsx'
mapping_file_path = 'data/mapping-rubricas.xlsx'

# Variáveis adicionais para o mês e ano
mes = st.number_input('Mês', min_value=1, max_value=12, value=1, step=1)  # Exemplo de período
ano = st.number_input('Ano', min_value=1900, max_value=2100, value=2024, step=1)
source_name = st.text_input('Nome da Fonte', value='ABRAMUS')  # Variável para a coluna Source

# Função para extrair as informações iniciais diretamente do arquivo CSV
def extract_catalog_and_period(source_path):
    with open(source_path, 'r', encoding='latin1') as file:
        metadata = [next(file).strip() for _ in range(4)]
    
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

# Criando colunas para centralizar botão
col1, col2, col3 = st.columns([1.6,1,1.6])

with col2:

    # Função principal
    def main():
        # Botão para iniciar o processamento
        if st.button('Criar arquivo', type='primary'):
            # Verifica se os caminhos foram fornecidos
            if source_path and output_file_path:
                try:
                    # Lendo as planilhas
                    st.write("Carregando os dados...")
                    target_df = pd.read_excel(target_path, header=None)  # Planilha com headers padrão
                    source_df = pd.read_csv(source_path, sep=';', encoding='latin1', header=4)  # Planilha com conteúdo a ser copiado
                    
                    # Extraindo Catalog e Period da planilha de origem
                    catalog, period = extract_catalog_and_period(source_path)

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

                    # Definindo o nome completo do arquivo de saída
                    output_filename = os.path.join(output_file_path, f'Royalties_by_Channel_{catalog}.xlsx')
                    
                    # Salvando o DataFrame final em um novo arquivo Excel
                    final_df.to_excel(output_filename, index=False)

                    # Informar o usuário que o processo foi concluído
                    st.success(f'Arquivo processado e salvo como {output_filename}')

                except Exception as e:
                    st.error(f"Ocorreu um erro: {e}")

    if __name__ == "__main__":
        main()
