import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime
import io
import base64

def create_download_link(df, filename):
    """Cria um link de download para o arquivo Excel"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Criar abas diferentes
        # 1. Detalhamento Completo
        df.to_excel(writer, sheet_name='Detalhamento Completo', index=False)
        
        # 2. Resumo por Música
        resumo_musica = df.groupby(['Título', 'ISRC/ISWC'])['Rendimento'].sum().reset_index()
        resumo_musica = resumo_musica.sort_values('Rendimento', ascending=False)
        resumo_musica.to_excel(writer, sheet_name='Resumo por Música', index=False)
        
        # 3. Resumo por Sociedade
        resumo_sociedade = df.groupby(['Sociedade', 'Território'])['Rendimento'].sum().reset_index()
        resumo_sociedade = resumo_sociedade.sort_values('Rendimento', ascending=False)
        resumo_sociedade.to_excel(writer, sheet_name='Resumo por Sociedade', index=False)
        
        # Obter o objeto workbook e adicionar formatos
        workbook = writer.book
        money_format = workbook.add_format({'num_format': 'R$ #,##0.00'})
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'bg_color': '#D9D9D9',
            'border': 1
        })
        
        # Formatar cada aba
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            
            # Ajustar largura das colunas
            if sheet_name == 'Detalhamento Completo':
                worksheet.set_column('A:A', 40)  # Título
                worksheet.set_column('B:B', 15)  # ISRC/ISWC
                worksheet.set_column('C:H', 20)  # Outras colunas
                worksheet.set_column('I:I', 15, money_format)  # Rendimento
            
            elif sheet_name == 'Resumo por Música':
                worksheet.set_column('A:A', 40)  # Título
                worksheet.set_column('B:B', 15)  # ISRC/ISWC
                worksheet.set_column('C:C', 15, money_format)  # Rendimento
            
            elif sheet_name == 'Resumo por Sociedade':
                worksheet.set_column('A:B', 25)  # Sociedade e Território
                worksheet.set_column('C:C', 15, money_format)  # Rendimento
    
    excel_data = output.getvalue()
    b64 = base64.b64encode(excel_data).decode('utf-8')
    return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">Download do arquivo Excel</a>'

def extract_data_from_pdf(pdf_file):
    """Extrai dados do arquivo PDF"""
    data = []
    
    with pdfplumber.open(pdf_file) as pdf:
        current_title = None
        current_isrc = None
        
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')
            
            for line in lines:
                if any(x in line for x in ['DISTRIBUIÇÃO DE DIREITOS', 'DATA :', 'TOTAL:', 'DEMONSTRATIVO', 'CPF:', 'ABRAMUS:', 'ECAD:']):
                    continue
                    
                isrc_match = re.search(r'([T]\d{10})', line)
                if isrc_match:
                    parts = line.split()
                    isrc_index = next(i for i, part in enumerate(parts) if re.match(r'T\d{10}', part))
                    current_title = ' '.join(parts[:isrc_index])
                    current_isrc = isrc_match.group(1)
                    continue
                
                parts = line.split()
                if len(parts) >= 8 and current_title:
                    try:
                        value = float(parts[-1].replace(',', '.'))
                        period_pattern = r'\d{4}/\d{2}\s*-\s*\d{4}/\d{2}'
                        period = ' '.join(re.findall(period_pattern, line)[0].split())
                        society = parts[0]
                        territory = parts[1]
                        usage_type = ' '.join(parts[2:-4])
                        holder = ' '.join(parts[-4:-2])
                        
                        data.append({
                            'Título': current_title,
                            'ISRC/ISWC': current_isrc,
                            'Sociedade': society,
                            'Território': territory,
                            'Rubrica': usage_type,
                            'Direito': 'AUTORAL',
                            'Titular': holder,
                            'Período': period,
                            'Rendimento': value
                        })
                    except:
                        continue
    
    return pd.DataFrame(data)

def main():
    st.title("ABRAMUS INT to Excel")
    
    st.caption("Processa o demonstrativo internacional da ABRAMUS em pdf e gera um relatório Excel.")
    
    uploaded_file = st.file_uploader("Faça upload do demonstrativo PDF da ABRAMUS", type="pdf")
    
    if uploaded_file is not None:
        with st.spinner('Processando o arquivo... Por favor, aguarde.'):
            try:
                # Processar o PDF
                df = extract_data_from_pdf(uploaded_file)
                
                # Mostrar estatísticas básicas
                st.success("Arquivo processado com sucesso!")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total de registros", len(df))
                with col2:
                    st.metric("Valor total", f"R$ {df['Rendimento'].sum():,.2f}")
                
                # Mostrar preview dos dados
                st.subheader("Preview dos dados extraídos")
                st.dataframe(df.head())
                
                # Criar nome do arquivo Excel mantendo o nome original do PDF
                original_filename = uploaded_file.name
                excel_filename = f"{original_filename.rsplit('.', 1)[0]}_PYTHON.xlsx"
                
                # Criar e oferecer download do Excel
                download_link = create_download_link(df, excel_filename)
                st.markdown(download_link, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"""
                Ocorreu um erro ao processar o arquivo. 
                Verifique se o arquivo está no formato correto dos demonstrativos da ABRAMUS Internacional.
                
                Erro: {str(e)}
                """)

if __name__ == "__main__":
    main()