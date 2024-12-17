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
from email.mime.application import MIMEApplication
import socket


def color_severity(val):
    if val == 'LOW':
        return 'background-color: #ffd9b3 !important; color: #b35900 !important'  # Naranja pastel
    elif val == 'MEDIUM':
        return 'background-color: #fff2b3 !important; color: #7a7a00 !important'  # Amarillo pastel
    elif val == 'HIGH':
        return 'background-color: #f7b3b3 !important; color: #a10000 !important'  # Rojo pastel
    return ''


table_style = """
<style>
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
    .section-container {
        width: 100% !important;
        margin-bottom: 20px !important;
    }
</style>
"""


def load_and_style_health_events(system, hostname, config):
    base_path = config['basePath']
    csv_relative_path = config['csvPath']
    csvPath = os.path.join(base_path, csv_relative_path)
    csv_files = config['systems'][system]['files']['csv']


    health_event_files = glob.glob(f"{csvPath}/{system}-{hostname}-{csv_files['healthEvents']}")
    
    html_health_events = ""
    
    for health_event_file in health_event_files:
        df_health_events = pd.read_csv(health_event_file)
        styled_health_events = df_health_events.style.applymap(color_severity, subset=['severity'])
        html_health_events += styled_health_events.to_html(classes='data-table')
    
    return html_health_events


def PPDM_create_daily_investigation_report(config_path):
    with open(config_path) as config_file:
        config = json.load(config_file)


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
                <h2 style="font-family: Arial, sans-serif; color: #0044cc; margin-bottom: 10px;">DAILY INVESTIGATION PPDM - Health Events</h2>
    """


    for system, system_config in config["systems"].items():
        if system != "PPDM":
            continue
        
        for instance_config in system_config['instances']:
            hostname = instance_config["hostname"]
            html_health_events = load_and_style_health_events(system, hostname, config)
            
            html_body += f"""
            <div class="section-container">
                <h3 style="font-family: Arial, sans-serif; color: #0066cc; margin: 10px 0;">Hostname: {hostname}</h3>
                
                <div style="margin-bottom: 15px;">
                    <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333; margin: 5px 0;">
                        Health Events
                    </p>
                    {html_health_events}
                </div>
            </div>
            """


    html_body += """
            </div>
        </body>
    </html>
    """


    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
        f.write(html_body)
        temp_file_path = f.name


    webbrowser.open(f'file://{temp_file_path}')


    dateToday = datetime.now().strftime("%Y%m%d")
    customerName = config['customer']['name']
    sender_email = config['customer']['senderEmail']
    receiver_email = config['customer']['receiverEmail']
    subject = f"AUTOMATED_{customerName}_{dateToday}_Daily_Check_Investigation"
    smtp_server = config['customer']['smtpServer']
    smtp_port = config['customer']['smtpPort']


    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email


    html_part = MIMEText(html_body, "html")
    message.attach(html_part)


    xlsx_directory = os.path.join(config["basePath"], config['xlsxPath'])
    xlsx_pattern = f"{datetime.now().strftime('%Y%m%d')}-PPDM-*-activities_no_ok_summary.xlsx"


    xlsx_files = glob.glob(os.path.join(xlsx_directory, xlsx_pattern))


    print("xlsx_directory: ", xlsx_directory)
    print("xlsx_pattern: ", xlsx_pattern)
    print("xlsx_files: ", xlsx_files)


    if xlsx_files:
        for file in xlsx_files:
            with open(file, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(file))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(file)}"'
                message.attach(part)
    else:
        print("No se encontraron archivos .xlsx para adjuntar.")


    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.sendmail(sender_email, receiver_email, message.as_string())
        print("Email sent successfully")
    except (socket.gaierror, socket.error) as e:
        print(f"Failed to connect to the SMTP server: {e}")
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")


if __name__ == "__main__":
    PPDM_create_daily_investigation_report("config_encrypted.json")
