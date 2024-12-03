import modules.functions as fn
import os
import pandas as pd
import webbrowser
import tempfile
import json
import glob
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# CSS modificado con control de altura
table_style = """
<style>
    /* Reset de estilos para Outlook */
    table {
        border-collapse: collapse !important;
        width: 100% !important;
        margin-bottom: 20px !important;
        mso-table-lspace: 0pt !important;
        mso-table-rspace: 0pt !important;
        font-size: 11px !important;
    }
    th, td {
        border: 1px solid #ddd !important;
        padding: 2px 4px !important;  /* Reducido el padding vertical a 2px */
        text-align: left !important;
        font-family: Arial, sans-serif !important;
        font-size: 11px !important;
        mso-line-height-rule: exactly !important;
        line-height: 1.2 !important;  /* Altura de línea reducida */
        height: 16px !important;      /* Altura fija para las celdas */
    }
    th {
        background-color: #cccccc !important;
        color: white !important;
        font-weight: bold !important;
        height: 18px !important;      /* Altura ligeramente mayor para encabezados */
    }
    tr {
        height: 16px !important;      /* Altura fija para las filas */
    }
    tr:nth-child(even) {
        background-color: #f2f2f2 !important;
    }
    /* Contenedor de tabla para layout lado a lado */
    .table-cell {
        width: 48% !important;
        padding: 5px !important;
        vertical-align: top !important;
    }
    /* Clase específica para las tablas de datos */
    .data-table {
        margin: 0 !important;
        padding: 0 !important;
    }
    .data-table td {
        height: 16px !important;
        max-height: 16px !important;
        overflow: hidden !important;
        white-space: nowrap !important;
    }
</style>
"""


# Layouts predeterminados por sistema
DEFAULT_SYSTEM_LAYOUTS = {
    "PPDM": {
        "layout": [
            {"cells": [
                {"tables": ["dashboardJobGroupRate", "dashboardjobgroupActivities"]},
                {"tables": ["healthSystem", "dashboardHealh"]},
                {"tables": ["storageSystems"]}
            ]}
        ]
    },
    "DD": {
        "layout": [
            {"cells": [
                {"tables": ["alertSeveritySummary"]},
                {"tables": ["alertsByClass"]},
                {"tables": ["servicesStatus"]}
            ]}
        ]
    },    
    # Layout por defecto para otros sistemas
    "DEFAULT": {
        "layout": {}
    }
}


ADVANCED_STYLE_FUNCTIONS = {
    'dashboardJobGroupRate': {
        'Rate (%)': lambda val: (
        'background-color: #b3e6b3; color: #2d6a2d' if val == "ready" else
        'background-color: #fff2b3; color: #7a7a00' if val == "migrating" else
        'background-color: #f7b3b3; color: #a10000' if val == "not_ready" else ''
        )
    },
    'healthSystem': {
        'STATUS': lambda val: (
            'background-color: #b3e6b3; color: #2d6a2d' if val == "GOOD" else
            'background-color: #fff2b3; color: #7a7a00' if val == "FAIR" else
            'background-color: #f7b3b3; color: #a10000' if val == "POOR" else ''
        )
    },    
    'dashboardHealh': {
        'Score': lambda val: (
            'background-color: #b3e6b3; color: #2d6a2d' if val == 0 else
            'background-color: #fff2b3; color: #7a7a00' if -20 <= val < 0 else
            'background-color: #f7b3b3; color: #a10000' if val < -20 else ''
        )
    },
    'storageSystems': {
        'READINESS': lambda val: (
            'background-color: #b3e6b3; color: #2d6a2d' if val == "ready" else
            'background-color: #fff2b3; color: #7a7a00' if val == "migrating" else
            'background-color: #f7b3b3; color: #a10000' if val == "not_ready" else ''
        ),
        'STATUS': lambda val: (
            'background-color: #b3e6b3; color: #2d6a2d' if val == "GOOD" else
            'background-color: #fff2b3; color: #7a7a00' if val == "FAIR" else
            'background-color: #f7b3b3; color: #a10000' if val == "POOR" else ''
        )
    },
    'servicesStatus': {
        'status': lambda val:(
            'background-color: #b3e6b3; color: #2d6a2d' if val == "ENABLED" else
            'background-color: #f7b3b3; color: #a10000' if val == "DISABLED" else ''
        )   
    },
    'alertsByClass': {
        'numAlerts': lambda val: (
            'background-color: #b3e6b3; color: #2d6a2d' if val == 0 else
            'background-color: #f7b3b3; color: #a10000' if val > 0 else ''
        )
    }
}


