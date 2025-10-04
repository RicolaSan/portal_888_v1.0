from flask import render_template, jsonify
import pandas as pd
import openpyxl
import locale
from datetime import datetime
import numpy as np
from . import controle_de_perdas

# Configura o locale para o formato de moeda brasileira
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
saeoi51 = pd.read_excel("//10.122.244.3/publico/ISV/SAEOI051.xlsx")

# =============== FUNÇÕES UTILITÁRIAS ===============

def format_currency(value):
    """Formata valor para moeda brasileira"""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def validate_columns(df, columns):
    """Valida se o DataFrame possui as colunas necessárias"""
    return all(col in df.columns for col in columns)

def filter_by_evento(df, eventos):
    """Filtra DataFrame por eventos específicos"""
    if not validate_columns(df, ['EVENTO']):
        return pd.DataFrame()
    
    df = df.copy()
    df['EVENTO'] = pd.to_numeric(df['EVENTO'], errors='coerce').fillna(0).astype(int)
    
    if isinstance(eventos, list):
        return df[df['EVENTO'].isin(eventos)]
    else:
        return df[df['EVENTO'] == eventos]

def filter_by_description_prefix(df, prefixes, exclude=False):
    """Filtra DataFrame por prefixos na descrição"""
    if not validate_columns(df, ['DESCRICAO']):
        return pd.DataFrame()
    
    df = df.copy()
    if exclude:
        return df[~df['DESCRICAO'].str.startswith(tuple(prefixes), na=False)]
    else:
        return df[df['DESCRICAO'].str.startswith(tuple(prefixes), na=False)]

def filter_by_operacao(df, operacao):
    """Filtra DataFrame por operação específica"""
    if not validate_columns(df, ['OPERACAO']):
        return pd.DataFrame()
    
    return df[df['OPERACAO'] == operacao]

def filter_by_date(df, target_date=None):
    """Filtra DataFrame por data específica"""
    if not validate_columns(df, ['DT.ULT.EV.']):
        return df
    
    df = df.copy()
    df['DT.ULT.EV.'] = pd.to_datetime(df['DT.ULT.EV.'], errors='coerce')
    
    if target_date is None:
        target_date = datetime.now().date()
    
    return df[df['DT.ULT.EV.'].dt.date == target_date]

def prepare_dataframe_for_display(df, columns=['MERCADORIA', 'DESCRICAO', 'VLR.TOTAL', 'EMB1'], sort_by='VLR.TOTAL', ascending=True):
    """Prepara DataFrame para exibição com colunas específicas e ordenação"""
    if df.empty:
        return df
    
    # Verifica se as colunas existem no DataFrame
    available_columns = [col for col in columns if col in df.columns]
    
    if not available_columns:
        return pd.DataFrame()
    
    df_display = df[available_columns].copy()
    
    if sort_by in df_display.columns:
        df_display = df_display.sort_values(by=sort_by, ascending=ascending)
    
    return df_display

def calculate_totals(df, vlr_col='VLR.TOTAL', emb1_col='EMB1'):
    """Calcula totais de VLR.TOTAL e EMB1"""
    vlr_total = df[vlr_col].sum() if vlr_col in df.columns and not df.empty else 0
    emb1_total = df[emb1_col].sum() if emb1_col in df.columns and not df.empty else 0
    
    return vlr_total, emb1_total

def format_dataframe_currency(df, column='VLR.TOTAL'):
    """Aplica formatação de moeda em uma coluna específica do DataFrame"""
    if column in df.columns and not df.empty:
        df = df.copy()
        df[column] = df[column].apply(format_currency)
    return df

def dataframe_to_html_table(df, empty_message="Nenhum dado disponível para exibição."):
    """Converte DataFrame para HTML ou retorna mensagem se vazio"""
    if not df.empty:
        return df.to_html(classes='table table-striped', index=False)
    else:
        return f"<p class='text-center text-muted'>{empty_message}</p>"

