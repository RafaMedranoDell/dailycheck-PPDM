import pandas as pd
import webbrowser
import tempfile
import json
import glob
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Leer el archivo de configuración
with open("config_encrypted.json") as config_file:
    config = json.load(config_file)

# Definir la función para colorear las celdas en la columna "severity" con tonos pastel
def color_severity(val):
    if val == 'LOW':
        return 'background-color: #ffd9b3 !important; color: #b35900 !important'
    elif val == 'MEDIUM':
        return 'background-color: #fff2b3 !important; color: #7a7a00 !important'
    elif val == 'HIGH':
        return 'background-color: #f7b3b3 !important; color: #a10000 !important'
    return ''

# CSS mejorado para compatibilidad con Outlook
table_style = """
<style>
    /* Reset de estilos para Outlook */
    table {
        border-collapse: collapse !important;
        width: 100% !important;
        margin-bottom: 20px !important;
        mso-table-lspace: 0pt !important;
        mso-table-rspace: 0pt !important;
        font-family: Arial, sans-serif !important;
        font-size: 11px !important;
    }
    th, td {
        border: 1px solid #ddd !important;
        padding: 2px 4px !important;
        text-align: left !important;
        font-size: 11px !important;
        mso-line-height-rule: exactly !important;
        line-height: 1.2 !important;
        height: 16px !important;
    }
    th {
        background-color: #cccccc !important;
        color: white !important;
        font-weight: bold !important;
        height: 18px !important;
    }
    tr {
        height: 16px !important;
    }
    tr:nth-child(even) {
        background-color: #f2f2f2 !important;
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
    /* Contenedor de tabla para layout */
    .section-container {
        width: 100% !important;
        margin-bottom: 20px !important;
    }
</style>
"""

# Función para cargar y aplicar estilo a los datos de Health Events
def load_and_style_health_events(system, hostname, config):
    base_path = config.get('basePath', '')
    csv_files = config['systems'][system]['files']['csv']
    health_event_files = glob.glob(f"{base_path}/{system}-{hostname}-{csv_files['healthEvents']}")
    
    html_health_events = ""
    
    for health_event_file in health_event_files:
        df_health_events = pd.read_csv(health_event_file)
        styled_health_events = df_health_events.style.applymap(color_severity, subset=['severity'])
        html_health_events += styled_health_events.to_html(classes='data-table')
    
    return html_health_events


# Función para cargar y aplicar estilo a los datos de Summary Jobs Skipped
def load_and_style_summary_jobs_skipped(system, hostname, config):
    base_path = config.get('basePath', '')
    csv_files = config['systems'][system]['files']['csv']
    summary_jobs_skipped_files = glob.glob(f"{base_path}/{system}-{hostname}-{csv_files['summaryJobsSkipped']}")
    
    html_summary_jobs_skipped = ""
    
    for summary_jobs_skipped_file in summary_jobs_skipped_files:
        df_summary_jobs_skipped = pd.read_csv(summary_jobs_skipped_file)
        html_summary_jobs_skipped += df_summary_jobs_skipped.to_html(classes='data-table')
    
    return html_summary_jobs_skipped


# Función para cargar y aplicar estilo a los datos de Unique Errors No Skipped
def load_and_style_unique_errors_no_skipped(system, hostname, config):
    base_path = config.get('basePath', '')
    csv_files = config['systems'][system]['files']['csv']
    unique_errors_no_skipped_files = glob.glob(f"{base_path}/{system}-{hostname}-{csv_files['uniqueErrorsNoSkipped']}")
    
    html_unique_errors_no_skipped = ""
    
    for unique_errors_no_skipped_file in unique_errors_no_skipped_files:
        df_unique_errors_no_skipped = pd.read_csv(unique_errors_no_skipped_file)
        html_unique_errors_no_skipped += df_unique_errors_no_skipped.to_html(classes='data-table')
    
    return html_unique_errors_no_skipped

# HTML mejorado con soporte para Outlook
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
            <h2 style="font-family: Arial, sans-serif; color: #0044cc; margin-bottom: 10px;">DAILYCHECK PPDM - Health Events</h2>
"""

# Iterar sobre los sistemas y hostnames
for system, system_config in config["systems"].items():
    for instance_config in system_config['instances']:
        hostname = instance_config["hostname"]
        
        # Cargar datos
        html_health_events = load_and_style_health_events(system, hostname, config)
        html_summary_jobs_skipped = load_and_style_summary_jobs_skipped(system, hostname, config)
        html_unique_errors_no_skipped = load_and_style_unique_errors_no_skipped(system, hostname, config)
        
        html_body += f"""
        <div class="section-container">
            <h3 style="font-family: Arial, sans-serif; color: #0066cc; margin: 10px 0;">Hostname: {hostname}</h3>
            
            <div style="margin-bottom: 15px;">
                <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333; margin: 5px 0;">
                    Health Events
                </p>
                {html_health_events}
            </div>

            <div style="margin-bottom: 15px;">
                <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333; margin: 5px 0;">
                    Summary Jobs Skipped
                </p>
                {html_summary_jobs_skipped}
            </div>

            <div style="margin-bottom: 15px;">
                <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333; margin: 5px 0;">
                    Unique Errors No Skipped
                </p>
                {html_unique_errors_no_skipped}
            </div>
        </div>
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

# # Configurar los parámetros del correo
# sender_email = "DailycheckHDV@hdv.com"
# receiver_email = "dell.residencies@dell.com"
# subject = "DAILYCHECK "
# smtp_server = "esa-relay.rsvgnw.local"
# smtp_port = 25

# # Crear el mensaje MIME
# message = MIMEMultipart("alternative")
# message["Subject"] = subject
# message["From"] = sender_email
# message["To"] = receiver_email

# # Agregar el contenido HTML al mensaje
# html_part = MIMEText(html_body, "html")
# message.attach(html_part)

# # Enviar el correo sin autenticación
# with smtplib.SMTP(smtp_server, smtp_port) as server:
#     server.sendmail(sender_email, receiver_email, message.as_string())