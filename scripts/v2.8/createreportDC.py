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



# Leer el archivo de configuración
with open("config_encrypted.json") as config_file:
    config = json.load(config_file)


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


# Definir la función para colorear las celdas en la columna "status" de la tercera tabla
def color_status(val):
    if val == "GOOD":
        return 'background-color: #b3e6b3; color: #2d6a2d'  # Verde pastel
    elif val == "FAIR":
        return 'background-color: #fff2b3; color: #7a7a00'  # Amarillo pastel
    elif val == "POOR":
        return 'background-color: #f7b3b3; color: #a10000'  # Rojo pastel
    return ''


# Definir la función para colorear las celdas en la columna "READINESS"
def color_readiness(val): 
    if val == "ready": 
        return 'background-color: #b3e6b3; color: #2d6a2d'  # Verde pastel
    elif val == "migrating": 
        return 'background-color: #fff2b3; color: #7a7a00'  # Amarillo pastel
    elif val == "not_ready": 
        return 'background-color: #f7b3b3; color: #a10000'  # Rojo pastel
    return ''


# Definir la función de estilo para colorear las celdas de la columna "Rate (%)"
def color_rate(val):
    if val == 100:
        return 'background-color: #b3e6b3; color: #2d6a2d'  # Verde pastel
    elif 90 <= val < 100:
        return 'background-color: #ffdab3; color: #7a4100'  # Naranja pastel
    elif 80 <= val < 90:
        return 'background-color: #fff2b3; color: #7a7a00'  # Amarillo pastel
    elif val < 80:
        return 'background-color: #f7b3b3; color: #a10000'  # Rojo pastel
    return ''


# Definir la función de estilo para colorear las celdas de la columna "Health status"
def color_health_status(val):
    if val == "GOOD":
        return 'background-color: #b3e6b3; color: #2d6a2d'  # Verde pastel
    elif val == "FAIR":
        return 'background-color: #fff2b3; color: #7a7a00'  # Amarillo pastel
    elif val == "POOR":
        return 'background-color: #f7b3b3; color: #a10000'  # Rojo pastel
    return ''


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

# Modificar las funciones de estilizado para incluir las clases
def load_and_style_data(system, hostname, config):
    # Obtener los nombres de archivo desde la configuración
    base_path = config['basePath']
    csv_relative_path = config['csvPath']
    csvPath= os.path.join(base_path, csv_relative_path)
    csv_files = config['systems'][system]['files']['csv']

    health_files = glob.glob(f"{csvPath}/{system}-{hostname}-{csv_files['dashboardHealh']}")
    health_system_files = glob.glob(f"{csvPath}/{system}-{hostname}-{csv_files['healthSystem']}")
    job_files = glob.glob(f"{csvPath}/{system}-{hostname}-{csv_files['dashboardjobgroupActivities']}")
    rate_files = glob.glob(f"{csvPath}/{system}-{hostname}-{csv_files['dashboardJobGroupRate']}")
    storage_files = glob.glob(f"{csvPath}/{system}-{hostname}-{csv_files['storageSystems']}")
 
    html_health = ""
    html_health_system = ""
    html_job_group = ""
    html_job_rate = ""
    html_storage_systems = ""
    
    # Process Health files
    for health_file in health_files:
        df_health = pd.read_csv(health_file)
        styled_health = df_health.style.applymap(color_score, subset=['Score'])
        html_health = styled_health.to_html(table_attributes='class="data-table"')

    for health_system_file in health_system_files:
        df_health_system = pd.read_csv(health_system_file)
        styled_health_system = df_health_system.style.applymap(color_health_status, subset=['STATUS'])
        html_health_system = styled_health_system.to_html(table_attributes='class="data-table"')
    
    # Process Job Group Activities files
    for job_file in job_files:
        df_job_group = pd.read_csv(job_file)
        styled_job_group = df_job_group.style.apply(color_failed, axis=1)
        html_job_group = styled_job_group.to_html(table_attributes='class="data-table"')

    # Process Job Group Rate files (nueva tabla)
    for rate_file in rate_files:
        df_rate = pd.read_csv(rate_file)

        # Asegurarse de que "Rate (%)" esté en formato numérico
        df_rate["Rate (%)"] = pd.to_numeric(df_rate["Rate (%)"], errors="coerce")
        styled_job_rate = (
            df_rate.style
            .set_table_attributes('class="data-table"')  # Asegurar clase CSS
            .applymap(color_rate, subset=["Rate (%)"])  # Colorear solo la columna "Rate (%)"
            .format({"Rate (%)": "{:.2f}"})  # Limitar a 2 decimales
        )
        html_job_rate = styled_job_rate.to_html()

    # Process Storage Systems files
    for storage_file in storage_files:
        df_storage = pd.read_csv(storage_file)
        styled_storage_systems = (
            df_storage.style
            .format(precision=2)  # Limitar a dos decimales en todas las columnas numéricas
            .applymap(color_status, subset=['STATUS'])  # Aplicar color solo en la columna "status"
            .applymap(color_readiness, subset=['READINESS'])  # Estilo en 'READINESS'            
        )
        html_storage_systems = styled_storage_systems.to_html(table_attributes='class="data-table"')
  
    return html_health, html_health_system, html_job_group, html_job_rate, html_storage_systems

