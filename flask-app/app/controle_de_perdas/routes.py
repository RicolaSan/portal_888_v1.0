from flask import render_template, jsonify
import pandas as pd
import openpyxl
import locale
from datetime import datetime
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

def process_group_data(df, group_col='GRUPO', subgroup_col='SUB-GRUPO', value_col='VLR.TOTAL'):
    """Processa dados agrupados por grupo e subgrupo"""
    if not validate_columns(df, [group_col, subgroup_col, value_col]):
        return {}
    
    grupos = df[group_col].unique()
    box_data = {}
    
    for grupo in grupos:
        grupo_df = df[df[group_col] == grupo]
        
        # Soma total do grupo
        soma_grupo = grupo_df[value_col].sum()
        soma_grupo_formatado = format_currency(soma_grupo)
        
        # Soma por subgrupo
        subgrupos = grupo_df.groupby(subgroup_col)[value_col].sum().reset_index()
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

@controle_de_perdas.route('/')
@controle_de_perdas.route('/controle_de_perdas')
def index():
    global saeoi51
    df = saeoi51

    data_mais_antiga, data_mais_recente = get_date_range_info(df)
    
    data_mais_antiga_fmt = format_date_for_display(data_mais_antiga)
    data_mais_recente_fmt = format_date_for_display(data_mais_recente)

    return render_template(
        'menu.html',
        data_mais_antiga=data_mais_antiga_fmt,
        data_mais_recente=data_mais_recente_fmt
    )

