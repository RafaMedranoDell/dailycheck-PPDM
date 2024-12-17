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

def color_score(val):
    if val == 0:
        return 'background-color: #b3e6b3; color: #2d6a2d'  # Verde pastel
    elif 0 > val >= -20:
        return 'background-color: #fff2b3; color: #7a7a00'  # Amarillo pastel
    elif val < -20:
        return 'background-color: #f7b3b3; color: #a10000'  # Rojo pastel
    return ''

def color_failed(row):
    if row['STATUS'] == 'Failed' and row['Count'] != 0:
        return ['background-color: #f7b3b3; color: #a10000'] * len(row)
    return [''] * len(row)

def color_status(val):
    if val == "GOOD":
        return 'background-color: #b3e6b3; color: #2d6a2d'  # Verde pastel
    elif val == "FAIR":
        return 'background-color: #fff2b3; color: #7a7a00'  # Amarillo pastel
    elif val == "POOR":
        return 'background-color: #f7b3b3; color: #a10000'  # Rojo pastel
    return ''

def color_readiness(val): 
    if val == "ready": 
        return 'background-color: #b3e6b3; color: #2d6a2d'  # Verde pastel
    elif val == "migrating": 
        return 'background-color: #fff2b3; color: #7a7a00'  # Amarillo pastel
    elif val == "not_ready": 
        return 'background-color: #f7b3b3; color: #a10000'  # Rojo pastel
    return ''

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

def color_health_status(val):
    if val == "GOOD":
        return 'background-color: #b3e6b3; color: #2d6a2d'  # Verde pastel
    elif val == "FAIR":
        return 'background-color: #fff2b3; color: #7a7a00'  # Amarillo pastel
    elif val == "POOR":
        return 'background-color: #f7b3b3; color: #a10000'  # Rojo pastel
    return ''

table_style = """
<style>
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
        padding: 2px 4px !important;
        text-align: left !important;
        font-family: Arial, sans-serif !important;
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
    .table-cell {
        width: 48% !important;
        padding: 5px !important;
        vertical-align: top !important;
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
</style>
"""

def load_and_style_data(system, hostname, config):
    base_path = config['basePath']
    csv_relative_path = config['csvPath']
    csvPath= os.path.join(base_path, csv_relative_path)
    csv_files = config['systems'][system]['files']['csv']

    health_categories_files = glob.glob(f"{csvPath}/{system}-{hostname}-{csv_files['healthSummary']}")
    health_system_status_files = glob.glob(f"{csvPath}/{system}-{hostname}-{csv_files['healthSystemStatus']}")
    job_files = glob.glob(f"{csvPath}/{system}-{hostname}-{csv_files['jobgroupSummary']}")
    rate_files = glob.glob(f"{csvPath}/{system}-{hostname}-{csv_files['jobgroupRate']}")
    storage_files = glob.glob(f"{csvPath}/{system}-{hostname}-{csv_files['storageSystems']}")

    html_health_categories = ""
    html_health_system_status = ""
    html_job_group = ""
    html_job_rate = ""
    html_storage_systems = ""

    for health_categories_file in health_categories_files:
        df_health = pd.read_csv(health_categories_file)
        styled_health = df_health.style.applymap(color_score, subset=['Score'])
        html_health_categories = styled_health.to_html(table_attributes='class="data-table"')

    for health_system_status_file in health_system_status_files:
        df_health_system = pd.read_csv(health_system_status_file)
        styled_health_system = df_health_system.style.applymap(color_health_status, subset=['STATUS'])
        html_health_system_status = styled_health_system.to_html(table_attributes='class="data-table"')

    for job_file in job_files:
        df_job_group = pd.read_csv(job_file)
        styled_job_group = df_job_group.style.apply(color_failed, axis=1)
        html_job_group = styled_job_group.to_html(table_attributes='class="data-table"')

    for rate_file in rate_files:
        df_rate = pd.read_csv(rate_file)
        df_rate["Rate (%)"] = pd.to_numeric(df_rate["Rate (%)"], errors="coerce")
        styled_job_rate = (
            df_rate.style
            .set_table_attributes('class="data-table"')
            .applymap(color_rate, subset=["Rate (%)"])
            .format({"Rate (%)": "{:.2f}"})
        )
        html_job_rate = styled_job_rate.to_html()

    for storage_file in storage_files:
        df_storage = pd.read_csv(storage_file)
        styled_storage_systems = (
            df_storage.style
            .format(precision=2)
            .applymap(color_status, subset=['STATUS'])
            .applymap(color_readiness, subset=['READINESS'])
        )
        html_storage_systems = styled_storage_systems.to_html(table_attributes='class="data-table"')

    return html_health_categories, html_health_system_status, html_job_group, html_job_rate, html_storage_systems

def PPDM_create_daily_check_report(config_path):
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
                <h2 style="font-family: Arial, sans-serif; color: #0044cc; margin-bottom: 10px;">DAILY CHECK PPDM</h2>
    """

    for system, system_config in config["systems"].items():
        if system != "PPDM":
            continue
        
        for instance_config in system_config['instances']:
            hostname = instance_config["hostname"]
            html_health_categories, html_health_system_status, html_job_group, html_job_rate, html_storage_systems = load_and_style_data(system, hostname, config)
            
            html_body += f"""
            <h3 style="font-family: Arial, sans-serif; color: #0066cc; margin: 10px 0;">Hostname: {hostname}</h3>
            <table cellpadding="0" cellspacing="0" border="0" width="100%" style="table-layout: fixed;">
                <tr>
                    <td class="table-cell">
                        <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333; margin: 5px 0;">
                            JOB GROUPS RATE
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
                            HEALTY SYSTEM STATUS
                        </p>
                        {html_health_system_status}
                        <hr style="border: 0; height: 10px; background: #fff; margin: 10px 0;">
                        <p style="font-family: Arial, sans-serif; color: #333; margin: 5px 0;">
                        </p>  
                        <p style="font-family: Arial, sans-serif; font-weight: bold; text-decoration: underline; color: #333; margin: 5px 0;">
                            Health Categories
                        </p>
                        {html_health_categories}
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

    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
        f.write(html_body)
        temp_file_path = f.name

    webbrowser.open(f'file://{temp_file_path}')

    dateToday = datetime.now().strftime("%Y%m%d")
    customerName = config['customer']['name']
    sender_email = config['customer']['senderEmail']
    receiver_email = config['customer']['receiverEmail']
    subject = f"AUTOMATED_{customerName}_{dateToday}_Daily_Check"
    smtp_server = config['customer']['smtpServer']
    smtp_port = config['customer']['smtpPort']

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    html_part = MIMEText(html_body, "html")
    message.attach(html_part)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.sendmail(sender_email, receiver_email, message.as_string())

if __name__ == "__main__":
    create_daily_check_report("config_encrypted.json")