def process_group_data(df, group_col='GRUPO', subgroup_col='SUB-GRUPO', value_col='VLR.TOTAL', event_col='EVENTO'):
    """Processa dados agrupados por grupo e subgrupo com ordenação específica por evento"""
    if not validate_columns(df, [group_col, subgroup_col, value_col, event_col]):
        return {}
    
    # Determina a ordenação baseada no tipo de evento
    if df[event_col].iloc[0] == 6004:
        ascending_order = True  # Ordem crescente para evento 6004
    elif df[event_col].iloc[0] == 6504:
        ascending_order = False  # Ordem decrescente para evento 6504
    else:
        ascending_order = True  # Padrão
    
    # Calcula soma total por grupo para ordenação
    grupos_soma = df.groupby(group_col)[value_col].sum().reset_index()
    grupos_soma = grupos_soma.sort_values(by=value_col, ascending=ascending_order)
    grupos_ordenados = grupos_soma[group_col].tolist()
    
    box_data = {}
    
    for grupo in grupos_ordenados:
        grupo_df = df[df[group_col] == grupo]
        
        # Soma total do grupo
        soma_grupo = grupo_df[value_col].sum()
        soma_grupo_formatado = format_currency(soma_grupo)
        
        # Soma por subgrupo
        subgrupos = grupo_df.groupby(subgroup_col)[value_col].sum().reset_index()
        # Ordena por valor - mantém decrescente para subgrupos ou ajusta conforme necessário
        subgrupos = subgrupos.sort_values(by=value_col, ascending=False)
        subgrupos[value_col] = subgrupos[value_col].apply(format_currency)
        
        box_data[grupo] = {
            'soma_grupo': soma_grupo_formatado,
            'subgrupos': subgrupos.to_dict(orient='records')
        }
    
    return box_data

def get_date_range_info(df, date_col='DT.ULT.EV.'):
    """Obtém informações sobre o range de datas no DataFrame"""
    if date_col not in df.columns:
        return None, None
    
    df_copy = df.copy()
    df_copy[date_col] = pd.to_datetime(df_copy[date_col], errors='coerce')
    
    data_mais_antiga = df_copy[date_col].min().date() if not df_copy[date_col].isna().all() else None
    data_mais_recente = df_copy[date_col].max().date() if not df_copy[date_col].isna().all() else None
    
    return data_mais_antiga, data_mais_recente

def format_date_for_display(date_obj):
    """Formata data para exibição"""
    return date_obj.strftime('%d/%m/%Y') if date_obj else "N/A"

# =============== ROTAS ===============
#rota da página inicial
@controle_de_perdas.route('/')
@controle_de_perdas.route('/controle_de_perdas')
def index():
    global saeoi51
    df = saeoi51

    data_mais_antiga, data_mais_recente = get_date_range_info(df)
    
    data_mais_antiga_fmt = format_date_for_display(data_mais_antiga)
    data_mais_recente_fmt = format_date_for_display(data_mais_recente)

    return render_template(
        'controle_de_perdas.html',
        data_mais_antiga=data_mais_antiga_fmt,
        data_mais_recente=data_mais_recente_fmt
    )
#visualisar se  está atualisado.
@controle_de_perdas.route('/menu')
def menu():
    global saeoi51
    df = saeoi51

    data_mais_antiga, data_mais_recente = get_date_range_info(df)
    
    data_mais_antiga_fmt = format_date_for_display(data_mais_antiga)
    data_mais_recente_fmt = format_date_for_display(data_mais_recente)

    return render_template(
        'controle_de_perdas.html',
        data_mais_antiga=data_mais_antiga_fmt,
        data_mais_recente=data_mais_recente_fmt
    )

@controle_de_perdas.route('/ajustepreventiva')
def ajustepreventiva():
    global saeoi51
    df = saeoi51
    
    # Filtra os eventos 6004 e 6504
    evento_6004 = filter_by_evento(df, 6004)
    evento_6504 = filter_by_evento(df, 6504)
    
    # Processa os dados por grupo
    box_6004 = process_group_data(evento_6004)
    box_6504 = process_group_data(evento_6504)

    # Calcula os totais de cada box
    total_6004 = calculate_totals(evento_6004)[0]  # Pega apenas o VLR.TOTAL
    total_6504 = calculate_totals(evento_6504)[0]  # Pega apenas o VLR.TOTAL

    # Formata os totais
    total_6004_formatado = format_currency(total_6004)
    total_6504_formatado = format_currency(total_6504)
    
    # Prepara dados para o template ajustepreventiva.html
    # Combina dados dos eventos 6004 e 6504 para criar subgrupos
    combined_df = pd.concat([evento_6004, evento_6504], ignore_index=True)
    
    # Cria dados simulados para subgrupos
    subgrupos_data = []
    if validate_columns(combined_df, ['SUB-GRUPO', 'VLR.TOTAL']):
        subgrupos_unicos = combined_df['SUB-GRUPO'].unique()
        
        for i, subgrupo in enumerate(subgrupos_unicos[:10]):  # Limita a 10 subgrupos para exemplo
            subgrupo_df = combined_df[combined_df['SUB-GRUPO'] == subgrupo]
            valor_total = subgrupo_df['VLR.TOTAL'].sum()
            total_itens = len(subgrupo_df)
            
            # Simula dados para o template
            subgrupo_data = {
                'codigo': str(subgrupo),
                'nome': f'Subgrupo {subgrupo}',
                'status': ['pendente', 'processando', 'concluido'][i % 3],
                'status_text': ['Pendente', 'Processando', 'Concluído'][i % 3],
                'prioridade': ['alta', 'media', 'baixa'][i % 3],
                'prioridade_text': ['Alta', 'Média', 'Baixa'][i % 3],
                'valor_total': format_currency(valor_total),
                'total_itens': total_itens,
                'pendencias': max(0, total_itens - (i * 2)),
                'eficiencia': min(100, 60 + (i * 5)),
                'progresso': min(100, 20 + (i * 8)),
                'itens': [],  # Pode ser preenchido conforme necessário
                'historico': [],  # Pode ser preenchido conforme necessário
            }
            subgrupos_data.append(subgrupo_data)
    
    # Calcula estatísticas gerais
    total_subgrupos = len(subgrupos_data)
    ajustes_pendentes = sum(1 for s in subgrupos_data if s['status'] == 'pendente')
    ajustes_realizados = sum(1 for s in subgrupos_data if s['status'] == 'concluido')
    economia_gerada = format_currency(total_6004 + total_6504)
    
    # Lista de subgrupos disponíveis para filtros
    subgrupos_disponiveis = [{'codigo': s['codigo'], 'nome': s['nome']} for s in subgrupos_data]

    return render_template(
        'ajustepreventiva.html', 
        box_6004=box_6004, 
        box_6504=box_6504,
        total_6004=total_6004_formatado,
        total_6504=total_6504_formatado,
        subgrupos_data=subgrupos_data,
        total_subgrupos=total_subgrupos,
        ajustes_pendentes=ajustes_pendentes,
        ajustes_realizados=ajustes_realizados,
        economia_gerada=economia_gerada,
        subgrupos_disponiveis=subgrupos_disponiveis
    )