def load_and_style_data(system, hostname, config, custom_styles=None):
    base_path = config['basePath']
    csv_relative_path = config['csvPath']
    csvPath = os.path.join(base_path, csv_relative_path)
    csv_files = config['systems'][system]['files']['csv']

    html_tables = {}
    style_functions = custom_styles or {}

    for table_name, file_pattern in csv_files.items():
        file_path = f"{csvPath}/{system}-{hostname}-{file_pattern}"
        matching_files = glob.glob(file_path)

        for csv_file in matching_files:
            try:
                df = pd.read_csv(csv_file)

                if df.empty:
                    print(f"El archivo {csv_file} está vacío. Se omite.")
                    continue

                print(f"Columnas disponibles en {csv_file}: {df.columns}")  # Depuración: columnas

                # Aplicar estilos específicos si están definidos para esta tabla
                if table_name in style_functions:
                    for col, style_func in style_functions[table_name].items():
                        if col in df.columns:
                            # Aplicar estilos de manera segura
                            df[col] = df[col].apply(lambda x: f'<span style="{style_func(x)}">{x}</span>' 
                                                    if style_func(x) else x)

                # Convertir a HTML
                html_table = df.to_html(
                    classes='data-table', 
                    escape=False,
                    table_id=f'{system}-{table_name}'
                )

                # Agregar atributos de sistema y tabla
                html_table = html_table.replace(
                    '<table', 
                    f'<table data-system="{system}" data-table="{table_name}"'
                )

                html_tables[table_name] = html_table
                print(f"Tabla HTML generada correctamente para {table_name}.")  # Depuración: éxito
                
            except Exception as e:
                print(f"Error processing {csv_file}: {e}")
                import traceback
                traceback.print_exc()

    return html_tables



def generate_html_report(config, custom_styles=None):
    html_body = f"""
    <html>
        <head>
            {table_style}
        </head>
        <body>
            <div style="width: 100%; max-width: 1200px; margin: 0 auto;">
                <h2 style="font-family: Arial, sans-serif; color: #0044cc; margin-bottom: 10px;">DAILY CHECK REPORT</h2>
    """

    # Iterar sobre sistemas en el orden del JSON
    for system, system_config in config["systems"].items():
        html_body += f"""
        <h3 style="font-family: Arial, sans-serif; color: #0066cc; margin: 10px 0;">System: {system}</h3>
        """
        
        # Obtener layout para este sistema (o usar layout por defecto)
        system_layout = DEFAULT_SYSTEM_LAYOUTS.get(system, DEFAULT_SYSTEM_LAYOUTS["DEFAULT"])
        
        # Procesar cada instancia del sistema
        for instance_config in system_config['instances']:
            hostname = instance_config["hostname"]
            
            html_body += f"""
            <h4 style="font-family: Arial, sans-serif; color: #0088cc; margin: 10px 0;">Hostname: {hostname}</h4>
            """
            
            # Cargar y procesar datos para este sistema e instancia
            html_tables = load_and_style_data(system, hostname, config, custom_styles)
            
            # Procesar layout específico del sistema
            for layout_section in system_layout["layout"]:
                html_body += """
                <table cellpadding="0" cellspacing="0" border="0" width="100%" style="table-layout: fixed;">
                    <tr>
                """
                
                # Procesar cada celda del layout
                for cell in layout_section["cells"]:
                    html_body += """
                    <td class="table-cell">
                    """
                    
                    # Agregar tablas a esta celda
                    for table_name in cell["tables"]:
                        if table_name in html_tables:
                            html_body += f"""
                            <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333; margin: 5px 0;">
                                {table_name}
                            </p>
                            {html_tables[table_name]}
                            """
                    
                    html_body += """
                    </td>
                    """
                
                html_body += """
                    </tr>
                </table>
                """

    html_body += """
            </div>
        </body>
    </html>
    """

    return html_body


# Cargar configuración
with open("config_encrypted.json") as config_file:
    config = json.load(config_file)


# Generar fecha actual
dateToday = datetime.now().strftime("%Y%m%d")


# Generar HTML
html_body = generate_html_report(config, custom_styles=ADVANCED_STYLE_FUNCTIONS)


with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
    f.write(html_body)
    temp_file_path = f.name

webbrowser.open(f'file://{temp_file_path}')