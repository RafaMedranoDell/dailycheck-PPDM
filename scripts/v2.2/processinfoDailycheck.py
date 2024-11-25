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



def process_health(df, system, instance, config):
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
        'scoreDeduction': 'sum',
        'healthCategory': 'count'
    }).rename(columns={'scoreDeduction': 'Score', 'healthCategory': 'Issues'})
    # Convertir los valores de Score a negativos
    df_health_grouped['Score'] = -df_health_grouped['Score']

    # Unir los datos para completar el DataFrame de salud
    df_health = pd.merge(df_health_base, df_health_grouped, on='healthCategory', how='outer', suffixes=('_base', '_grouped'))
    # Rellenar los valores NaN con los valores correspondientes en 'Score' y 'Issues'
    df_health['Score'] = df_health['Score_grouped'].fillna(df_health['Score_base']).astype(int)
    df_health['Issues'] = df_health['Issues_grouped'].fillna(df_health['Issues_base']).astype(int)
    df_health = df_health[['healthCategory', 'Score', 'Issues']]

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

    # Reemplazar los valores en el DataFrame original de eventos de salud
    df_health_events = df.replace(r'\n', '|||', regex=True)

    # Get file paths from config
    base_path = config.get('basePath', '')
    csv_files = config['systems'][system]['files']['csv']

    save_dataframe_to_csv(df_health, os.path.join(base_path, f'{system}-{instance}-{csv_files["dashboardHealh"]}'))
    save_dataframe_to_csv(df_health_events, os.path.join(base_path, f'{system}-{instance}-{csv_files["healthEvents"]}'))



def process_job_group_activities(df, system, instance, config):
    """Process the Dashboard Job Group Activities DataFrame."""

    # Filter the DataFrame
    categories = ['CLOUD_TIER', 'INDEX', 'PROTECT', 'REPLICATE', 'RESTORE']
    filtered_df_job_groups = df.loc[df['category'].isin(categories)]
    
    # Create Job Groups DataFrame
    df_job_groups = filtered_df_job_groups['result.status'].value_counts().reset_index()
    df_job_groups.columns = ['result.status', 'Num']

    # Complete Job Groups DataFrame including all possible result.status
    possible_result_status = ['OK', 'FAILED', 'OK_WITH_ERRORS', 'CANCELED', 'SKIPPED', 'UNKNOWN']
    df_base = pd.DataFrame({
        'result.status': possible_result_status,
        'Num': 0
    })

    # DataFrames, usando un merge outer para asegurarse de no perder datos
    df_job_groups_complete = pd.merge(df_base, df_job_groups, on='result.status', how='outer')
    # Llenar valores nulos en la columna Num
    df_job_groups_complete['Num'] = df_job_groups_complete['Num_y'].combine_first(df_job_groups_complete['Num_x']).astype(int)
    # Seleccionar solamente las columnas necesarias
    df_job_groups_complete = df_job_groups_complete[['result.status', 'Num']]

    # Reemplazar los valores de 'result.status' para adecuarlo al Dashboard de PPDM
    status_mapping = {
        'OK': 'Successful',
        'FAILED': 'Failed',
        'OK_WITH_ERRORS': 'Completed with Exceptions',
        'CANCELED': 'Canceled',
        'SKIPPED': 'Skipped',
        'UNKNOWN': 'Unknown'
    }

    df_job_groups_complete['result.status'] = df_job_groups_complete['result.status'].replace(status_mapping)

    # Renombrar la columna 'result.status' a 'STATUS'
    df_job_groups_complete = df_job_groups_complete.rename(columns={'result.status': 'STATUS'})

    # Get file paths from config
    base_path = config.get('basePath', '')
    csv_files = config['systems'][system]['files']['csv']
    
    save_dataframe_to_csv(df_job_groups_complete, os.path.join(base_path, f'{system}-{instance}-{csv_files["dashboardjobgroupActivities"]}'))


