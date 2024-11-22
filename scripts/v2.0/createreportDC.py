import pandas as pd
import webbrowser
import tempfile
import json
import glob


# Leer el archivo de configuración
with open("config_encrypted.json") as config_file:
    config = json.load(config_file)


# Función para cargar y aplicar estilo a los datos
def load_and_style_data(system, hostname, config):
    # Obtener los nombres de archivo desde la configuración
    base_path = config.get('basePath', '')
    csv_files = config['systems'][system]['files']['csv']
    
    health_files = glob.glob(f"{base_path}/{system}-{hostname}-{csv_files['dashboardHealh']}")
    job_files = glob.glob(f"{base_path}/{system}-{hostname}-{csv_files['dashboardjobgroupActivities']}")

    # Inicializar variables para almacenar el HTML
    html_health = ""
    html_job_group = ""

    # Procesar archivos de "Health"
    for health_file in health_files:
        df_health = pd.read_csv(health_file)
        styled_health = df_health.style.applymap(color_score, subset=['Score'])
        html_health += styled_health.to_html()

    # Procesar archivos de "Job Group Activities"
    for job_file in job_files:
        df_job_group = pd.read_csv(job_file)
        styled_job_group = df_job_group.style.apply(color_failed, axis=1)
        html_job_group += styled_job_group.to_html()

    return html_health, html_job_group


# Definir la función para colorear las celdas en la columna "Score"
def color_score(val):
    if val == 0:
        return 'background-color: #b3e6b3; color: #2d6a2d'  # Verde pastel
    elif 0 > val >= -20:
        return 'background-color: #fff2b3; color: #7a7a00'  # Amarillo pastel
    elif val < -20:
        return 'background-color: #f7b3b3; color: #a10000'  # Rojo pastel
    return ''


# Definir la función para colorear la celda en la columna "Num" de la fila "FAILED" en la segunda tabla
def color_failed(row):
    if row['STATUS'] == 'Failed' and row['Num'] != 0:
        return ['background-color: #f7b3b3; color: #a10000'] * len(row)
    return [''] * len(row)


# CSS personalizado para mejorar el estilo visual de las tablas
table_style = """
<style>
    table {
        border-collapse: collapse;
        width: 100%;
        font-family: Arial, sans-serif;
        margin-bottom: 20px;
        font-size: 11px;  /* Tamaño de fuente para toda la tabla */
    }
    th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
        font-size: 11px;  /* Tamaño de fuente para las celdas */
        padding: 4px 4px;  /* Reducir el padding vertical a 4px y horizontal a 8px */
    }
    th {
        background-color: #cccccc;
        color: white;
        font-weight: bold;
    }
    tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    tr:hover {
        background-color: #ddd;
    }
</style>
"""


# Crear el cuerpo HTML del correo
html_body = f"""
<html>
    <head>{table_style}</head>
    <body>
        <h2 style="font-family: Arial, sans-serif; color: #0044cc;">DAILY INVESTIGATION PPDM</h2>
"""


# Iterar sobre los sistemas y hostnames en el archivo de configuración
for system, system_config in config["systems"].items():
    for instance_config in system_config['instances']:
        hostname = instance_config["hostname"]

        # Cargar y dar estilo a los datos para el hostname actual
        html_health, html_job_group = load_and_style_data(system, hostname, config)

        # Agregar la sección para el hostname actual
        html_body += f"""
        <h3 style="font-family: Arial, sans-serif; color: #0066cc;">Hostname: {hostname}</h3>
        
        <div style="display: flex; justify-content: space-around; padding: 10px;">
            <div style="width: 48%;">
                <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333;">
                    Health Status
                </p>
                {html_health}
            </div>
            <div style="width: 48%;">
                <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333;">
                    Jobs | Protection - Last 24 hours
                </p>
                {html_job_group}
            </div>
        </div>
        """


# Finalizar el HTML
html_body += "</body></html>"


# Guardar el HTML en un archivo temporal y abrirlo en el navegador
with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
    f.write(html_body)
    temp_file_path = f.name


# Abrir el archivo en el navegador predeterminado
webbrowser.open(f'file://{temp_file_path}')
