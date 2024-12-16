import modules.functions as fn
import pandas as pd
import json
import csv
import os
import glob


#Definicion de Variables
config_file = "config_encrypted.json"


def save_dataframe_to_csv(df, file_path):
    """Saves the DataFrame to a CSV file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_csv(file_path, index=False, quoting=csv.QUOTE_ALL, escapechar='\\')
    
    if os.path.exists(file_path):  # Cambiar 'csv_path' a 'file_path'
        print(f'    Archivo guardado exitosamente: {file_path}')
    else:
        print(f'    Error al guardar el archivo: {file_path}')


def process_if_not_empty(file_path, process_function, system, instance, config, csvPath):
    """Checks if the JSON data is empty; if not, converts it to a DataFrame and processes it."""
    data = fn.load_json_file(file_path)
    if not data:
        print(f'El archivo "{file_path}" está vacío o no contiene datos válidos. Se omitirá.')
        return
    
    df = pd.DataFrame(data)
    process_function(df, system, instance, config, csvPath)


def create_health_summary(df):
    """Crear un resumen de métricas de salud."""
    health_categories = ['CONFIGURATION', 'DATA_PROTECTION', 'PERFORMANCE', 'COMPONENTS', 'CAPACITY']
    
    # Plantilla base con categorías de salud
    df_health_template = pd.DataFrame({
        'healthCategory': health_categories,
        'Score': 0,
        'Issues': 0
    })

    # Agrupar y calcular métricas
    df_grouped_health_metrics = df.groupby('healthCategory').agg({
        'scoreDeduction': 'max',
        'healthCategory': 'count'
    }).rename(columns={'scoreDeduction': 'Score', 'healthCategory': 'Issues'})
    df_grouped_health_metrics['Score'] = -df_grouped_health_metrics['Score']

    # Completar resumen de salud
    df_health_summary = pd.merge(
        df_health_template,
        df_grouped_health_metrics,
        on='healthCategory',
        how='outer',
        suffixes=('_template', '_grouped')
    )
    df_health_summary['Score'] = df_health_summary['Score_grouped'].fillna(df_health_summary['Score_template']).astype(int)
    df_health_summary['Issues'] = df_health_summary['Issues_grouped'].fillna(df_health_summary['Issues_template']).astype(int)
    df_health_summary = df_health_summary[['healthCategory', 'Issues', 'Score']]

    # Renombrar y reemplazar valores
    df_health_summary = df_health_summary.rename(columns={'healthCategory': 'CATEGORY'})
    category_mapping = {
        'CONFIGURATION': 'Configuration',
        'DATA_PROTECTION': 'Data Protection',
        'PERFORMANCE': 'Performance',
        'COMPONENTS': 'Components',
        'CAPACITY': 'Capacity'
    }
    df_health_summary['CATEGORY'] = df_health_summary['CATEGORY'].replace(category_mapping)
    
    return df_health_summary


def create_health_system_status(df_health_summary):
    """Crear el estado general del sistema."""
    lowest_health_score = df_health_summary['Score'].min()
    normalized_system_score = 100 + lowest_health_score
    total_issues_count = df_health_summary['Issues'].sum()

    # Determinar estado basado en el puntaje
    if normalized_system_score > 95:
        system_status = "GOOD"
    elif 71 < normalized_system_score <= 94:
        system_status = "FAIR"
    else:
        system_status = "POOR"

    # Crear DataFrame con el estado
    df_system_status = pd.DataFrame([{
        'TotalIssuesCount': total_issues_count,
        'SystemScore': normalized_system_score,
        'STATUS': system_status
    }])

    return df_system_status


def create_health_events(df):
    """Limpiar y transformar registros de eventos de salud."""
    return df.replace(r'\n', '|||', regex=True)


def process_health(df, system, instance, config, csvPath):
    """Procesar datos de salud y guardar los resultados en CSV."""
    # Crear los DataFrames requeridos
    df_health_summary = create_health_summary(df)
    df_system_status = create_health_system_status(df_health_summary)
    df_event_logs = create_health_events(df)

    # Guardar los DataFrames en archivos CSV
    csv_files = config['systems'][system]['files']['csv']
    
    fn.save_dataframe_to_csv(df_health_summary, os.path.join(csvPath, f'{system}-{instance}-{csv_files["healthSummary"]}'))
    fn.save_dataframe_to_csv(df_event_logs, os.path.join(csvPath, f'{system}-{instance}-{csv_files["healthEvents"]}'))
    fn.save_dataframe_to_csv(df_system_status, os.path.join(csvPath, f'{system}-{instance}-{csv_files["healthSystemStatus"]}'))


def summarize_job_group_status(df_filtered):
    """Crear un resumen de actividades por estado de resultado."""
    possible_statuses = ['OK', 'FAILED', 'OK_WITH_ERRORS', 'CANCELED', 'SKIPPED', 'UNKNOWN']
    df_all_statuses = pd.DataFrame({'result_status': possible_statuses, 'Count': 0})

    # Contar ocurrencias de cada estado de resultado
    df_status_counts = df_filtered['result.status'].value_counts().reset_index()
    df_status_counts.columns = ['result_status', 'Count']

    # Completar con posibles estados faltantes
    df_job_group_summary = pd.merge(
        df_all_statuses,
        df_status_counts,
        on='result_status',
        how='outer'
    )
    # Completar valores nulos con ceros
    df_job_group_summary['Count'] = df_job_group_summary['Count_y'].combine_first(df_job_group_summary['Count_x']).astype(int)
    df_job_group_summary = df_job_group_summary[['result_status', 'Count']]

    # Mapear los estados de resultado a nombres amigables
    status_mapping = {
        'OK': 'Successful',
        'FAILED': 'Failed',
        'OK_WITH_ERRORS': 'Completed with Exceptions',
        'CANCELED': 'Canceled',
        'SKIPPED': 'Skipped',
        'UNKNOWN': 'Unknown'
    }
    df_job_group_summary['result_status'] = df_job_group_summary['result_status'].replace(status_mapping)

    # Renombrar columnas
    df_job_group_summary = df_job_group_summary.rename(columns={'result_status': 'STATUS'})

    return df_job_group_summary


def calculate_job_group_rate(df_job_group_summary):
    """Calcular el total y el porcentaje de éxito de los grupos de trabajos."""
    total_jobs = df_job_group_summary['Count'].sum()
    successful_jobs = df_job_group_summary.loc[df_job_group_summary['STATUS'] == 'Successful', 'Count'].sum()
    success_rate = round((successful_jobs / total_jobs) * 100, 2) if total_jobs > 0 else 0

    df_job_group_rate = pd.DataFrame([[total_jobs, success_rate]], columns=['Total Job Groups', 'Rate (%)'])
    return df_job_group_rate


def process_job_group_activities(df, system, instance, config, csv_path):
    """Procesar actividades del grupo de trabajos y guardar resultados en CSV."""
    # Filtrar el DataFrame para categorías relevantes
    relevant_categories = ['CLOUD_TIER', 'INDEX', 'PROTECT', 'REPLICATE', 'RESTORE']
    df_filtered_jobs = df[df['category'].isin(relevant_categories)]

    # Crear los DataFrames de resumen y tasa de éxito
    df_job_group_summary = summarize_job_group_status(df_filtered_jobs)
    df_job_group_rate = calculate_job_group_rate(df_job_group_summary)

    # Obtener rutas de archivos desde la configuración
    csv_files = config['systems'][system]['files']['csv']

    # Guardar los DataFrames en archivos CSV
    fn.save_dataframe_to_csv(df_job_group_summary, os.path.join(csv_path, f'{system}-{instance}-{csv_files["jobgroupSummary"]}'))
    fn.save_dataframe_to_csv(df_job_group_rate, os.path.join(csv_path, f'{system}-{instance}-{csv_files["jobgroupRate"]}'))


def generate_activities_no_ok_summary(df):

    df = df.fillna("(empty)")

        # Calcular el número de ocurrencias por combinación de columnas clave
    df_error_occurrences = df.groupby([
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code', 
        'host.name', 
        'asset.name',
        'result.error.reason'
    ]).size().reset_index(name='occurrences')

    # Seleccionar columnas relevantes para el análisis
    relevant_columns = [
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code',
        'activityInitiatedType', 
        'host.name', 
        'asset.name', 
        'result.error.reason', 
        'result.error.extendedReason', 
        'result.error.detailedDescription', 
        'result.error.remediation'
    ]
    df_relevant_data = df[relevant_columns]

    # Crear un DataFrame con errores únicos basado en combinaciones clave
    df_unique_errors = df_relevant_data.drop_duplicates(subset=[
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code', 
        'host.name', 
        'asset.name',
        'result.error.reason'
    ])

    # Unir las ocurrencias con el DataFrame de errores únicos
    df_final_summary = df_unique_errors.merge(
        df_error_occurrences, 
        on=[
            'category', 
            'protectionPolicy.name', 
            'result.status', 
            'result.error.code', 
            'host.name', 
            'asset.name',
            'result.error.reason'
        ]
    )

    # Reorganizar y ordenar las columnas para el informe final
    final_columns_order = [
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code',
        'activityInitiatedType',
        'occurrences',
        'host.name', 
        'asset.name', 
        'result.error.reason', 
        'result.error.extendedReason', 
        'result.error.detailedDescription', 
        'result.error.remediation'
    ]
    return df_final_summary[final_columns_order].sort_values([
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code', 
        'host.name', 
        'asset.name',
        'result.error.reason'
    ])


def process_activities_no_ok(df, system, instance, config, csv_path):

    # Generar tabla de errores únicos 
    df_activities_no_ok_summary = generate_activities_no_ok_summary(df)

    # Reemplazar "\n" por "|||" en todo el DataFrame
    df_activities_no_ok_summary = df_activities_no_ok_summary.replace(r'\n', '  ..  ', regex=True)

    # Obtener rutas de archivo desde la configuración
    csv_files = config['systems'][system]['files']['csv']

    # Guardar los DataFrames en CSV
    save_dataframe_to_csv(df_activities_no_ok_summary, os.path.join(csv_path, f'{system}-{instance}-{csv_files["activitiesNoOkSummary"]}'))
    #save_dataframe_to_csv(df_summary_jobs_skipped, os.path.join(csv_path, f'{system}-{instance}-{csv_files["summaryJobsSkipped"]}'))


def process_storage_systems(df, system, instance, config, csvPath):
    """Process storage systems information from JSON data."""
    
    # Filter for DATA_DOMAIN_SYSTEM entries
    df_storage_systems = df[df['type'] == 'DATA_DOMAIN_SYSTEM']
    
    # Prepare a list to store processed rows
    processed_rows = []
    
    # Iterate through the filtered DataFrame
    for _, row in df_storage_systems.iterrows():
        # Extract base information
        name = row.get('name', '')
        readiness = row.get('readiness', '').lower()
        
        # Check if dataDomain and capacities exist
        capacities = row.get('details', {}).get('dataDomain', {}).get('capacities', [])
        
        # Process each capacity block
        for capacity in capacities:
            processed_rows.append({
                'NAME': name,
                'READINESS': readiness,
                'TIER': capacity.get('type', ''),
                # 'SIZE': capacity.get('totalPhysicalSize', ''),
                # 'USED': capacity.get('totalPhysicalUsed', ''),
                'PERCENT USED': f"{capacity.get('percentUsed', 0):.2f}",  # Format to 2 decimal places
                'STATUS': capacity.get('capacityStatus', '')
            })
    
    # Create DataFrame from processed rows
    df_storage_systems_output = pd.DataFrame(processed_rows)   
    df_storage_systems_output = df_storage_systems_output.sort_values(by=['NAME', 'TIER'])

    # Get file paths from config
    csv_files = config['systems'][system]['files']['csv']
    
    # Save to CSV
    save_dataframe_to_csv(df_storage_systems_output, os.path.join(csvPath, f'{system}-{instance}-{csv_files["storageSystems"]}'))


def main():
    """Main function that coordinates all tasks."""
    # Load configuration
    with open("config_encrypted.json", "r") as config_file:
        config = json.load(config_file)

    # Obtener la ruta base y la ruta de los ficheros JSON
    base_path = config["basePath"]  # Obtener la ruta base desde el archivo de configuración
    json_relative_path = config["jsonPath"]
    csv_relative_path = config["csvPath"]
    jsonPath = os.path.join(base_path, json_relative_path)
    csvPath = os.path.join(base_path, csv_relative_path)
    
    for system, system_config in config["systems"].items():
        if system != "PPDM":
            continue  # Saltar este sistema si no es "PPDM"

       
        json_files = system_config['files']['json']
        
        for instance_config in system_config['instances']:
            hostname = instance_config["hostname"]
            print('------------------------')
            print(f'PROCESANDO SISTEMAS "{system}"')
            print('------------------------')

            print('------------------------')
            print(f'Procesando información de : "{hostname}"')
            print('------------------------')

            # Process Health Issues
            health_files = glob.glob(os.path.join(jsonPath, f'{system}-{hostname}-{json_files["systemHealthIssues"]}')) 
            if not health_files:
                print(f'  No existe el fichero "{system}-{hostname}-{json_files["systemHealthIssues"]}"')           
            else:
                print(f'  {hostname}: Procesando fichero: {health_files}')
                for file_path in health_files:
                    process_if_not_empty(file_path, process_health, system, hostname, config, csvPath)
            
            # Process Job Group Activities
            job_files = glob.glob(os.path.join(jsonPath, f'{system}-{hostname}-{json_files["jobGroupActivitiesSummary"]}'))
            if not job_files:
                print(f'  No existe el fichero "{system}-{hostname}-{json_files["jobGroupActivitiesSummary"]}"')
            else:
                print(f'  {hostname}: Procesando fichero: {job_files}')
                for file_path in job_files:
                    process_if_not_empty(file_path, process_job_group_activities, system, hostname, config, csvPath)
            
            # Process Activities No OK
            activities_files = glob.glob(os.path.join(jsonPath, f'{system}-{hostname}-{json_files["activitiesNotOK"]}'))            
            if not activities_files:
                print(f'  No existe el fichero "{system}-{hostname}-{json_files["activitiesNotOK"]}"')
            else:
                print(f'  {hostname}: Procesando fichero: {activities_files}')
                for file_path in activities_files:
                    process_if_not_empty(file_path, process_activities_no_ok, system, hostname, config, csvPath)

            # Process Storage Systems
            storage_files = glob.glob(os.path.join(jsonPath, f'{system}-{hostname}-{json_files["storageSystems"]}'))
            if not storage_files:
                print(f'  No existe el fichero "{system}-{hostname}-{json_files["storageSystems"]}"')
            else:
                print(f'  {hostname}: Procesando fichero: {storage_files}')
                for file_path in storage_files:
                    process_if_not_empty(file_path, process_storage_systems, system, hostname, config, csvPath)
            
            print('------------------------')



if __name__ == '__main__':
    main()