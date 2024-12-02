import pandas as pd
import json
import csv
import os
import glob


def open_json_file(file_path):
    """Opens a JSON file and loads it into a dictionary."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def convert_to_dataframe(data):
    """Converts a dictionary to a pandas DataFrame."""
    df = pd.DataFrame(data)
    return df


def save_dataframe_to_csv(df, file_path):
    """Saves the DataFrame to a CSV file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_csv(file_path, index=False, quoting=csv.QUOTE_ALL, escapechar='\\')
    
    if os.path.exists(file_path):  # Cambiar 'csv_path' a 'file_path'
        print(f'    Archivo guardado exitosamente: {file_path}')
    else:
        print(f'    Error al guardar el archivo: {file_path}')



def process_health(df, system, instance, config, csvPath):
    """Process the Health DataFrame."""
    
    # Posibles categorías de salud
    possible_health_category = ['CONFIGURATION', 'DATA_PROTECTION', 'PERFORMANCE', 'COMPONENTS', 'CAPACITY']

    # Crear un DataFrame base con todas las categorías de salud y valores iniciales
    df_health_base = pd.DataFrame({
        'healthCategory': possible_health_category,
        'Score': 0,
        'Issues': 0
    })

    # Agrupar por healthCategory y sumar los scoreDeduction y contar los issues
    df_health_grouped = df.groupby('healthCategory').agg({
        'scoreDeduction': 'max',
        'healthCategory': 'count'
    }).rename(columns={'scoreDeduction': 'Score', 'healthCategory': 'Issues'})
    # Convertir los valores de Score a negativos
    df_health_grouped['Score'] = -df_health_grouped['Score']

    # Unir los datos para completar el DataFrame de salud
    df_health = pd.merge(df_health_base, df_health_grouped, on='healthCategory', how='outer', suffixes=('_base', '_grouped'))
    # Rellenar los valores NaN con los valores correspondientes en 'Score' y 'Issues'
    df_health['Score'] = df_health['Score_grouped'].fillna(df_health['Score_base']).astype(int)
    df_health['Issues'] = df_health['Issues_grouped'].fillna(df_health['Issues_base']).astype(int)
    df_health = df_health[['healthCategory', 'Issues', 'Score']]

    # Renombrar la columna 'healthCategory' a 'Health'
    df_health = df_health.rename(columns={'healthCategory': 'CATEGORY'})

    # Reemplazar los valores en la columna 'CATEGORY'
    category_mapping = {
        'CONFIGURATION': 'Configuration',
        'DATA_PROTECTION': 'Data Protection',
        'PERFORMANCE': 'Performance',
        'COMPONENTS': 'Components',
        'CAPACITY': 'Capacity'
    }
    df_health['CATEGORY'] = df_health['CATEGORY'].replace(category_mapping)

    ########## OBTENER TABLA df_health_system ###################
    # Calcular SystemScore: el menor valor en la columna 'Score'
    system_score = df_health['Score'].min()
    
    # Convertir el menor valor negativo en la escala de 100 (100 + SystemScore)
    system_score_converted = 100 + system_score
    
    # Calcular TotalNumIssues: suma total de los issues en la columna 'Issues'
    total_num_issues = df_health['Issues'].sum()
    
    # Calcular STATUS basado en SystemScore convertido
    if system_score_converted > 95:
        status = "GOOD"
    elif 71 < system_score_converted <= 94:
        status = "FAIR"
    else:
        status = "POOR"

    # Crear un DataFrame con los resultados
    df_status = pd.DataFrame([{
        'TotalNumIssues': total_num_issues,
        'SystemScore': system_score_converted,
        'STATUS': status        
    }])

    #############################################################


    # Reemplazar los valores en el DataFrame original de eventos de salud
    df_health_events = df.replace(r'\n', '|||', regex=True)

    # Get file paths from config
    csv_files = config['systems'][system]['files']['csv']

    save_dataframe_to_csv(df_health, os.path.join(csvPath, f'{system}-{instance}-{csv_files["dashboardHealh"]}'))
    save_dataframe_to_csv(df_health_events, os.path.join(csvPath, f'{system}-{instance}-{csv_files["healthEvents"]}'))
    save_dataframe_to_csv(df_status, os.path.join(csvPath, f'{system}-{instance}-{csv_files["healthSystem"]}'))