# El resto del HTML con atributos adicionales para control de altura
html_body = f"""
<html xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" xmlns:m="http://schemas.microsoft.com/office/2004/12/omml" xmlns="http://www.w3.org/TR/REC-html40">
    <head>
        {table_style}
        <!--[if gte mso 9]>
        <xml>
            <o:OfficeDocumentSettings>
                <o:AllowPNG/>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
        <![endif]-->
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif;">
        <div style="width: 100%; max-width: 1200px; margin: 0 auto;">
            <h2 style="font-family: Arial, sans-serif; color: #0044cc; margin-bottom: 10px;">DAILY CHECK PPDM</h2>
"""

# Iterar sobre los sistemas y hostnames
for system, system_config in config["systems"].items():

    # Verificar si el sistema es PPDM
    if system != "PPDM":
        continue  # Saltar a la siguiente iteración si no es PPDM
    
    for instance_config in system_config['instances']:
        hostname = instance_config["hostname"]
        
        # Load data
        html_health, html_health_system, html_job_group, html_job_rate, html_storage_systems = load_and_style_data(system, hostname, config)
        
        # Use table for layout with height attributes
        html_body += f"""
        <h3 style="font-family: Arial, sans-serif; color: #0066cc; margin: 10px 0;">Hostname: {hostname}</h3>
        <table cellpadding="0" cellspacing="0" border="0" width="100%" style="table-layout: fixed;">
            <tr>
                <td class="table-cell">
                    <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333; margin: 5px 0;">
                        Job Group Rate
                    </p>
                    {html_job_rate}                    
                    <p style="font-family: Arial, sans-serif; color: #333; margin: 5px 0;">
                        Categories of Job Groups Included: "PROTECT", "REPLICATE", "RESTORE", "CLOUD_TIER", "INDEX"
                    </p>           
                    <hr style="border: 0; height: 1px; background: #fff; margin: 10px 0;">                                        
                    <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333; margin: 5px 0;">
                        Jobs | Protection - Last 24 hours
                    </p>
                    {html_job_group}
                </td>
                <td class="table-cell">
                    <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333; margin: 5px 0;">
                        HEALTH SYSTEM
                    </p>
                    {html_health_system}
                    <hr style="border: 0; height: 10px; background: #fff; margin: 10px 0;">
                    <p style="font-family: Arial, sans-serif; color: #333; margin: 5px 0;">
                    </p>
                    <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333; margin: 5px 0;">
                        Health Categories
                    </p>
                    {html_health}
                </td>
                <td class="table-cell">
                    <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333; margin: 5px 0;">
                        Storage Systems
                    </p>
                    {html_storage_systems}
                </td>
            </tr>
        </table>
        """

html_body += """
        </div>
    </body>
</html>
"""

# Guardar el HTML en un archivo temporal y abrirlo en el navegador
with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
    f.write(html_body)
    temp_file_path = f.name

# Abrir el archivo en el navegador predeterminado
webbrowser.open(f'file://{temp_file_path}')


# Generar la fecha actual en formato YYYYMMDD
# dateToday = datetime.now().strftime("%Y%m%d")

# Configurar los parámetros del correo
customerName = config['customer']['name']
sender_email = config['customer']['senderEmail']
receiver_email = config['customer']['receiverEmail']
subject = f"AUTOMATED_{customerName}_{dateToday}_Daily_Check"
smtp_server = config['customer']['smtpServer']
smtp_port = config['customer']['smtpPort']

# Crear el mensaje MIME
message = MIMEMultipart("alternative")
message["Subject"] = subject
message["From"] = sender_email
message["To"] = receiver_email

# Agregar el contenido HTML al mensaje
html_part = MIMEText(html_body, "html")
message.attach(html_part)

#Enviar el correo sin autenticación
# with smtplib.SMTP(smtp_server, smtp_port) as server:
   # server.sendmail(sender_email, receiver_email, message.as_string())