@controle_de_perdas.route('/ajustepreventiva_subgrupo/<subgrupo>')
def ajustepreventiva_subgrupo(subgrupo):
    global saeoi51
    df = saeoi51

    # Filtra apenas os eventos 6004 e 6504 primeiro
    df_eventos = df[df['EVENTO'].isin([6004, 6504])]
    
    # Decodifica o subgrupo da URL (caso tenha caracteres especiais)
    from urllib.parse import unquote
    import base64
    
    subgrupo_decoded = unquote(subgrupo)
    
    # Tenta decodificar base64 se necessário
    try:
        # Verifica se parece com base64 (termina com = ou ==)
        if subgrupo_decoded.endswith('=') or subgrupo_decoded.endswith('=='):
            subgrupo_decoded = base64.b64decode(subgrupo_decoded).decode('utf-8')
    except Exception:
        # Se falhar na decodificação base64, usa o valor original
        pass

    # Tenta busca exata primeiro
    subgrupo_df = df_eventos[df_eventos['SUB-GRUPO'] == subgrupo_decoded]
    
    # Se não encontrar, tenta busca case-insensitive
    if subgrupo_df.empty:
        subgrupo_df = df_eventos[df_eventos['SUB-GRUPO'].str.upper() == subgrupo_decoded.upper()]
        
    # Se ainda não encontrar, tenta busca parcial
    if subgrupo_df.empty:
        subgrupo_df = df_eventos[df_eventos['SUB-GRUPO'].str.contains(subgrupo_decoded, case=False, na=False)]
    
    # Prepara dados para exibição
    subgrupo_df = prepare_dataframe_for_display(subgrupo_df)
    
    # Formata valores com 2 casas decimais (sem símbolo de moeda)
    if not subgrupo_df.empty and 'VLR.TOTAL' in subgrupo_df.columns:
        subgrupo_df = format_dataframe_currency(subgrupo_df, 'VLR.TOTAL')

    table_html = dataframe_to_html_table(subgrupo_df)

    return render_template('ajustepreventiva_popup.html', table=table_html, subgrupo=subgrupo_decoded)

