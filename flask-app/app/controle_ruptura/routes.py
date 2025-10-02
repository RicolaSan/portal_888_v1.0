from flask import render_template, request, send_file, jsonify
from . import controle_ruptura
import pandas as pd 
import openpyxl
from math import ceil
from io import BytesIO
import logging

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def calculo_ruptura():
    """
    Processes rupture control data from CSV file.
    
    Returns:
        pd.DataFrame: Processed DataFrame with rupture control data
    """
    try:
        file_path = r'\\10.122.244.1\files\gerencial\gerencia\edvan\smg12.f888.csv'
        
        # Read CSV with error handling
        smg12_df = pd.read_csv(file_path, sep=';', encoding='latin1')
        
        # Column mapping for better readability
        column_mapping = {
            'MERC': 'CODIGO',
            'NAO VENDE (RUPT.)': 'DIA S/VND (RUPT.)',
            'DT ULT ENT': 'DT ULT ENTRADA',
            'QTD ULT ENT': 'ENTRADA EMB1',
        }
        
        smg12_df = smg12_df.rename(columns=column_mapping)
        
        # Define selected columns (GRUPO is kept for filtering but will be hidden in display)
        colunas_selecionadas = [
            'CODIGO', 'DESCRICAO', 'EMBALAGEM', 'DT ULT ENTRADA',
            'DIA S/VND (RUPT.)', 'ENTRADA EMB1', 'ESTOQ EMB1',
            'ESTOQ EMB9', 'DT ULT VND', 'IDADE', 'DIAS S/VND', 'GRUPO'
        ]
        
        # Filter columns that exist in the DataFrame
        existing_columns = [col for col in colunas_selecionadas if col in smg12_df.columns]
        smg12_df = smg12_df[existing_columns]
        
        # Clean data
        smg12_df = smg12_df.dropna(subset=['DIA S/VND (RUPT.)'])
        smg12_df['ESTOQ EMB1'] = smg12_df['ESTOQ EMB1'].fillna(0)
        smg12_df['ESTOQ EMB9'] = smg12_df['ESTOQ EMB9'].fillna(0)
        
        # Process numeric columns
        colunas_numericas = ['ESTOQ EMB1', 'ESTOQ EMB9', 'ENTRADA EMB1', 
                           'DIA S/VND (RUPT.)', 'IDADE']
        
        for coluna in colunas_numericas:
            if coluna in smg12_df.columns:
                smg12_df[coluna] = (smg12_df[coluna]
                                   .fillna(0)
                                   .astype(str)
                                   .str.replace(',', '.')
                                   .str.strip())
                smg12_df[coluna] = pd.to_numeric(smg12_df[coluna], errors='coerce').fillna(0).astype(int)
        
        # Sort by group
        if 'GRUPO' in smg12_df.columns:
            smg12_df = smg12_df.sort_values(by=['GRUPO', 'CODIGO'])
        if 'DT ULT ENTRADA' in smg12_df.columns:
            smg12_df['DT ULT ENTRADA'].fillna('SEM ENTRADA',inplace=True)
        
        return smg12_df
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        return pd.DataFrame()

def get_grupos_disponiveis():
    """
    Get list of available groups from the data.
    
    Returns:
        list: List of unique groups
    """
    try:
        smg12_df = calculo_ruptura()
        if 'GRUPO' in smg12_df.columns:
            grupos = sorted(smg12_df['GRUPO'].dropna().unique().tolist())
            return grupos
        return []
    except Exception as e:
        logger.error(f"Error getting groups: {str(e)}")
        
    
        return []

