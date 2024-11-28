import pandas as pd
import webbrowser
import tempfile
import json
import glob


# Leer el archivo de configuración
with open("config.json") as config_file:
    config = json.load(config_file)


# Función para cargar y aplicar estilo a los datos de Health Events
def load_and_style_health_events(system, hostname):
    # Cargar el archivo basado en el hostname y system
    health_event_files = glob.glob(f"{system}-{hostname}-Health_events.csv")

    # Inicializar variable para almacenar el HTML
    html_health_events = ""

    # Procesar archivos de "Health Events"
    for health_event_file in health_event_files:
        df_health_events = pd.read_csv(health_event_file)
        styled_health_events = df_health_events.style.applymap(color_severity, subset=['severity'])
        html_health_events += styled_health_events.to_html()

    return html_health_events


# Función para cargar y aplicar estilo a los datos de Job Errors
def load_and_style_job_errors(system, hostname):
    job_error_files = glob.glob(f"{system}-{hostname}-jobErrors.csv")
    html_job_errors = ""

    for job_error_file in job_error_files:
        df_job_errors = pd.read_csv(job_error_file)
        html_job_errors += df_job_errors.to_html()

    return html_job_errors


# Definir la función para colorear las celdas en la columna "severity" con tonos pastel
def color_severity(val):
    if val == 'LOW':
        return 'background-color: #b3e6b3; color: #2d6a2d'  # Verde pastel
    elif val == 'MEDIUM':
        return 'background-color: #fff2b3; color: #7a7a00'  # Amarillo pastel
    elif val == 'HIGH':
        return 'background-color: #f7b3b3; color: #a10000'  # Rojo pastel
    return ''


# CSS personalizado para mejorar el estilo visual de las tablas
table_style = """
<style>
    table {
        border-collapse: collapse;
        width: 100%;
        font-family: Arial, sans-serif;
        margin-bottom: 20px;
        font-size: 11px;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
        font-size: 11px;
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
        <h2 style="font-family: Arial, sans-serif; color: #0044cc;">DAILYCHECK PPDM - Health Events</h2>
"""


# Iterar sobre los sistemas y hostnames en el archivo de configuración
for system, instances in config["systems"].items():
    for instance in instances:
        hostname = instance["hostname"]

        # Cargar y dar estilo a los datos para el hostname actual
        html_health_events = load_and_style_health_events(system, hostname)
        html_job_errors = load_and_style_job_errors(system, hostname)

        # Agregar la sección para el hostname actual
        html_body += f"""
        <h3 style="font-family: Arial, sans-serif; color: #0066cc;">Hostname: {hostname}</h3>
        
        <div style="padding: 10px;">
            <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333;">
                Health Events
            </p>
            {html_health_events}

            <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333;">
                Job Errors
            </p>
            {html_job_errors}
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


# Configurar los parámetros del correo
sender_email = "DailycheckHDV@hdv.com"
receiver_email = "dell.residencies@dell.com"
subject = "DAILYCHECK "
smtp_server = "esa-relay.rsvgnw.local"
smtp_port = 25

# Crear el mensaje MIME
message = MIMEMultipart("alternative")
message["Subject"] = subject
message["From"] = sender_email
message["To"] = receiver_email

# Agregar el contenido HTML al mensaje
html_part = MIMEText(html_body, "html")
message.attach(html_part)

# Enviar el correo sin autenticación
with smtplib.SMTP(smtp_server, smtp_port) as server:
    server.sendmail(sender_email, receiver_email, message.as_string())