def process_job_group_activities(df, system, instance, config, csvPath):
    """Process the Dashboard Job Group Activities DataFrame."""


    # Filtrar el DataFrame por categorías específicas
    categories = ['CLOUD_TIER', 'INDEX', 'PROTECT', 'REPLICATE', 'RESTORE']
    df_filtered = df[df['category'].isin(categories)]

    # Create Job Groups DataFrame
    df_job_groups_summary = df_filtered['result.status'].value_counts().reset_index()
    df_job_groups_summary.columns = ['result.status', 'Num']

    # # Complete Job Groups DataFrame including all possible result.status
    possible_result_status = ['OK', 'FAILED', 'OK_WITH_ERRORS', 'CANCELED', 'SKIPPED', 'UNKNOWN']
    df_possible_result_status = pd.DataFrame({
        'result.status': possible_result_status,
        'Num': 0
    })

    # DataFrames, usando un merge outer para asegurarse de no perder datos
    df_job_groups_summary = pd.merge(df_possible_result_status, df_job_groups_summary, on='result.status', how='outer')
    # Llenar valores nulos en la columna Num
    df_job_groups_summary['Num'] = df_job_groups_summary['Num_y'].combine_first(df_job_groups_summary['Num_x']).astype(int)
    # Seleccionar solamente las columnas necesarias
    df_job_groups_summary = df_job_groups_summary[['result.status', 'Num']]

   # Reemplazar los valores de 'result.status' para adecuarlo al Dashboard de PPDM
    status_mapping = {
        'OK': 'Successful',
        'FAILED': 'Failed',
        'OK_WITH_ERRORS': 'Completed with Exceptions',
        'CANCELED': 'Canceled',
        'SKIPPED': 'Skipped',
        'UNKNOWN': 'Unknown'
    }

    df_job_groups_summary['result.status'] = df_job_groups_summary['result.status'].replace(status_mapping)

    # # Renombrar la columna 'result.status' a 'STATUS'
    df_job_groups_summary = df_job_groups_summary.rename(columns={'result.status': 'STATUS'})


    # Calcular TOTAL
    TOTAL = df_job_groups_summary['Num'].sum()
    
    # Calcular RATE de 'Successful'
    successful_count = df_job_groups_summary.loc[df_job_groups_summary['STATUS'] == 'Successful', 'Num'].sum()
    RATE = round((successful_count / TOTAL) * 100, 2) if TOTAL > 0 else 0

    print("TOTAL: ", TOTAL)
    print("RATE: ", RATE)

    df_job_groups_rate = pd.DataFrame([[TOTAL, RATE]], columns=['Total Job Groups', 'Rate (%)'])


    # Get file paths from config
    csv_files = config['systems'][system]['files']['csv']
    
    save_dataframe_to_csv(df_job_groups_summary, os.path.join(csvPath, f'{system}-{instance}-{csv_files["dashboardjobgroupActivities"]}'))
    save_dataframe_to_csv(df_job_groups_rate, os.path.join(csvPath, f'{system}-{instance}-{csv_files["dashboardJobGroupRate"]}'))



def process_activities_no_ok(df, system, instance, config, csvPath):

#################TABLA RESUMEN JOBS SKIPPED  #########################
    # Filtrar entradas con result.status igual a "SKIPPED"
    skipped_df = df[df['result.status'] == 'SKIPPED'].copy()
    
    # Reemplazar valores NaN con un string vacío para evitar errores
    skipped_df['host.name'] = skipped_df['host.name'].fillna('')
    
    # Realizar la agrupación en dos pasos para mayor claridad
    # Primero, crear un DataFrame con los nombres de hosts concatenados
    hosts_df = skipped_df.groupby([
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code'
    ])['host.name'].agg(
        host_names=lambda x: ' / '.join(sorted(set(x))) if any(x) else ''
    ).reset_index()
    
    # Luego, contar hosts y assets únicos
    counts_df = skipped_df.groupby([
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code'
    ]).agg({
        'host.name': lambda x: len(set(x.dropna())),
        'asset.name': lambda x: len(set(x.dropna()))
    }).reset_index()
    
    # Renombrar columnas de counts_df
    counts_df.columns = [
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code', 
        'num.hosts', 
        'num.assets'
    ]
    
    # Combinar los DataFrames
    final_df = hosts_df.merge(counts_df, on=[
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code'
    ])
    
    # Reordenar columnas para asegurar el orden correcto
    final_columns = [
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code', 
        'host_names', 
        'num.hosts', 
        'num.assets'
    ]
    
      
    df_summary_jobs_skipped = final_df[final_columns]