def process_activities_no_ok(df, system, instance, config):
    """Process the Activities No OK DataFrame."""

    # CREATE DATAFRAME WITH NUMBER OF ASSETS WITH ERRORS
    df_assets_with_errors = df.groupby(
        ["category", "result.status", "result.error.code","protectionPolicy.name", "asset.type"]
    ).agg(Count=("asset.name", "nunique")).reset_index()

    # CREATE DATAFRAME WITH NUMBER OF "HOSTS" WITH "ERRORS"
    df_hosts_with_errors = df.groupby(
        ["category", "result.status", "result.error.code","protectionPolicy.name"]
    ).agg(Count=("host.name", "nunique")).reset_index()


    # CREATE DATAFRAME WITH ALL UNIQUE ERRORS
    columns_errors = ['category', 'result.status', 'protectionPolicy.name', 'result.error.code', 'host.name', 'asset.name', 'inventorySource.type', 'result.error.reason', 'result.error.extendedReason', 'result.error.detailedDescription', 'result.error.remediation']
    df_errors = df[columns_errors]
    df_unique_errors = df_errors.drop_duplicates(subset=['category', 'result.status', 'protectionPolicy.name', 'result.error.code', 'host.name', 'asset.name', 'inventorySource.type'])
    
    #df_unique_errors_sorted = df_unique_errors.sort_values(by=["category", "result.status"], kind='stable').reset_index(drop=True)
    df_unique_errors_sorted = df_unique_errors.sort_values(by=['category', 'protectionPolicy.name', 'result.status', 'result.error.code', 'host.name', 'asset.name'])



    # CRAETE DATAFRAME WITH UNIQUE ERRORS (EXCEPT SKIPPED)
    columns = ['category', 'protectionPolicy.name', 'result.status', 'result.error.code', 'host.name', 'asset.name', 'result.error.reason', 'result.error.extendedReason', 'result.error.detailedDescription', 'result.error.remediation']
    df_errors_no_skipped = df[columns]

    # Filtrar las filas donde "result.status" no sea "SKIPPED"
    df_unique_errors_no_skipped = df_errors_no_skipped[df_errors_no_skipped['result.status'] != 'SKIPPED']

    # Eliminar duplicados basados en la combinación de las columnas clave
    df_unique_errors_no_skipped = df_unique_errors_no_skipped.drop_duplicates(subset=['category', 'protectionPolicy.name', 'result.status', 'result.error.code', 'host.name', 'asset.name'])

    # Ordenar las filas según las columnas especificadas
    df_unique_errors_no_skipped = df_unique_errors_no_skipped.sort_values(by=['category', 'protectionPolicy.name', 'result.status', 'result.error.code', 'host.name', 'asset.name'])



    # CREATE DATAFRAME WITH SUMMARY OF JOBS SKIPPED
    df_errors_skipped = df[df['result.status'] == 'SKIPPED']

    # # Calcular num.hosts
    # # Group by the relevant columns and then count unique hosts
    # num_hosts_skipped = df_summary_jobs_skipped.groupby(['category', 'protectionPolicy.name', 'result.status', 'result.error.code'])['host.name'].nunique().reset_index(name='num.hosts')

    # # Calcular num.assets
    # # Group by the relevant columns and then count unique assets
    # num_assets_skipped = df_summary_jobs_skipped.groupby(['category', 'protectionPolicy.name', 'result.status', 'result.error.code'])['asset.name'].nunique().reset_index(name='num.assets')

    # # Merge with the original dataframe to get num.hosts and num.assets
    # df_summary_jobs_skipped = df_summary_jobs_skipped.merge(num_hosts_skipped, on=['category', 'protectionPolicy.name', 'result.status', 'result.error.code'], how='left')
    # df_summary_jobs_skipped = df_summary_jobs_skipped.merge(num_assets_skipped, on=['category', 'protectionPolicy.name', 'result.status', 'result.error.code'], how='left')

    # # Seleccionar las columnas en el orden especificado
    # columns_summary_jobs_skipped = ['category', 'protectionPolicy.name', 'result.status', 'result.error.code', 'host.name', 'asset.name', 'num.hosts', 'num.assets']
    # df_summary_jobs_skipped = df_summary_jobs_skipped[columns_summary_jobs_skipped]


    group_columns = ['category', 'protectionPolicy.name', 'result.status', 'result.error.code']
    
    # Calculamos el número de hosts únicos por grupo
    hosts_count = df_errors_skipped.groupby(group_columns)['host.name'].nunique().reset_index()
    hosts_count = hosts_count.rename(columns={'host.name': 'host.count'})
    
    # Calculamos el número de assets únicos por host y grupo
    assets_skipped_count = df_errors_skipped.groupby(group_columns + ['host.name', 'asset.name']).size().reset_index()
    assets_skipped_per_group = assets_skipped_count.groupby(group_columns).size().reset_index()
    assets_skipped_per_group = assets_skipped_per_group.rename(columns={0: 'host.assets'})
    
    # Forzamos que host.assets sea entero usando round y luego conversión a int
    assets_skipped_per_group['host.assets'] = assets_skipped_per_group['host.assets'].round().astype('Int64')
    
    # Combinamos los resultados
    df_summary_jobs_skipped = pd.merge(hosts_count, assets_skipped_per_group, on=group_columns, how='outer')
    
    # Ordenamos las columnas según el orden requerido
    columns_jobs_skipped = [
        'category',
        'protectionPolicy.name',
        'result.status',
        'result.error.code',
        'host.count',
        'host.assets'
    ]
    
    df_summary_jobs_skipped = df_summary_jobs_skipped[columns_jobs_skipped]
    
    # Aseguramos que ambas columnas numéricas sean enteros
    df_summary_jobs_skipped['host.count'] = df_summary_jobs_skipped['host.count'].astype('Int64')
    df_summary_jobs_skipped['host.assets'] = df_summary_jobs_skipped['host.assets'].astype('Int64')

    df_summary_jobs_skipped = df_summary_jobs_skipped.sort_values(by=['category', 'protectionPolicy.name', 'result.status', 'result.error.code'])



    # susstituir la cadena "\n" por "|||" en todo el contenido del DataFrame
    df_unique_errors_sorted = df_unique_errors_sorted.replace(r'\n', '  ..  ', regex=True)
    df_unique_errors_no_skipped = df_unique_errors_no_skipped.replace(r'\n', '  ..  ', regex=True)

    # Get file paths from config
    base_path = config.get('basePath', '')
    csv_files = config['systems'][system]['files']['csv']

    # Save DataFrames as CSV
    save_dataframe_to_csv(df_assets_with_errors, os.path.join(base_path, f'{system}-{instance}-{csv_files["assetErrors"]}'))
    save_dataframe_to_csv(df_hosts_with_errors, os.path.join(base_path, f'{system}-{instance}-{csv_files["hostErrors"]}'))
    save_dataframe_to_csv(df_unique_errors_sorted, os.path.join(base_path, f'{system}-{instance}-{csv_files["jobErrors"]}'))
    save_dataframe_to_csv(df_unique_errors_no_skipped, os.path.join(base_path, f'{system}-{instance}-{csv_files["uniqueErrorsNoSkipped"]}'))
    save_dataframe_to_csv(df_summary_jobs_skipped, os.path.join(base_path, f'{system}-{instance}-{csv_files["summaryJobsSkipped"]}'))
    
    