@controle_de_perdas.route('/menu')
def menu():
    global saeoi51
    df = saeoi51

    data_mais_antiga, data_mais_recente = get_date_range_info(df)
    
    data_mais_antiga_fmt = format_date_for_display(data_mais_antiga)
    data_mais_recente_fmt = format_date_for_display(data_mais_recente)

    return render_template(
        'menu.html',
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

    return render_template(
        'ajustepreventiva.html', 
        box_6004=box_6004, 
        box_6504=box_6504,
        total_6004=total_6004_formatado,
        total_6504=total_6504_formatado
    )

@controle_de_perdas.route('/ajustepreventiva/subgrupo/<subgrupo>')
def ajustepreventiva_subgrupo(subgrupo):
    global saeoi51
    df = saeoi51

    # Filtra os itens do subgrupo
    if validate_columns(df, ['SUB-GRUPO']):
        subgrupo_df = df[df['SUB-GRUPO'] == subgrupo]
    else:
        subgrupo_df = pd.DataFrame()

    # Prepara dados para exibição
    subgrupo_df = prepare_dataframe_for_display(subgrupo_df)
    
    # Formata valores com 2 casas decimais (sem símbolo de moeda)
    if 'VLR.TOTAL' in subgrupo_df.columns:
        subgrupo_df['VLR.TOTAL'] = subgrupo_df['VLR.TOTAL'].apply(lambda x: f"{x:.2f}")

    table_html = dataframe_to_html_table(subgrupo_df)

    return render_template('ajustepreventiva_popup.html', table=table_html, subgrupo=subgrupo)

@controle_de_perdas.route('/perdaporgrupo')
def perdaporgrupo():
    global saeoi51
    df = saeoi51

    if validate_columns(df, ['GRUPO', 'SUB-GRUPO']):
        # Substitui "/" por "|" na coluna SUB-GRUPO
        df = df.copy()
        df['SUB-GRUPO'] = df['SUB-GRUPO'].str.replace('/', '|', regex=False)
        
        box_data = process_group_data(df, value_col='VLR.TOTAL')
        
        # Ajusta o nome da chave para compatibilidade com template
        for grupo in box_data:
            box_data[grupo]['soma'] = box_data[grupo]['soma_grupo']
    else:
        box_data = {"Nenhum Grupo Encontrado": {"soma": format_currency(0), "subgrupos": []}}

    return render_template('perdaporgrupo.html', box_data=box_data)

@controle_de_perdas.route('/subgrupo/<subgrupo>')
def subgrupo_items(subgrupo):
    global saeoi51
    df = saeoi51

    # Filtra por subgrupo
    if validate_columns(df, ['SUB-GRUPO']):
        subgrupo_df = df[df['SUB-GRUPO'] == subgrupo]
    else:
        subgrupo_df = pd.DataFrame()

    # Prepara para exibição
    subgrupo_df = prepare_dataframe_for_display(subgrupo_df)
    
    # Formata valores com 2 casas decimais
    if 'VLR.TOTAL' in subgrupo_df.columns:
        subgrupo_df['VLR.TOTAL'] = subgrupo_df['VLR.TOTAL'].apply(lambda x: f"{x:.2f}")

    table_html = dataframe_to_html_table(subgrupo_df)

    return render_template('subgrupo_popup.html', table=table_html, subgrupo=subgrupo)

@controle_de_perdas.route('/negativo')
def negativo():
    global saeoi51
    df = saeoi51

    # Filtra por evento 6521
    df_filtrado = filter_by_evento(df, 6521)
    
    # Prepara para exibição
    df_filtrado = prepare_dataframe_for_display(df_filtrado, ascending=False)
    
    # Calcula totais ANTES da formatação
    total_perdas, total_emb1 = calculate_totals(df_filtrado)
    total_perdas_formatado = format_currency(total_perdas)

    # Aplica formatação de moeda na coluna VLR.TOTAL do DataFrame
    if 'VLR.TOTAL' in df_filtrado.columns and not df_filtrado.empty:
        df_filtrado = df_filtrado.copy()
        df_filtrado['VLR.TOTAL'] = df_filtrado['VLR.TOTAL'].apply(format_currency)

    table_html = dataframe_to_html_table(df_filtrado)

    return render_template(
        'negativo.html',
        table=table_html,
        total_perdas=total_perdas_formatado,
        total_emb1=total_emb1
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
    
    # Converte a coluna de data para o formato datetime
    if 'DT.ULT.EV.' in df.columns:
        df['DT.ULT.EV.'] = pd.to_datetime(df['DT.ULT.EV.'], errors='coerce')

    # Filtra os dados para cada box e ordena por "VLR.TOTAL" (do menor para o maior)
    box1_df = df[df['EVENTO'] == 1500][['EVENTO', 'MERCADORIA', 'DESCRICAO', 'VLR.TOTAL', 'EMB1']].sort_values(by='VLR.TOTAL', ascending=True)
    box2_df = df[df['EVENTO'].isin([6004, 6001, 6504, 6021, 8000, 6501])][['EVENTO', 'MERCADORIA', 'DESCRICAO', 'VLR.TOTAL', 'EMB1']].sort_values(by='VLR.TOTAL', ascending=True)
    
    # Filtra os dados para o Box 3 (data atual) e ordena
    data_atual = datetime.now().date()
    box3_df = df[(df['EVENTO'] == 1500) & (df['DT.ULT.EV.'].dt.date == data_atual)][['EVENTO', 'MERCADORIA', 'DESCRICAO', 'VLR.TOTAL', 'EMB1']].sort_values(by='VLR.TOTAL', ascending=True)

    # Filtra os dados para o Box 4 (data atual e eventos específicos) e ordena
    box4_df = df[(df['EVENTO'].isin([6004, 6001, 6504, 6021, 8000, 6501])) & (df['DT.ULT.EV.'].dt.date == data_atual)][['EVENTO', 'MERCADORIA', 'DESCRICAO', 'VLR.TOTAL', 'EMB1']].sort_values(by='VLR.TOTAL', ascending=True)

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

    # Calcula os totais para o box central
    central_vlr_total = box3_vlr_total + box4_vlr_total
    central_emb1_total = box3_emb1_total + box4_emb1_total

    perda_total = box1_vlr_total + box2_vlr_total
    perda_total2 = box3_vlr_total + box4_vlr_total

    # Primeiro, calcula os valores originais (sem formatação)
    box1_vlr_total_raw = box1_df['VLR.TOTAL'].sum() if 'VLR.TOTAL' in box1_df.columns else 0
    box2_vlr_total_raw = box2_df['VLR.TOTAL'].sum() if 'VLR.TOTAL' in box2_df.columns else 0
    box3_vlr_total_raw = box3_df['VLR.TOTAL'].sum() if 'VLR.TOTAL' in box3_df.columns else 0
    box4_vlr_total_raw = box4_df['VLR.TOTAL'].sum() if 'VLR.TOTAL' in box4_df.columns else 0

    # Calcula a soma dos itens com evento 6501 para subtração
    evento_6501_df = df[df['EVENTO'] == 6501]
    evento_6501_total = evento_6501_df['VLR.TOTAL'].sum() if 'VLR.TOTAL' in evento_6501_df.columns and not evento_6501_df.empty else 0
    
    # Calcula a soma dos itens com evento 6501 na data atual para subtração
    evento_6501_hoje_df = df[(df['EVENTO'] == 6501) & (df['DT.ULT.EV.'].dt.date == data_atual)]
    evento_6501_hoje_total = evento_6501_hoje_df['VLR.TOTAL'].sum() if 'VLR.TOTAL' in evento_6501_hoje_df.columns and not evento_6501_hoje_df.empty else 0

    # Formata os valores totais
    box1_vlr_total = format_currency(box1_vlr_total_raw)
    box2_vlr_total = format_currency(box2_vlr_total_raw)
    box3_vlr_total = format_currency(box3_vlr_total_raw)
    box4_vlr_total = format_currency(box4_vlr_total_raw)

    # Calcula e formata as perdas totais SUBTRAINDO o evento 6501
    perda_total = format_currency((box1_vlr_total_raw + box2_vlr_total_raw) - evento_6501_total)
    perda_total2 = format_currency((box3_vlr_total_raw + box4_vlr_total_raw) - evento_6501_hoje_total)
    
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

    # Box da esquerda: EVENTO em [6004, 6001, 6504, 6021, 6501, 8000]
    eventos_esquerda = [6004, 6001, 6504, 6021, 6501, 8000]
    box_esquerda_df = df_filtrado[df_filtrado['EVENTO'].isin(eventos_esquerda)]

    # Box da direita: EVENTO = 1500
    box_direita_df = df_filtrado[df_filtrado['EVENTO'] == 1500]

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

    return render_template(
        'perdafrios.html',
        box_esquerda_html=box_esquerda_html,
        box_direita_html=box_direita_html,
        box_vencimento_html=box_vencimento_html,
        total_esquerda=total_esquerda_formatado,
        emb1_esquerda=emb1_esquerda,
        total_direita=total_direita_formatado,
        emb1_direita=emb1_direita,
        total_vencimento=total_vencimento_formatado,
        emb1_vencimento=emb1_vencimento,
        total_geral=total_geral_formatado
    )
