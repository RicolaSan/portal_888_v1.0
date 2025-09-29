from flask import render_template, request, send_file, make_response, flash, redirect, url_for
from . import controle_vencimento
import pandas as pd
import openpyxl
from math import ceil
from datetime import datetime, timedelta
import os
import io
from io import StringIO, BytesIO


# Carregar os dados uma vez na inicialização
try:
    # Tentar carregar dados da rede primeiro
    fornecedor_df = pd.read_csv("//10.122.244.3/publico/ControleVencimento/Forn.csv", sep=";", encoding="latin1")
    vencimento_df = pd.read_excel("//10.122.244.3/publico/ControleVencimento/SAEOU060.xlsx")
except Exception as e:
    # Se falhar, usar dados de teste locais
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    test_data_dir = os.path.join(base_dir, 'test_data')
    
    fornecedor_df = pd.read_csv(os.path.join(test_data_dir, "Forn.csv"), sep=";", encoding="latin1")
    vencimento_df = pd.read_excel(os.path.join(test_data_dir, "SAEOU060.xlsx"))

def formatar_dados(df):
    # Garantir que a coluna CODIGO seja string e remova o ".0"
    df["CODIGO"] = df["CODIGO"].astype(str).str.replace(r"\.0$", "", regex=True)

    # Converter as colunas ESTOQ.EMB1 e ESTOQ.EMB9 para inteiros
    df["ESTOQ.EMB1"] = pd.to_numeric(df["ESTOQ.EMB1"], errors="coerce").fillna(0).astype(int)
    df["ESTOQ.EMB9"] = pd.to_numeric(df["ESTOQ.EMB9"], errors="coerce").fillna(0).astype(int)

    # Formatar a coluna VALOR A VENCER como moeda em reais
    df["VALOR A VENCER"] = df["VALOR A VENCER"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    return df



@controle_vencimento.route("/", methods=["GET", "POST"])
def home():
    global fornecedor_df, vencimento_df



    # Renomear colunas
    fornecedor_df_renomeado = fornecedor_df.rename(columns={"Item Produto": "CODIGO",
                                                           "Fornecedor Atual": "CPF/CNPJ",
                                                           "FORNECEDOR": "FORNECEDOR"})
    fornecedor_final_df = fornecedor_df_renomeado[["CODIGO", "CPF/CNPJ", "FORNECEDOR"]].dropna(subset=["FORNECEDOR"])

    vencimento_df_renomeado = vencimento_df.rename(columns={
        "CÓDIGO": "CODIGO",
        "DESCRIÇÃO MERCADORIA": "DESCRICAO",
        "COMPLEMENTO": "COMPLEMENTO",
        "EMBALAGEM": "EMBALAGEM",
        "DATA VENCIMENTO": "VENCIMENTO",
        "EST. LÍQ. EMB1": "ESTOQ.EMB1",
        "EST. LÍQ. EMB9": "ESTOQ.EMB9",
        "VALOR VENCIMENTO": "VALOR A VENCER"
    })

    # Merge dos DataFrames
    vencimento_controle_df = pd.merge(vencimento_df_renomeado, fornecedor_final_df, on="CODIGO", how="left")

    # Converter a coluna VENCIMENTO para datetime
    vencimento_controle_df["VENCIMENTO"] = pd.to_datetime(vencimento_controle_df["VENCIMENTO"], errors="coerce")

    # Calcular dias para vencer
    hoje = datetime.now()
    vencimento_controle_df["DIAS_PARA_VENCER"] = (vencimento_controle_df["VENCIMENTO"] - hoje).dt.days

    # Filtrar apenas produtos que ainda não venceram (dias >= 0)
    vencimento_controle_df = vencimento_controle_df[vencimento_controle_df["DIAS_PARA_VENCER"] >= 0]

    # Formatar os dados
    vencimento_controle_df = formatar_dados(vencimento_controle_df)

    # Ordenar o DataFrame pela coluna "VENCIMENTO"
    vencimento_controle_df = vencimento_controle_df.sort_values(by="VENCIMENTO", ascending=True)

    filtro = ""
    dias_vencimento = ""
    
    if request.method == "POST":
        filtro = request.form.get("filtro", "").strip()
        dias_vencimento = request.form.get("dias_vencimento", "").strip()
    else:
        filtro = request.args.get("filtro", "").strip()
        dias_vencimento = request.args.get("dias_vencimento", "").strip()

    # Filtro de texto
    if filtro:
        vencimento_controle_df = vencimento_controle_df[
            vencimento_controle_df["CODIGO"].astype(str).str.contains(filtro, case=False, na=False) |
            vencimento_controle_df["DESCRICAO"].str.contains(filtro, case=False, na=False) |
            vencimento_controle_df["FORNECEDOR"].str.contains(filtro, case=False, na=False)
        ]

    # Filtro de dias para vencimento
    if dias_vencimento:
        try:
            dias_limite = int(dias_vencimento)
            # Filtrar produtos que vencem em até X dias
            vencimento_controle_df = vencimento_controle_df[vencimento_controle_df["DIAS_PARA_VENCER"] <= dias_limite]
        except (ValueError, TypeError):
            pass

    # Paginação
    page = int(request.args.get("page", 1))
    per_page = 50
    total_items = len(vencimento_controle_df)
    total_pages = ceil(total_items / per_page)

    # Definir colunas visíveis conforme especificado
    colunas_visiveis = ["CODIGO", "DESCRICAO", "COMPLEMENTO", "EMBALAGEM", "FORNECEDOR", "ESTOQ.EMB1", "ESTOQ.EMB9", "VALOR A VENCER", "VENCIMENTO"]
    
    # Filtrar para exibir apenas as colunas especificadas que existem no DataFrame
    colunas_existentes = [col for col in colunas_visiveis if col in vencimento_controle_df.columns]
    vencimento_controle_df = vencimento_controle_df[colunas_existentes]

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_df = vencimento_controle_df.iloc[start_index:end_index]

    # Converter para HTML
    vencimento_html = paginated_df.to_html(index=False, classes="styled-table")

    return render_template(
        "home.html",
        vencimento=vencimento_html,
        page=page,
        total_pages=total_pages,
        filtro=filtro,
        dias_vencimento=dias_vencimento
    )

@controle_vencimento.route("/valoravencer", methods=["GET"])
def valoravencer():
    global fornecedor_df, vencimento_df

    # Renomear e preparar os DataFrames (usando o mesmo mapeamento da rota principal)
    fornecedor_df_renomeado = fornecedor_df.rename(columns={"Item Produto": "CODIGO",
                                                           "Fornecedor Atual": "CPF/CNPJ",
                                                           "FORNECEDOR": "FORNECEDOR"})
    fornecedor_final_df = fornecedor_df_renomeado[["CODIGO", "CPF/CNPJ", "FORNECEDOR"]].dropna(subset=["FORNECEDOR"])

    vencimento_df_renomeado = vencimento_df.rename(columns={
        "CÓDIGO": "CODIGO",
        "DESCRIÇÃO MERCADORIA": "DESCRICAO",
        "DATA VENCIMENTO": "VENCIMENTO",
        "EST. LÍQ. EMB1": "ESTOQ.EMB1",
        "EST. LÍQ. EMB9": "ESTOQ.EMB9",
        "VALOR VENCIMENTO": "VALOR A VENCER"
    })

    # Merge dos DataFrames
    vencimento_controle_df = pd.merge(vencimento_df_renomeado, fornecedor_final_df, on="CODIGO", how="left")

    # Converter a coluna VENCIMENTO para datetime
    vencimento_controle_df["VENCIMENTO"] = pd.to_datetime(vencimento_controle_df["VENCIMENTO"], errors="coerce")

    # Calcular dias para vencer
    hoje = datetime.now()
    vencimento_controle_df["DIAS_PARA_VENCER"] = (vencimento_controle_df["VENCIMENTO"] - hoje).dt.days

    # Filtrar apenas produtos que ainda não venceram (dias >= 0)
    vencimento_controle_df = vencimento_controle_df[vencimento_controle_df["DIAS_PARA_VENCER"] >= 0]

    # Formatar os dados
    vencimento_controle_df = formatar_dados(vencimento_controle_df)

    # Ordenar por valor a vencer (descendente)
    vencimento_controle_df = vencimento_controle_df.sort_values(by="VALOR A VENCER", ascending=False)

    # Paginação
    page = int(request.args.get("page", 1))
    per_page = 50
    total_items = len(vencimento_controle_df)
    total_pages = ceil(total_items / per_page)

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_df = vencimento_controle_df.iloc[start_index:end_index]

    # Converter para HTML
    vencimento_html = paginated_df.to_html(index=False, classes="styled-table")

    return render_template(
        "valoravencer.html",
        vencimento=vencimento_html,
        page=page,
        total_pages=total_pages,
        total_items=total_items
    )


@controle_vencimento.route("/imprimir", methods=["GET"])
def imprimir():
    global fornecedor_df, vencimento_df

    # Obter parâmetros de filtro da URL
    filtro = request.args.get('filtro', '').strip()
    dias_vencimento = request.args.get('dias_vencimento', '').strip()

    # Renomear e preparar os DataFrames (pode ser extraído para função auxiliar)
    fornecedor_df_renomeado = fornecedor_df.rename(columns={
        "Item Produto": "CODIGO",
        "Fornecedor Atual": "CPF/CNPJ",
        "FORNECEDOR": "FORNECEDOR",
    })
    fornecedor_final_df = fornecedor_df_renomeado[["CODIGO", "CPF/CNPJ", "FORNECEDOR"]].dropna(subset=["FORNECEDOR"])

    vencimento_df_renomeado = vencimento_df.rename(columns={
        "CÓDIGO": "CODIGO",
        "DESCRIÇÃO MERCADORIA": "DESCRICAO",
        "COMPLEMENTO": "COMPLEMENTO",
        "EMBALAGEM": "EMBALAGEM",
        "DATA VENCIMENTO": "VENCIMENTO",
        "EST. LÍQ. EMB1": "ESTOQ.EMB1",
        "EST. LÍQ. EMB9": "ESTOQ.EMB9",
        "VALOR VENCIMENTO": "VALOR A VENCER"
    })

    # Merge dos DataFrames
    vencimento_controle_df = pd.merge(vencimento_df_renomeado, fornecedor_final_df, on="CODIGO", how="left")

    # Converter a coluna VENCIMENTO para datetime
    vencimento_controle_df["VENCIMENTO"] = pd.to_datetime(vencimento_controle_df["VENCIMENTO"], errors="coerce")

    # Calcular dias para vencer
    hoje = datetime.now()
    vencimento_controle_df["DIAS_PARA_VENCER"] = (vencimento_controle_df["VENCIMENTO"] - hoje).dt.days

    # Filtrar apenas produtos que ainda não venceram (dias >= 0)
    vencimento_controle_df = vencimento_controle_df[vencimento_controle_df["DIAS_PARA_VENCER"] >= 0]

    # Aplicar filtro de texto se fornecido
    if filtro:
        mask = (
            vencimento_controle_df["CODIGO"].astype(str).str.contains(filtro, case=False, na=False) |
            vencimento_controle_df["DESCRICAO"].astype(str).str.contains(filtro, case=False, na=False) |
            vencimento_controle_df["FORNECEDOR"].astype(str).str.contains(filtro, case=False, na=False)
        )
        vencimento_controle_df = vencimento_controle_df[mask]

    # Aplicar filtro de dias para vencimento se fornecido
    if dias_vencimento:
        try:
            dias_limite = int(dias_vencimento)
            vencimento_controle_df = vencimento_controle_df[vencimento_controle_df["DIAS_PARA_VENCER"] <= dias_limite]
        except ValueError:
            pass

    # Formatar os dados
    vencimento_controle_df = formatar_dados(vencimento_controle_df)

    # Definir colunas visíveis conforme especificado
    colunas_visiveis = ["CODIGO", "DESCRICAO", "COMPLEMENTO", "EMBALAGEM", "FORNECEDOR", "ESTOQ.EMB1", "ESTOQ.EMB9", "VALOR A VENCER", "VENCIMENTO"]
    
    # Filtrar para exibir apenas as colunas especificadas que existem no DataFrame
    colunas_existentes = [col for col in colunas_visiveis if col in vencimento_controle_df.columns]
    vencimento_controle_df = vencimento_controle_df[colunas_existentes]

    # Ordenar por data de vencimento
    vencimento_controle_df = vencimento_controle_df.sort_values(by="VENCIMENTO")

    vencimento_html = vencimento_controle_df.to_html(classes="styled-table", index=False, border=0, justify="center")

    return render_template(
        "imprimir.html",
        vencimento=vencimento_html,
        filtro=filtro,
        dias_vencimento=dias_vencimento,
        total_items=len(vencimento_controle_df)
    )

@controle_vencimento.route("/vencendo45", methods=["GET"])
def vencendo45():
    global fornecedor_df, vencimento_df

    # Renomear e preparar os DataFrames (pode ser extraído para função auxiliar)
    fornecedor_df_renomeado = fornecedor_df.rename(columns={
        "Item Produto": "CODIGO",
        "Fornecedor Atual": "CPF/CNPJ",
        "FORNECEDOR": "FORNECEDOR",
    })
    fornecedor_final_df = fornecedor_df_renomeado[["CODIGO", "CPF/CNPJ", "FORNECEDOR"]].dropna(subset=["FORNECEDOR"])

    vencimento_df_renomeado = vencimento_df.rename(columns={
        "CÓDIGO": "CODIGO",
        "DESCRIÇÃO MERCADORIA": "DESCRICAO",
        "DATA VENCIMENTO": "VENCIMENTO",
        "EST. LÍQ. EMB1": "ESTOQ.EMB1",
        "EST. LÍQ. EMB9": "ESTOQ.EMB9",
        "VALOR VENCIMENTO": "VALOR A VENCER"
    })

    # Merge dos DataFrames
    vencimento_controle_df = pd.merge(vencimento_df_renomeado, fornecedor_final_df, on="CODIGO", how="left")

    # Converter a coluna VENCIMENTO para datetime
    vencimento_controle_df["VENCIMENTO"] = pd.to_datetime(vencimento_controle_df["VENCIMENTO"], errors="coerce")

    # Calcular dias para vencer
    hoje = datetime.now()
    vencimento_controle_df["DIAS_PARA_VENCER"] = (vencimento_controle_df["VENCIMENTO"] - hoje).dt.days

    # Filtrar produtos que vencem em até 45 dias
    vencimento_controle_df = vencimento_controle_df[
        (vencimento_controle_df["DIAS_PARA_VENCER"] >= 0) & 
        (vencimento_controle_df["DIAS_PARA_VENCER"] <= 45)
    ]

    # Formatar os dados
    vencimento_controle_df = formatar_dados(vencimento_controle_df)

    # Ordenar por dias para vencer (ascendente)
    vencimento_controle_df = vencimento_controle_df.sort_values(by="DIAS_PARA_VENCER", ascending=True)

    # Paginação
    page = int(request.args.get("page", 1))
    per_page = 50
    total_items = len(vencimento_controle_df)
    total_pages = ceil(total_items / per_page)

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    paginated_df = vencimento_controle_df.iloc[start_index:end_index]

    # Converter para HTML
    vencendo_html = paginated_df.to_html(index=False, classes="styled-table")

    return render_template(
        "vencendo45.html",
        vencimento=vencendo_html,
        page=page,
        total_pages=total_pages,
        total_items=total_items
    )

@controle_vencimento.route("/vencendo45/exportar")
def exportar_vencendo45():
    global fornecedor_df, vencimento_df

    # Preparar dados (mesmo código da rota vencendo45)
    fornecedor_df_renomeado = fornecedor_df.rename(columns={
        "Item Produto": "CODIGO",
        "Fornecedor Atual": "CPF/CNPJ",
        "FORNECEDOR": "FORNECEDOR",
    })
    fornecedor_final_df = fornecedor_df_renomeado[["CODIGO", "CPF/CNPJ", "FORNECEDOR"]].dropna(subset=["FORNECEDOR"])

    vencimento_df_renomeado = vencimento_df.rename(columns={
        "CÓDIGO": "CODIGO",
        "DESCRIÇÃO MERCADORIA": "DESCRICAO",
        "DATA VENCIMENTO": "VENCIMENTO",
        "EST. LÍQ. EMB1": "ESTOQ.EMB1",
        "EST. LÍQ. EMB9": "ESTOQ.EMB9",
        "VALOR VENCIMENTO": "VALOR A VENCER"
    })

    vencimento_controle_df = pd.merge(vencimento_df_renomeado, fornecedor_final_df, on="CODIGO", how="left")
    vencimento_controle_df["VENCIMENTO"] = pd.to_datetime(vencimento_controle_df["VENCIMENTO"], errors="coerce")

    hoje = datetime.now()
    vencimento_controle_df["DIAS_PARA_VENCER"] = (vencimento_controle_df["VENCIMENTO"] - hoje).dt.days

    # Filtrar produtos que vencem em até 45 dias
    vencimento_controle_df = vencimento_controle_df[
        (vencimento_controle_df["DIAS_PARA_VENCER"] >= 0) & 
        (vencimento_controle_df["DIAS_PARA_VENCER"] <= 45)
    ]

    # Exporta para CSV em memória (BytesIO)
    output = BytesIO()
    vencimento_controle_df.to_csv(output, index=False, sep=";", encoding="utf-8")
    output.seek(0)

    return send_file(
        output,
        download_name="vencendo_45_dias.csv",
        as_attachment=True,
        mimetype="text/csv"
    )

@controle_vencimento.route("/valoravencer/exportar")
def exportar_valoravencer():
    global fornecedor_df, vencimento_df

    # Preparar dados (mesmo código da rota valoravencer)
    fornecedor_df_renomeado = fornecedor_df.rename(columns={
        "Item Produto": "CODIGO",
        "Fornecedor Atual": "CPF/CNPJ",
        "FORNECEDOR": "FORNECEDOR",
    })
    fornecedor_final_df = fornecedor_df_renomeado[["CODIGO", "CPF/CNPJ", "FORNECEDOR"]].dropna(subset=["FORNECEDOR"])

    vencimento_df_renomeado = vencimento_df.rename(columns={
        "CÓDIGO": "CODIGO",
        "DESCRIÇÃO MERCADORIA": "DESCRICAO",
        "DATA VENCIMENTO": "VENCIMENTO",
        "EST. LÍQ. EMB1": "ESTOQ.EMB1",
        "EST. LÍQ. EMB9": "ESTOQ.EMB9",
        "VALOR VENCIMENTO": "VALOR A VENCER"
    })

    vencimento_controle_df = pd.merge(vencimento_df_renomeado, fornecedor_final_df, on="CODIGO", how="left")
    vencimento_controle_df["VENCIMENTO"] = pd.to_datetime(vencimento_controle_df["VENCIMENTO"], errors="coerce")

    hoje = datetime.now()
    vencimento_controle_df["DIAS_PARA_VENCER"] = (vencimento_controle_df["VENCIMENTO"] - hoje).dt.days
    vencimento_controle_df = vencimento_controle_df[vencimento_controle_df["DIAS_PARA_VENCER"] >= 0]

    # Exporta para CSV em memória (BytesIO)
    output = BytesIO()
    vencimento_controle_df.to_csv(output, index=False, sep=";", encoding="utf-8")
    output.seek(0)

    return send_file(
        output,
        download_name="valor_a_vencer.csv",
        as_attachment=True,
        mimetype="text/csv"
    )

@controle_vencimento.route("/exportar", methods=["GET"])
def exportar():
    global fornecedor_df, vencimento_df

    # Obter filtros da URL
    filtro = request.args.get("filtro", "").strip()
    dias_vencimento = request.args.get("dias_vencimento", "").strip()

    # Preparar dados (mesmo código da rota home)
    fornecedor_df_renomeado = fornecedor_df.rename(columns={
        "Item Produto": "CODIGO",
        "Fornecedor Atual": "CPF/CNPJ",
        "FORNECEDOR": "FORNECEDOR",
    })
    fornecedor_final_df = fornecedor_df_renomeado[["CODIGO", "CPF/CNPJ", "FORNECEDOR"]].dropna(subset=["FORNECEDOR"])

    vencimento_df_renomeado = vencimento_df.rename(columns={
        "CÓDIGO": "CODIGO",
        "DESCRIÇÃO MERCADORIA": "DESCRICAO",
        "DATA VENCIMENTO": "VENCIMENTO",
        "EST. LÍQ. EMB1": "ESTOQ.EMB1",
        "EST. LÍQ. EMB9": "ESTOQ.EMB9",
        "VALOR VENCIMENTO": "VALOR A VENCER"
    })

    vencimento_controle_df = pd.merge(vencimento_df_renomeado, fornecedor_final_df, on="CODIGO", how="left")
    vencimento_controle_df["VENCIMENTO"] = pd.to_datetime(vencimento_controle_df["VENCIMENTO"], errors="coerce")

    hoje = datetime.now()
    vencimento_controle_df["DIAS_PARA_VENCER"] = (vencimento_controle_df["VENCIMENTO"] - hoje).dt.days
    vencimento_controle_df = vencimento_controle_df[vencimento_controle_df["DIAS_PARA_VENCER"] >= 0]

    # Aplicar filtros
    if filtro:
        vencimento_controle_df = vencimento_controle_df[
            vencimento_controle_df["CODIGO"].astype(str).str.contains(filtro, case=False, na=False) |
            vencimento_controle_df["DESCRICAO"].str.contains(filtro, case=False, na=False) |
            vencimento_controle_df["FORNECEDOR"].str.contains(filtro, case=False, na=False)
        ]

    if dias_vencimento:
        try:
            dias_limite = int(dias_vencimento)
            vencimento_controle_df = vencimento_controle_df[vencimento_controle_df["DIAS_PARA_VENCER"] <= dias_limite]
        except ValueError:
            pass

    # Definir colunas visíveis
    colunas_visiveis = ["CODIGO", "DESCRICAO", "VENCIMENTO", "ESTOQ.EMB1", "ESTOQ.EMB9", "VALOR A VENCER", "FORNECEDOR"]

    # Filtrar para garantir que só exporta as colunas visíveis
    vencimento_controle_df = vencimento_controle_df[[col for col in colunas_visiveis if col in vencimento_controle_df.columns]]

    # Exporta para CSV em memória (BytesIO)
    output = BytesIO()
    vencimento_controle_df.to_csv(output, index=False, sep=";", encoding="utf-8")
    output.seek(0)

    return send_file(
        output,
        download_name="vencimentos_filtrados.csv",
        as_attachment=True,
        mimetype="text/csv"
    )

@controle_vencimento.route('/page')
def vencimento_page():
    """Página principal do controle de vencimento"""
    try:
        return render_template('vencimento_page.html')
    except Exception as e:
        return render_template('vencimento_page.html', error=str(e))