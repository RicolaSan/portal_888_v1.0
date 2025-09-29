from flask import render_template, request, jsonify
from . import controle_de_isv_bp
import pandas as pd
from datetime import datetime



# Dados das tabelas
forn_df = pd.read_csv(
    '//10.122.244.1/files/gerencial/WebISV/Forn.csv', sep=';', encoding='latin-1')


smg12_df = pd.read_csv('//10.122.244.1/files/gerencial/gerencia/edvan/smg12.f888.csv', sep=';', encoding='latin-1')

# Limpar e converter a coluna IDADE
# 1. Remover espaços em branco
smg12_df['IDADE'] = smg12_df['IDADE'].astype(str).str.strip()

# 2. Substituir vírgula por ponto (formato decimal brasileiro)
smg12_df['IDADE'] = smg12_df['IDADE'].str.replace(',', '.')

# 3. Converter para float primeiro, depois para int
smg12_df['IDADE'] = pd.to_numeric(smg12_df['IDADE'], errors='coerce')

# 4. Tratar valores NaN (se houver)
smg12_df['IDADE'] = smg12_df['IDADE'].fillna(0)

# 5. Converter para int
smg12_df['IDADE'] = smg12_df['IDADE'].astype(int)


smg12_df = smg12_df.rename(columns={
                           'MERC': 'CODIGO',
                           'ESTOQ EMB1':'ESTOQUE EMB1',
                           'ESTOQ EMB9':'ESTOQUE EMB9'})


# Convertendo ESTOQUE EMB1, ESTOQUE EMB9 para inteiros
smg12_df['ESTOQUE EMB1'] = pd.to_numeric(smg12_df['ESTOQUE EMB1'], errors='coerce').fillna(0).astype(int)
smg12_df['ESTOQUE EMB9'] = pd.to_numeric(smg12_df['ESTOQUE EMB9'], errors='coerce').fillna(0).astype(int)
# Convertendo IDADE para inteiro
smg12_df['IDADE'] = pd.to_numeric(smg12_df['IDADE'], errors='coerce').fillna(0).astype(int)

smg12_organizado_df = smg12_df[['CODIGO', 'DESCRICAO', 'EMBALAGEM','DIAS S/VND', 'IDADE','ESTOQUE EMB1', 'ESTOQUE EMB9']]


# Renomeando colunas
forn_renomeado_df = forn_df.rename(columns={
                                    'Item Produto': 'CODIGO',
                                    'Fornecedor Atual': 'CNPJ/CPF', 
                                    'Unnamed: 2': 'FORNECEDOR'}).dropna(subset=['FORNECEDOR'])


# Convertendo para string e padronizando os códigos (agora com 5 dígitos em vez de 7)
forn_renomeado_df = forn_renomeado_df.copy()
# Converter explicitamente para string antes da atribuição
codigo_forn_processado = forn_renomeado_df['CODIGO'].astype(str).apply(lambda x: x.split('.')[0].zfill(5))
forn_renomeado_df = forn_renomeado_df.astype({'CODIGO': 'object'})
forn_renomeado_df['CODIGO'] = codigo_forn_processado

smg12_organizado_df = smg12_organizado_df.copy()
# Converter explicitamente para string antes da atribuição
codigo_smg12_processado = smg12_organizado_df['CODIGO'].astype(str).str.zfill(7).str[2:]  # Remove os dois primeiros zeros
smg12_organizado_df = smg12_organizado_df.astype({'CODIGO': 'object'})
smg12_organizado_df['CODIGO'] = codigo_smg12_processado

# Realizar o merge com a opção 'indicator' para diagnosticar
tabela_unificada2_df = pd.merge(
    forn_renomeado_df, smg12_organizado_df, on='CODIGO', how='outer', indicator=True)

# Remover linhas duplicadas com base na coluna 'CODIGO'
tabela_unificada2_df = tabela_unificada2_df.drop_duplicates(subset=['CODIGO'])

# Selecionar apenas as colunas necessárias
colunas_necessarias = ['CODIGO', 'DESCRICAO', 'EMBALAGEM', 'FORNECEDOR',
                       'ESTOQUE EMB1', 'ESTOQUE EMB9', 'IDADE', 'DIAS S/VND']
tabela_unificada2_df = tabela_unificada2_df[colunas_necessarias]


def get_isv_data(search='', dias_filter='3'):
    """
    Função centralizada para obter e filtrar dados ISV
    
    Args:
        search (str): Termo de busca para filtrar por código, descrição ou fornecedor
        dias_filter (str): Número mínimo de dias sem venda para filtrar
    
    Returns:
        dict: Dicionário com success, data e total
    """
    try:
        global tabela_unificada2_df
        
        # Trabalhar com uma cópia dos dados
        dados_filtrados = tabela_unificada2_df.copy()
        
        # Garantir que todas as colunas necessárias existam e tenham valores válidos
        colunas_necessarias = ['CODIGO', 'DESCRICAO', 'EMBALAGEM', 'FORNECEDOR', 'ESTOQUE EMB1', 'ESTOQUE EMB9', 'IDADE', 'DIAS S/VND']
        
        for col in colunas_necessarias:
            if col not in dados_filtrados.columns:
                if col in ['ESTOQUE EMB1', 'ESTOQUE EMB9', 'IDADE', 'DIAS S/VND']:
                    dados_filtrados[col] = 0
                else:
                    dados_filtrados[col] = ''
        
        # Preencher valores NaN
        for col in colunas_necessarias:
            if col in ['ESTOQUE EMB1', 'ESTOQUE EMB9', 'IDADE', 'DIAS S/VND']:
                dados_filtrados[col] = pd.to_numeric(dados_filtrados[col], errors='coerce').fillna(0).astype(int)
            else:
                dados_filtrados[col] = dados_filtrados[col].fillna('')
        
        # Aplicar filtro de dias primeiro (mais restritivo)
        if dias_filter:
            try:
                dias_limite = int(dias_filter)
                dados_filtrados = dados_filtrados[dados_filtrados['DIAS S/VND'] >= dias_limite]
            except ValueError:
                pass
        
        # Aplicar filtro de busca
        if search:
            mask = (
                dados_filtrados['CODIGO'].astype(str).str.contains(search, case=False, na=False) |
                dados_filtrados['DESCRICAO'].fillna('').str.contains(search, case=False, na=False) |
                dados_filtrados['FORNECEDOR'].fillna('').str.contains(search, case=False, na=False)
            )
            dados_filtrados = dados_filtrados[mask]
        
        # Limitar resultados para melhor performance (máximo 1000 registros)
        if len(dados_filtrados) > 1000:
            dados_filtrados = dados_filtrados.head(1000)
        
        # Converter para lista de dicionários
        data = dados_filtrados.to_dict('records')
        
        return {
            'success': True,
            'data': data,
            'total': len(data)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': [],
            'total': 0
        }


@controle_de_isv_bp.route('/page')
def isv_page():
    """Página completa do ISV com dados carregados"""
    print("=== ROTA /page ACESSADA ===")
    try:
        # Carregar dados ISV
        print("Carregando dados ISV...")
        data = get_isv_data()
        print(f"Dados carregados: {len(data.get('data', []))} itens")
        print("Renderizando template...")
        return render_template('/isv_page.html', isv_data=data)
    except Exception as e:
        print(f"Erro ao carregar página ISV: {e}")
        import traceback
        traceback.print_exc()
        return render_template('/isv_page.html', isv_data={"data": [], "error": str(e)})