@controle_de_perdas.route('/perdaporgrupo')
def perdaporgrupo():
    global saeoi51
    df = saeoi51

    if validate_columns(df, ['GRUPO', 'SUB-GRUPO', 'VLR.TOTAL']):
        # Cria uma cópia do DataFrame e limpa os dados
        df = df.copy()
        df['SUB-GRUPO'] = df['SUB-GRUPO'].str.replace('/', '-', regex=False)
        
        # Certifica que VLR.TOTAL é numérico
        df['VLR.TOTAL'] = pd.to_numeric(df['VLR.TOTAL'], errors='coerce')
        
        # Calcula totais por grupo
        grupos_totais = df.groupby('GRUPO')['VLR.TOTAL'].sum().sort_values(ascending=False)
        
        box_data = {}
        total_geral = 0
        
        for grupo in grupos_totais.index:
            grupo_df = df[df['GRUPO'] == grupo]
            grupo_total = grupos_totais[grupo]
            total_geral += grupo_total
            
            # Calcula totais por subgrupo dentro do grupo
            subgrupos = (grupo_df.groupby('SUB-GRUPO')
                        .agg({
                            'VLR.TOTAL': 'sum',
                            'GRUPO': 'count'  # conta registros para quantidade
                        })
                        .reset_index()
                        .sort_values('VLR.TOTAL', ascending=False))
            
            # Verifica se os totais dos subgrupos batem com o total do grupo
            subgrupos_total = subgrupos['VLR.TOTAL'].sum()
            if not np.isclose(subgrupos_total, grupo_total, rtol=1e-10):
                print(f"Aviso: Diferença encontrada no grupo {grupo}")
                print(f"Total do grupo: {grupo_total}")
                print(f"Soma dos subgrupos: {subgrupos_total}")
            
            # Prepara dados dos subgrupos
            subgrupos_lista = []
            for _, row in subgrupos.iterrows():
                subgrupo_data = {
                    'nome': row['SUB-GRUPO'],
                    'valor': format_currency(row['VLR.TOTAL']),
                    'valor_raw': float(row['VLR.TOTAL']),  # mantém o valor original
                    'quantidade': row['GRUPO']
                }
                subgrupos_lista.append(subgrupo_data)
            
            box_data[grupo] = {
                'soma': format_currency(grupo_total),
                'soma_raw': float(grupo_total),  # mantém o valor original
                'quantidade_total': len(grupo_df),
                'subgrupos': subgrupos_lista
            }

        # Verifica se o total geral está correto
        soma_todos_grupos = sum(float(dados['soma_raw']) for dados in box_data.values())
        if not np.isclose(soma_todos_grupos, total_geral, rtol=1e-10):
            print("Aviso: Total geral não corresponde à soma dos grupos")
            print(f"Total geral: {total_geral}")
            print(f"Soma dos grupos: {soma_todos_grupos}")

    else:
        box_data = {"Nenhum Grupo Encontrado": {
            "soma": format_currency(0),
            "soma_raw": 0,
            "quantidade_total": 0,
            "subgrupos": []
        }}
        total_geral = 0

    return render_template(
        'perdaporgrupo.html',
        box_data=box_data,
        total_geral=format_currency(total_geral)
    )

@controle_de_perdas.route('/controle-perdas/subgrupo/<subgrupo>')
@controle_de_perdas.route('/controle_de_perdas/subgrupo/<subgrupo>')
@controle_de_perdas.route('/subgrupo/<subgrupo>')
def subgrupo_items(subgrupo):
    global saeoi51
    df = saeoi51

    # Decodifica o subgrupo da URL
    from urllib.parse import unquote
    subgrupo_decoded = unquote(subgrupo)
    
    # Substitui - por / no subgrupo para corresponder aos dados
    subgrupo_decoded = subgrupo_decoded.replace('-', '/')

    if validate_columns(df, ['SUB-GRUPO', 'VLR.TOTAL']):
        # Filtra por subgrupo
        subgrupo_df = df[df['SUB-GRUPO'] == subgrupo_decoded].copy()
        
        # Debug logs
        print(f"Procurando subgrupo: {subgrupo_decoded}")
        print(f"Subgrupos disponíveis: {df['SUB-GRUPO'].unique()}")
        print(f"Registros encontrados: {len(subgrupo_df)}")
        
        if subgrupo_df.empty:
            return render_template(
                'subgrupo_popup.html',
                table="<p>Nenhum dado encontrado para o subgrupo: " + subgrupo_decoded + "</p>",
                subgrupo=subgrupo_decoded,
                total_subgrupo=format_currency(0),
                quantidade_items=0
            )
        
        # Calcula o total do subgrupo
        total_subgrupo = subgrupo_df['VLR.TOTAL'].sum()
        
        # Seleciona e ordena as colunas para exibição
        colunas_exibicao = ['MERCADORIA', 'DESCRICAO', 'VLR.TOTAL', 'EMB1']
        subgrupo_df = subgrupo_df[colunas_exibicao].sort_values('VLR.TOTAL', ascending=False)
        
        # Formata valores monetários
        subgrupo_df['VLR.TOTAL'] = subgrupo_df['VLR.TOTAL'].apply(format_currency)
        
        # Converte DataFrame para HTML
        table_html = dataframe_to_html_table(subgrupo_df)
        
        return render_template(
            'subgrupo_popup.html',
            table=table_html,
            subgrupo=subgrupo_decoded,
            total_subgrupo=format_currency(total_subgrupo),
            quantidade_items=len(subgrupo_df)
        )
    else:
        return render_template(
            'subgrupo_popup.html',
            table="<p>Erro: Colunas necessárias não encontradas no DataFrame</p>",
            subgrupo=subgrupo_decoded,
            total_subgrupo=format_currency(0),
            quantidade_items=0
        )