@controle_ruptura.route('/')
def index():
    """
    Main route for displaying rupture control data with pagination and group filtering.
    GRUPO column is hidden from display but used for filtering.
    """
    try:
        # Get parameters from query string
        page = request.args.get('page', 1, type=int)
        grupo_selecionado = request.args.get('grupo', '')
        per_page = 50
        
        # Get all data
        smg12_df = calculo_ruptura()
        
        # Get available groups
        grupos_disponiveis = get_grupos_disponiveis()
        
        # Check if data is empty
        if smg12_df.empty:
            return render_template('controle_ruptura.html', 
                                 smg12_df='', 
                                 page=1, 
                                 total_pages=0,
                                 grupos_disponiveis=grupos_disponiveis,
                                 grupo_selecionado=grupo_selecionado,
                                 total_items=0)
        
        # Filter by group if selected
        if grupo_selecionado and grupo_selecionado != 'todos':
            smg12_df = smg12_df[smg12_df['GRUPO'] == grupo_selecionado]
            smg12_df = smg12_df.sort_values(by=['ESTOQ EMB1'], ascending=False)
      
            
            
        
        # Calculate pagination
        total_items = len(smg12_df)
        total_pages = ceil(total_items / per_page) if total_items > 0 else 1
        
        # Validate page number
        if page < 1:
            page = 1
        elif page > total_pages:
            page = total_pages
        
        # Get data for current page
        if total_items > 0:
            start_idx = (page - 1) * per_page
            end_idx = min(start_idx + per_page, total_items)
            page_data = smg12_df.iloc[start_idx:end_idx]
            
            # Define display columns (GRUPO column is ALWAYS excluded from display)
            colunas_exibidas = [
                'CODIGO', 'DESCRICAO', 'EMBALAGEM', 'DT ULT ENTRADA',
                'ENTRADA EMB1', 'DIA S/VND (RUPT.)', 'ESTOQ EMB1',
                'ESTOQ EMB9', 'DT ULT VND', 'IDADE'
            ]
            
            # Filter to existing display columns (excluding GRUPO)
            existing_display_columns = [col for col in colunas_exibidas if col in page_data.columns]
            page_data_display = page_data[existing_display_columns]
            
            # Convert to HTML
            smg12_html = page_data_display.to_html(
                classes='table table-striped table-hover table-sm',
                index=False,
                escape=False,
                table_id='rupture-table'
            )
            
            start_item = start_idx + 1
            end_item = end_idx
        else:
            smg12_html = '<div class="alert alert-info">Nenhum item encontrado para o grupo selecionado.</div>'
            start_item = 0
            end_item = 0
    
        
        return render_template('controle_ruptura.html', 
                              smg12_df=smg12_html, 
                              page=page, 
                              total_pages=total_pages,
                              total_items=total_items,
                              start_item=start_item,
                              end_item=end_item,
                              grupos_disponiveis=grupos_disponiveis,
                              grupo_selecionado=grupo_selecionado)
                              
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return render_template('controle_ruptura.html', 
                             smg12_df='', 
                             page=1, 
                             total_pages=0,
                             grupos_disponiveis=[],
                             grupo_selecionado='',
                             total_items=0)