####################TABLA RESUMEN JOBS SKIPPED  ##################################


#################TABLA CON ERRORES DE JOBS (NO SKIPPED)  #########################
    # Filtrar entradas que no sean "SKIPPED"
    filtered_df = df[df['result.status'] != 'SKIPPED']

    filtered_df = filtered_df.fillna("(empty)")

    # Calcular las ocurrencias
    occurrence_df = filtered_df.groupby([
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code', 
        'host.name', 
        'asset.name',
        'result.error.reason'
    ]).size().reset_index(name='occurrence')

    # Crear un nuevo DataFrame con las columnas seleccionadas (excepto 'occurrence')
    selected_columns = [
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code', 
        'host.name', 
        'asset.name', 
        'result.error.reason', 
        'result.error.extendedReason', 
        'result.error.detailedDescription', 
        'result.error.remediation'
    ]
    processed_df = filtered_df[selected_columns]

    # Unir el DataFrame procesado con las ocurrencias
    final_df = processed_df.drop_duplicates(subset=[
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code', 
        'host.name', 
        'asset.name',
        'result.error.reason'
    ])

    final_df = final_df.merge(occurrence_df, on=[
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code', 
        'host.name', 
        'asset.name',
        'result.error.reason'
    ])

    # Reordenar las columnas para que 'occurrence' esté en la posición deseada
    final_columns = [
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code', 
        'occurrence',
        'host.name', 
        'asset.name', 
        'result.error.reason', 
        'result.error.extendedReason', 
        'result.error.detailedDescription', 
        'result.error.remediation'
    ]
    final_df = final_df[final_columns]

    # Ordenar el DataFrame final
    final_df_sorted = final_df.sort_values([
        'category', 
        'protectionPolicy.name', 
        'result.status', 
        'result.error.code', 
        'host.name', 
        'asset.name',
        'result.error.reason'
    ])

    df_unique_errors_no_skipped = final_df_sorted

####################################################################

    # susstituir la cadena "\n" por "|||" en todo el contenido del DataFrame
    #df_unique_errors_sorted = df_unique_errors_sorted.replace(r'\n', '  ..  ', regex=True)
    df_unique_errors_no_skipped = df_unique_errors_no_skipped.replace(r'\n', '  ..  ', regex=True)

    # Get file paths from config
    csv_files = config['systems'][system]['files']['csv']

    # Save DataFrames as CSV
    # save_dataframe_to_csv(df_assets_with_errors, os.path.join(csvPath, f'{system}-{instance}-{csv_files["assetErrors"]}'))
    # save_dataframe_to_csv(df_hosts_with_errors, os.path.join(csvPath, f'{system}-{instance}-{csv_files["hostErrors"]}'))
    # save_dataframe_to_csv(df_unique_errors_sorted, os.path.join(csvPath, f'{system}-{instance}-{csv_files["jobErrors"]}'))
    save_dataframe_to_csv(df_unique_errors_no_skipped, os.path.join(csvPath, f'{system}-{instance}-{csv_files["uniqueErrorsNoSkipped"]}'))
    save_dataframe_to_csv(df_summary_jobs_skipped, os.path.join(csvPath, f'{system}-{instance}-{csv_files["summaryJobsSkipped"]}'))
    #save_dataframe_to_csv(final_df, os.path.join(base_path, f'{system}-{instance}-{csv_files["summaryJobsSkipped"]}'))
        

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


def process_if_not_empty(file_path, process_function, system, instance, config, csvPath):
    """Checks if the JSON data is empty; if not, converts it to a DataFrame and processes it."""
    data = open_json_file(file_path)
    if not data:
        print(f'El archivo "{file_path}" está vacío o no contiene datos válidos. Se omitirá.')
        return
    
    df = convert_to_dataframe(data)
    process_function(df, system, instance, config, csvPath)


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

        # Verificar si el sistema es PPDM
        if system != "PPDM":
            continue  # Saltar a la siguiente iteración si no es PPDM

        print(f'PROCESANDO SISTEMAS "{system}"')
        print('------------------------')
        
        json_files = system_config['files']['json']
        
        for instance_config in system_config['instances']:
            hostname = instance_config["hostname"]

            print(f'Procesando información de : "{hostname}"')
            
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