@controle_de_perdas.route('/negativo')
def negativo():
    global saeoi51
    df = saeoi51

    # Box 1: Evento 6001
    box1_df = df[df['EVENTO'] == 6521]
    
    # Box 2: Evento 6501 
    box2_df = df[df['EVENTO'] == 6021]

    # Seleciona colunas para ambas as boxes
    colunas = ['MERCADORIA', 'DESCRICAO', 'VLR.TOTAL', 'EMB1']
    box1_df = box1_df[colunas].copy()
    box2_df = box2_df[colunas].copy()

    # Ordena por valor total
    box1_df = box1_df.sort_values('VLR.TOTAL', ascending=True)
    box2_df = box2_df.sort_values('VLR.TOTAL', ascending=True)

    # Calcula totais antes da formatação
    box1_vlr_total = box1_df['VLR.TOTAL'].sum()
    box1_emb1_total = box1_df['EMB1'].sum()
    
    box2_vlr_total = box2_df['VLR.TOTAL'].sum()
    box2_emb1_total = box2_df['EMB1'].sum()

    # Formata valores monetários nos DataFrames
    box1_df['VLR.TOTAL'] = box1_df['VLR.TOTAL'].apply(format_currency)
    box2_df['VLR.TOTAL'] = box2_df['VLR.TOTAL'].apply(format_currency)

    # Formata totais
    box1_vlr_total_fmt = format_currency(box1_vlr_total)
    box2_vlr_total_fmt = format_currency(box2_vlr_total)
    total_geral = format_currency(box1_vlr_total + box2_vlr_total)

    # Converte para HTML
    box1_html = box1_df.to_html(classes='table table-striped', index=False)
    box2_html = box2_df.to_html(classes='table table-striped', index=False)

    return render_template(
        'negativo.html',
        box1_html=box1_html,
        box2_html=box2_html,
        box1_vlr_total=box1_vlr_total_fmt,
        box2_vlr_total=box2_vlr_total_fmt,
        box1_emb1_total=box1_emb1_total,
        box2_emb1_total=box2_emb1_total,
        total_geral=total_geral
    )

@controle_de_perdas.route("/perda_hf")
def perda_hf():
    global saeoi51
    df = saeoi51
    
    # Filtra itens que começam com "HF"
    df_filtrado = filter_by_description_prefix(df, ['HF'])
    
    if df_filtrado.empty:
        return render_template('perda_hf.html',
                             filtro1_html="<p>Nenhum dado disponível</p>",
                             filtro2_html="<p>Nenhum dado disponível</p>",
                             filtro1_vlr_total=format_currency(0),
                             filtro2_vlr_total=format_currency(0),
                             filtro1_emb1_total=0,
                             filtro2_emb1_total=0,
                             total_perdas=format_currency(0))

    # Filtro 1: OPERACAO = "AVARIAS / HORTIFRUT"
    filtro1_df = filter_by_operacao(df_filtrado, "AVARIAS / HORTIFRUT")
    
    # Filtro 2: OPERACAO != "AVARIAS / HORTIFRUT" e EVENTO != 6521
    filtro2_df = df_filtrado[
        (df_filtrado['OPERACAO'] != "AVARIAS / HORTIFRUT") & 
        (df_filtrado['EVENTO'] != 6521)
    ] if validate_columns(df_filtrado, ['OPERACAO', 'EVENTO']) else pd.DataFrame()

    # Prepara dados para exibição
    filtro1_df = prepare_dataframe_for_display(filtro1_df)
    filtro2_df = prepare_dataframe_for_display(filtro2_df)

    # Calcula totais
    filtro1_vlr_total, filtro1_emb1_total = calculate_totals(filtro1_df)
    filtro2_vlr_total, filtro2_emb1_total = calculate_totals(filtro2_df)
    
    # Formata valores
    filtro1_vlr_total_fmt = format_currency(filtro1_vlr_total)
    filtro2_vlr_total_fmt = format_currency(filtro2_vlr_total)
    total_perdas_fmt = format_currency(filtro1_vlr_total + filtro2_vlr_total)

    # Aplica formatação nos DataFrames
    filtro1_df = format_dataframe_currency(filtro1_df)
    filtro2_df = format_dataframe_currency(filtro2_df)

    # Converte para HTML
    filtro1_html = dataframe_to_html_table(filtro1_df)
    filtro2_html = dataframe_to_html_table(filtro2_df)

    return render_template(
        'perda_hf.html',
        filtro1_html=filtro1_html,
        filtro2_html=filtro2_html,
        filtro1_vlr_total=filtro1_vlr_total_fmt,
        filtro2_vlr_total=filtro2_vlr_total_fmt,
        filtro1_emb1_total=filtro1_emb1_total,
        filtro2_emb1_total=filtro2_emb1_total,
        total_perdas=total_perdas_fmt
    )