@controle_ruptura.route('/api/grupos')
def api_grupos():
    """
    API endpoint to get available groups.
    """
    try:
        grupos = get_grupos_disponiveis()
        return jsonify({
            'success': True,
            'grupos': grupos
        })
    except Exception as e:
        logger.error(f"Error in API grupos: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@controle_ruptura.route('/imprimir')
def imprimir():
    """
    Route for printing all filtered data without pagination.
    """
    try:
        # Get filter parameters
        grupo_selecionado = request.args.get('grupo', 'todos')
        
        # Load all data
        smg12_df = calculo_ruptura()
        
        if smg12_df is None or smg12_df.empty:
            return render_template('controle_ruptura_print.html', 
                                 smg12_df='', 
                                 grupo_selecionado=grupo_selecionado,
                                 total_items=0)
        
        # Filter by group if selected
        if grupo_selecionado and grupo_selecionado != 'todos':
            smg12_df = smg12_df[smg12_df['GRUPO'] == grupo_selecionado]
            smg12_df = smg12_df.sort_values(by=['ESTOQ EMB1'], ascending=False)
        
        # Define display columns (GRUPO column is ALWAYS excluded from display)
        colunas_exibidas = [
            'CODIGO', 'DESCRICAO', 'EMBALAGEM', 'DT ULT ENTRADA',
            'ENTRADA EMB1', 'DIA S/VND (RUPT.)', 'ESTOQ EMB1',
            'ESTOQ EMB9', 'DT ULT VND', 'IDADE'
        ]
        
        # Filter to existing display columns (excluding GRUPO)
        existing_display_columns = [col for col in colunas_exibidas if col in smg12_df.columns]
        smg12_df_display = smg12_df[existing_display_columns]
        
        # Convert to HTML for printing
        smg12_html = smg12_df_display.to_html(
            classes='table table-striped table-hover table-sm print-table',
            index=False,
            escape=False,
            table_id='print-rupture-table'
        )
        
        total_items = len(smg12_df)
        
        return render_template('controle_ruptura_print.html', 
                             smg12_df=smg12_html, 
                             grupo_selecionado=grupo_selecionado,
                             total_items=total_items)
                              
    except Exception as e:
        logger.error(f"Error in print route: {str(e)}")
        return render_template('controle_ruptura_print.html', 
                             smg12_df='', 
                             grupo_selecionado='todos',
                             total_items=0)

@controle_ruptura.route('/export')
def export_excel():
    """
    Export rupture control data to Excel file with group filtering.
    GRUPO column can be optionally included in Excel export.
    """
    try:
        grupo_selecionado = request.args.get('grupo', '')
        include_grupo = request.args.get('include_grupo', 'false').lower() == 'true'
        
        smg12_df = calculo_ruptura()
        
        if smg12_df.empty:
            return jsonify({'error': 'Não há dados para exportar'}), 400
        
        # Filter by group if selected
        original_df = smg12_df.copy()  # Keep original for group info
        if grupo_selecionado and grupo_selecionado != 'todos':
            smg12_df = smg12_df[smg12_df['GRUPO'] == grupo_selecionado]
            filename = f'controle_ruptura_{grupo_selecionado}.xlsx'
        else:
            filename = 'controle_ruptura_todos_grupos.xlsx'
        
        if smg12_df.empty:
            return jsonify({'error': 'Nenhum dado encontrado para o grupo selecionado'}), 400
        
        # Define export columns (GRUPO can be included based on parameter)
        if include_grupo:
            export_columns = [
                'CODIGO', 'DESCRICAO', 'EMBALAGEM', 'DT ULT ENTRADA',
                'ENTRADA EMB1', 'DIA S/VND (RUPT.)', 'ESTOQ EMB1',
                'ESTOQ EMB9', 'DT ULT VND', 'IDADE', 'GRUPO'
            ]
        else:
            export_columns = [
                'CODIGO', 'DESCRICAO', 'EMBALAGEM', 'DT ULT ENTRADA',
                'ENTRADA EMB1', 'DIA S/VND (RUPT.)', 'ESTOQ EMB1',
                'ESTOQ EMB9', 'DT ULT VND', 'IDADE'
            ]
        
        # Filter to existing export columns
        existing_export_columns = [col for col in export_columns if col in smg12_df.columns]
        export_df = smg12_df[existing_export_columns]
        
        # Create Excel file in memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, sheet_name='Controle_Ruptura', index=False)
            
            # Format the Excel file
            workbook = writer.book
            worksheet = writer.sheets['Controle_Ruptura']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        return jsonify({'error': 'Erro ao exportar dados'}), 500

@controle_ruptura.route('/api/group-stats')
def api_group_stats():
    """
    API endpoint to get statistics by group.
    """
    try:
        smg12_df = calculo_ruptura()
        
        if smg12_df.empty or 'GRUPO' not in smg12_df.columns:
            return jsonify({
                'success': True,
                'stats': {}
            })
        
        # Calculate statistics by group
        group_stats = {}
        for grupo in smg12_df['GRUPO'].unique():
            group_data = smg12_df[smg12_df['GRUPO'] == grupo]
            group_stats[grupo] = {
                'total_items': len(group_data),
                'avg_rupture_days': round(group_data['DIA S/VND(RUPT.)'].mean(), 2) if len(group_data) > 0 else 0,
                'total_stock_emb1': int(group_data['ESTOQ EMB1'].sum()) if 'ESTOQ EMB1' in group_data.columns else 0,
                'total_stock_emb9': int(group_data['ESTOQ EMB9'].sum()) if 'ESTOQ EMB9' in group_data.columns else 0
            }
        
        return jsonify({
            'success': True,
            'stats': group_stats
        })
        
    except Exception as e:
        logger.error(f"Error getting group stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500