def process_if_not_empty(file_path, process_function, system, instance, config):
    """Checks if the JSON data is empty; if not, converts it to a DataFrame and processes it."""
    data = open_json_file(file_path)
    if not data:
        print(f'El archivo "{file_path}" está vacío o no contiene datos válidos. Se omitirá.')
        return
    
    df = convert_to_dataframe(data)
    process_function(df, system, instance, config)


def main():
    """Main function that coordinates all tasks."""
    # Load configuration
    with open("config_encrypted.json", "r") as config_file:
        config = json.load(config_file)
    
    for system, system_config in config["systems"].items():
        print(f'PROCESANDO SISTEMAS "{system}"')
        print('------------------------')
        
        json_files = system_config['files']['json']
        
        for instance_config in system_config['instances']:
            hostname = instance_config["hostname"]

            print(f'Procesando información de : "{hostname}"')
            
            # Process Health Issues
            health_files = glob.glob(f'{system}-{hostname}-{json_files["systemHealthIssues"]}') 
            if not health_files:
                print(f'  No existe el fichero "{system}-{hostname}-{json_files["systemHealthIssues"]}"')           
            else:
                print(f'  {hostname}: Procesando fichero: {health_files}')
                for file_path in health_files:
                    process_if_not_empty(file_path, process_health, system, hostname, config)
            
            # Process Job Group Activities
            job_files = glob.glob(f'{system}-{hostname}-{json_files["jobGroupActivitiesSummary"]}')
            if not job_files:
                print(f'  No existe el fichero "{system}-{hostname}-{json_files["jobGroupActivitiesSummary"]}"')
            else:
                print(f'  {hostname}: Procesando fichero: {job_files}')
                for file_path in job_files:
                    process_if_not_empty(file_path, process_job_group_activities, system, hostname, config)
            
            # Process Activities No OK
            activities_files = glob.glob(f'{system}-{hostname}-{json_files["activitiesNotOK"]}')            
            if not activities_files:
                print(f'  No existe el fichero "{system}-{hostname}-{json_files["activitiesNotOK"]}"')
            else:
                print(f'  {hostname}: Procesando fichero: {activities_files}')
                for file_path in activities_files:
                    process_if_not_empty(file_path, process_activities_no_ok, system, hostname, config)
            print('------------------------')



if __name__ == '__main__':
    main()