@controle_de_perdas.route('/totalperdas')
def totalperdas():
    global saeoi51
    df = saeoi51
    
    # Converte a coluna "EVENTO" para o tipo int
    if 'EVENTO' in df.columns:
        df['EVENTO'] = pd.to_numeric(df['EVENTO'], errors='coerce').fillna(0).astype(int)
    
    # Converte a coluna de data para o formato datetime"
    if 'DT.ULT.EV.' in df.columns:
        df['DT.ULT.EV.'] = pd.to_datetime(df['DT.ULT.EV.'], errors='coerce')

    # Filtra os dados para cada box e ordena por "VLR.TOTAL" (do menor para o maior)
    # Box 1: Evento 1500 E operação contendo "MERCADORIAS AVARIADAS"
    box1_df = df[
        (df['EVENTO'] == 1500) & 
        (df['OPERACAO'].str.contains('MERCADORIAS  AVARIADAS|MERCADORIAS AVARIADAS POR VENCIMENTO|AVARIAS POR DEGUSTACAO|AVARIAS / HORTIFRUT', na=False))
    ][['EVENTO', 'MERCADORIA', 'DESCRICAO', 'VLR.TOTAL', 'EMB1']].sort_values(by='VLR.TOTAL', ascending=True)
    
    box2_df = df[df['EVENTO'].isin([6004, 6001, 6504, 6021, 8000, 6501])][['EVENTO', 'MERCADORIA', 'DESCRICAO', 'VLR.TOTAL', 'EMB1']].sort_values(by='VLR.TOTAL', ascending=True)
    
    # Box 3: Evento 1500 E operação contendo "MERCADORIAS AVARIADAS" E data atual
    data_atual = datetime.now().date()
    box3_df = df[
        (df['EVENTO'] == 1500) & 
         (df['OPERACAO'].str.contains('MERCADORIAS  AVARIADAS|MERCADORIAS AVARIADAS POR VENCIMENTO|AVARIAS POR DEGUSTACAO|AVARIAS / HORTIFRUT', na=False)) & 
        (df['DT.ULT.EV.'].dt.date == data_atual)
    ][['EVENTO', 'MERCADORIA', 'DESCRICAO', 'VLR.TOTAL', 'EMB1']].sort_values(by='VLR.TOTAL', ascending=True)

    box4_df = df[(df['EVENTO'].isin([6004, 6001, 6504, 6021, 8000,6501])) & (df['DT.ULT.EV.'].dt.date == data_atual)][['EVENTO', 'MERCADORIA', 'DESCRICAO', 'VLR.TOTAL', 'EMB1']].sort_values(by='VLR.TOTAL', ascending=True)

    # Arredonda os valores da coluna "VLR.TOTAL" para duas casas decimais
    box1_df['VLR.TOTAL'] = box1_df['VLR.TOTAL'].round(2)
    box2_df['VLR.TOTAL'] = box2_df['VLR.TOTAL'].round(2)
    box3_df['VLR.TOTAL'] = box3_df['VLR.TOTAL'].round(2)
    box4_df['VLR.TOTAL'] = box4_df['VLR.TOTAL'].round(2)

    # Calcula as somas
    box1_vlr_total = box1_df['VLR.TOTAL'].sum()
    box1_emb1_total = box1_df['EMB1'].sum()

    box2_vlr_total = box2_df['VLR.TOTAL'].sum()
    box2_emb1_total = box2_df['EMB1'].sum()

    box3_vlr_total = box3_df['VLR.TOTAL'].sum()
    box3_emb1_total = box3_df['EMB1'].sum()

    box4_vlr_total = box4_df['VLR.TOTAL'].sum()
    box4_emb1_total = box4_df['EMB1'].sum()

    # Primeiro, calcula os valores originais (sem formatação)
    box1_vlr_total_raw = box1_df['VLR.TOTAL'].sum() if 'VLR.TOTAL' in box1_df.columns else 0
    box2_vlr_total_raw = box2_df['VLR.TOTAL'].sum() if 'VLR.TOTAL' in box2_df.columns else 0
    box3_vlr_total_raw = box3_df['VLR.TOTAL'].sum() if 'VLR.TOTAL' in box3_df.columns else 0
    box4_vlr_total_raw = box4_df['VLR.TOTAL'].sum() if 'VLR.TOTAL' in box4_df.columns else 0

    # Calcula os totais para o box central
    central_vlr_total = box3_vlr_total + box4_vlr_total
    central_emb1_total = box3_emb1_total + box4_emb1_total

    perda_total = box1_vlr_total_raw + box2_vlr_total_raw
    perda_total = format_currency(perda_total)
    perda_total2 = box3_vlr_total_raw + box4_vlr_total_raw
    perda_total2 = format_currency(perda_total2)

   
    # Formata os valores totais
    box1_vlr_total = format_currency(box1_vlr_total_raw)
    box2_vlr_total = format_currency(box2_vlr_total_raw)
    box3_vlr_total = format_currency(box3_vlr_total_raw)
    box4_vlr_total = format_currency(box4_vlr_total_raw)

    # Formata VLR.TOTAL em todos os DataFrames
    for df in [box1_df, box2_df, box3_df, box4_df]:
        if not df.empty and 'VLR.TOTAL' in df.columns:
            df['VLR.TOTAL'] = df['VLR.TOTAL'].apply(format_currency)

    # Converte os dados para exibição
    box1 = box1_df.head(50).to_dict(orient='records')
    box2 = box2_df.head(50).to_dict(orient='records')
    box3 = box3_df.head(50).to_dict(orient='records')
    box4 = box4_df.head(50).to_dict(orient='records')

    return render_template(
        'totalperdas.html',
        box1=box1,
        box1_vlr_total=box1_vlr_total,
        box1_emb1_total=box1_emb1_total,
        box2=box2,
        box2_vlr_total=box2_vlr_total,
        box2_emb1_total=box2_emb1_total,
        box3=box3,
        box3_vlr_total=box3_vlr_total,
        box3_emb1_total=box3_emb1_total,
        box4=box4,
        box4_vlr_total=box4_vlr_total,
        box4_emb1_total=box4_emb1_total,
        central_vlr_total=central_vlr_total,
        central_emb1_total=central_emb1_total,
        perda_total=perda_total,
        perda_total2=perda_total2
    )

