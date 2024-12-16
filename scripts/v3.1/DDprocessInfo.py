import modules.functions as fn
import os
import glob
import pandas as pd


#Definicion de Variables
config_file = "config_encrypted.json"


def process_if_not_empty(file_path, process_function, system, instance, config, csvPath):
    """Checks if the JSON data is empty; if not, converts it to a DataFrame and processes it."""
    data = fn.load_json_file(file_path)
    if not data:
        print(f'El archivo "{file_path}" está vacío o no contiene datos válidos. Se omitirá.')
        return
    
    df = pd.DataFrame(data)
    process_function(df, system, instance, config, csvPath)


def process_alerts_severity_summary(df, system, instance, config, csvPath):

    df_alerts_severity_summary = df['severity'].value_counts().reset_index()
    df_alerts_severity_summary.columns = ['severity', 'NumAlerts']

    # Get file paths from config
    csv_files = config['systems'][system]['files']['csv']

    fn.save_dataframe_to_csv(df_alerts_severity_summary, os.path.join(csvPath, f'{system}-{instance}-{csv_files["alertSeveritySummary"]}'))


def process_services_status(df, system, instance, config, csvPath):

    # Get file paths from config
    csv_files = config['systems'][system]['files']['csv']

    fn.save_dataframe_to_csv(df, os.path.join(csvPath, f'{system}-{instance}-{csv_files["servicesStatus"]}'))


def process_alerts_by_class(df, system, instance, config, csvPath):

    # Posibles clases de alertas
    possible_classAlerts = [
        "capacity", "Cifs", "Cloud", "Cluster", "dataAvailability", 
        "Environment", "Filesystem", "Firmware", "ha", "HardwareFailure", 
        "infrastructure", "Network", "Replication", 
        "Security",  "Syslog", "SystemMaintenance", "Storage"
    ]

    # Contar las ocurrencias de cada valor en 'class' en el DataFrame original
    class_counts = df['class'].value_counts()

    # Crear un DataFrame asegurando que todos los valores posibles de 'class' estén incluidos
    df_num_alerts_by_class = pd.DataFrame(possible_classAlerts, columns=['class'])
    df_num_alerts_by_class['numAlerts'] = df_num_alerts_by_class['class'].map(class_counts).fillna(0).astype(int)

    # Get file paths from config
    csv_files = config['systems'][system]['files']['csv']

    fn.save_dataframe_to_csv(df_num_alerts_by_class, os.path.join(csvPath, f'{system}-{instance}-{csv_files["alertsByClass"]}'))


def main():
    """Main function that coordinates all tasks."""
    # Load configuration
    config = fn.load_json_file(config_file)

    # Obtener la ruta base y la ruta de los ficheros JSON
    base_path = config["basePath"]  # Obtener la ruta base desde el archivo de configuración
    json_relative_path = config["jsonPath"]
    csv_relative_path = config["csvPath"]
    jsonPath = os.path.join(base_path, json_relative_path)
    csvPath = os.path.join(base_path, csv_relative_path)

    for system, system_config in config["systems"].items():

        # Verificar si el sistema es PPDM
        if system != "DD":
            continue  # Saltar a la siguiente iteración si no es PPDM

        print(f'PROCESANDO SISTEMAS "{system}"')
        print('------------------------')

        json_files = system_config['files']['json']
        
        for instance_config in system_config['instances']:
            hostname = instance_config["hostname"]

            print(f'Procesando información de : "{hostname}"')

            # Process Active Alerts
            activeAlerts_file = glob.glob(os.path.join(jsonPath, f'{system}-{hostname}-{json_files["activeAlerts"]}')) 
            if not activeAlerts_file:
                print(f'  No existe el fichero "{system}-{hostname}-{json_files["activeAlerts"]}"')           
            else:
                print(f'  {hostname}: Procesando fichero: {activeAlerts_file}')
                for file_path in activeAlerts_file:
                    process_if_not_empty(file_path, process_alerts_severity_summary, system, hostname, config, csvPath)
                    process_if_not_empty(file_path, process_alerts_by_class, system, hostname, config, csvPath)

            # Process Status of Service 
            services_file = glob.glob(os.path.join(jsonPath, f'{system}-{hostname}-{json_files["services"]}')) 
            if not services_file:
                print(f'  No existe el fichero "{system}-{hostname}-{json_files["services"]}"')           
            else:
                print(f'  {hostname}: Procesando fichero: {services_file}')
                for file_path in services_file:
                    process_if_not_empty(file_path, process_services_status, system, hostname, config, csvPath)