@controle_de_perdas.route('/perda_vencimento')
def perda_vencimento():
    try:
        global saeoi51
        df = saeoi51

        # Filtra as linhas onde a coluna "OPERACAO" contém o texto desejado
        if 'OPERACAO' in df.columns:
            df_filtrado = df[df['OPERACAO'] == "MERCADORIAS AVARIADAS POR VENCIMENTO"]
        else:
            df_filtrado = pd.DataFrame()  # DataFrame vazio caso a coluna não exista

        # Remove os itens onde "DESCRICAO" começa com "HF" ou "RF"
        if 'DESCRICAO' in df_filtrado.columns:
            df_filtrado = df_filtrado[~df_filtrado['DESCRICAO'].str.startswith(('HF', 'RF'), na=False)]

        # Remove as colunas indesejadas
        colunas_selecionadas = ['MERCADORIA', 'DESCRICAO', 'VLR.TOTAL', 'EMB1']
        df_filtrado = df_filtrado[colunas_selecionadas].sort_values(by='VLR.TOTAL', ascending=True)

        # Calcula o valor total de perdas por vencimento ANTES da formatação
        total_perdas = df_filtrado['VLR.TOTAL'].sum() if 'VLR.TOTAL' in df_filtrado.columns else 0
        total_perdas_formatado = format_currency(total_perdas)

        # Calcula o total de EMB1
        total_emb1 = df_filtrado['EMB1'].sum() if 'EMB1' in df_filtrado.columns else 0

        # Aplica formatação de moeda na coluna VLR.TOTAL do DataFrame
        if 'VLR.TOTAL' in df_filtrado.columns and not df_filtrado.empty:
            df_filtrado = df_filtrado.copy()
            df_filtrado['VLR.TOTAL'] = df_filtrado['VLR.TOTAL'].apply(format_currency)

        # Converte o DataFrame filtrado para HTML
        if not df_filtrado.empty:
            table_html = df_filtrado.to_html(classes='table table-striped', index=False)
        else:
            table_html = "<p class='text-center text-muted'>Nenhum dado disponível para exibição.</p>"

        return render_template(
            'perda_vencimento.html',
            vencimento_data=df_filtrado.to_dict('records') if not df_filtrado.empty else [],
            vencimento_vlr_total=total_perdas_formatado,
            vencimento_emb1_total=total_emb1,
            table=table_html,
            total_perdas=total_perdas_formatado,
            total_emb1=total_emb1
        )
    except Exception as e:
        print(f"Error in perda_vencimento: {e}")
        return render_template(
            'perda_vencimento.html',
            vencimento_data=[],
            vencimento_vlr_total="R$ 0,00",
            vencimento_emb1_total=0,
            table="<p class='text-center text-muted'>Erro ao carregar dados.</p>",
            total_perdas="R$ 0,00",
            total_emb1=0
        )

@controle_de_perdas.route('/perdafrios')
def perdafrios():
    global saeoi51
    df = saeoi51
    
    # Filtra os itens onde "DESCRICAO" começa com "RF"
    if 'DESCRICAO' in df.columns:
        df_filtrado = df[df['DESCRICAO'].str.startswith('RF', na=False)]
    else:
        df_filtrado = pd.DataFrame()

    # Box da esquerda: EVENTO em [6004, 6001, 6504, 6021, 8000]
    eventos_esquerda = [6004, 6001, 6504, 6021, 8000]
    box_esquerda_df = df_filtrado[df_filtrado['EVENTO'].isin(eventos_esquerda)]

    # Box da direita: EVENTO = 1500
    box_direita_df = df_filtrado[(df_filtrado['EVENTO'] == 1500) & 
                            (df_filtrado['OPERACAO'].str.contains('MERCADORIAS  AVARIADAS|MERCADORIAS AVARIADAS POR VENCIMENTO|AVARIAS POR DEGUSTACAO|AVARIAS / HORTIFRUT', na=False))]
    

    # Novo box: Perdas por Vencimento (Frios)
    if 'OPERACAO' in df.columns:
        box_vencimento_df = df[
            (df['OPERACAO'] == "MERCADORIAS AVARIADAS POR VENCIMENTO") &
            (df['DESCRICAO'].str.startswith('RF', na=False))
        ]
    else:
        box_vencimento_df = pd.DataFrame()

    # Seleciona as colunas relevantes para exibição
    colunas_para_exibir = ['MERCADORIA', 'DESCRICAO', 'VLR.TOTAL', 'EMB1']
    box_esquerda_df = box_esquerda_df[colunas_para_exibir].sort_values(by='VLR.TOTAL', ascending=True)
    box_direita_df = box_direita_df[colunas_para_exibir].sort_values(by='VLR.TOTAL', ascending=True)
    box_vencimento_df = box_vencimento_df[colunas_para_exibir].sort_values(by='VLR.TOTAL', ascending=True)

    # Calcula os totais ANTES da formatação
    total_esquerda = box_esquerda_df['VLR.TOTAL'].sum() if 'VLR.TOTAL' in box_esquerda_df.columns else 0
    emb1_esquerda = box_esquerda_df['EMB1'].sum() if 'EMB1' in box_esquerda_df.columns else 0

    total_direita = box_direita_df['VLR.TOTAL'].sum() if 'VLR.TOTAL' in box_direita_df.columns else 0
    emb1_direita = box_direita_df['EMB1'].sum() if 'EMB1' in box_direita_df.columns else 0

    total_vencimento = box_vencimento_df['VLR.TOTAL'].sum() if 'VLR.TOTAL' in box_vencimento_df.columns else 0
    emb1_vencimento = box_vencimento_df['EMB1'].sum() if 'EMB1' in box_vencimento_df.columns else 0

    # Formata os totais
    total_esquerda_formatado = format_currency(total_esquerda)
    total_direita_formatado = format_currency(total_direita)
    total_vencimento_formatado = format_currency(total_vencimento)

    # Calcula o total geral
    total_geral = total_esquerda + total_direita + total_vencimento
    total_geral_formatado = format_currency(total_geral)

    # Aplica formatação de moeda nos DataFrames
    for df_box in [box_esquerda_df, box_direita_df, box_vencimento_df]:
        if 'VLR.TOTAL' in df_box.columns and not df_box.empty:
            df_box['VLR.TOTAL'] = df_box['VLR.TOTAL'].apply(format_currency)

    # Converte os DataFrames para HTML
    box_esquerda_html = dataframe_to_html_table(box_esquerda_df)
    box_direita_html = dataframe_to_html_table(box_direita_df)
    box_vencimento_html = dataframe_to_html_table(box_vencimento_df)

    # Calcular totais gerais para os cards de resumo
    rf_vlr_total = total_geral_formatado
    rf_emb1_total = emb1_esquerda + emb1_direita + emb1_vencimento
    eventos_count = len(df_filtrado['EVENTO'].unique()) if not df_filtrado.empty else 0
    avariadas_vlr_total = total_direita_formatado  # Box 2 é mercadorias avariadas
    
    return render_template('perdafrios.html',
                         # Dados dos DataFrames para iteração no template
                         box1=box_direita_df.to_dict('records') if not box_direita_df.empty else [],
                         box2=box_esquerda_df.to_dict('records') if not box_esquerda_df.empty else [],
                         box3=box_vencimento_df.to_dict('records') if not box_vencimento_df.empty else [],
                         # Tabelas HTML
                         box1_html=box_direita_html,
                         box2_html=box_esquerda_html,
                         box3_html=box_vencimento_html,
                         # Valores totais dos boxes
                         box1_vlr_total=total_direita_formatado,
                         box2_vlr_total=total_esquerda_formatado,
                         box3_vlr_total=total_vencimento_formatado,
                         # EMB1 totais dos boxes
                         box1_emb1_total=emb1_direita,
                         box2_emb1_total=emb1_esquerda,
                         box3_emb1_total=emb1_vencimento,
                         # Totais gerais para os cards de resumo
                         rf_vlr_total=rf_vlr_total,
                         rf_emb1_total=rf_emb1_total,
                         eventos_count=eventos_count,
                         avariadas_vlr_total=avariadas_vlr_total)
