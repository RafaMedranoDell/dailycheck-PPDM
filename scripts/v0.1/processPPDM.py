import pandas as pd
import json
import csv
import os


def open_json_file(file_path):
    """Opens a JSON file and loads it into a dictionary."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def convert_to_dataframe(data):
    """Converts a dictionary to a pandas DataFrame."""
    df = pd.DataFrame(data)
    return df


def save_dataframe_to_csv(df, file_name):
    """Saves the DataFrame to a CSV file."""
    #csv_path = os.path.join('output_folder_path', file_name)
    csv_path = file_name
    df.to_csv(csv_path, index=False, quoting=csv.QUOTE_ALL, escapechar='\\')


def process_health(df):
    """Process the Health DataFrame."""
    
    # Possible health categories
    possible_health_category = ['CAPACITY', 'PERFORMANCE', 'CONFIGURATION', 'COMPONENTS', 'DATA_PROTECTION']

    # Create a DataFrame with all possible 'healthCategory' set to '0'
    df_health_base = pd.DataFrame({
        'healthCategory': possible_health_category,
        'Score': 0,
        'Issues': 0
    })

    # Group by healthCategory and sum scoreDeduction and count the issues
    df_health_grouped = df.groupby('healthCategory').agg({
        'scoreDeduction': 'sum',
        'healthCategory': 'count'
    }).rename(columns={'scoreDeduction': 'Score', 'healthCategory': 'Issues'})
    # Convierte los valores de Score a negativos
    df_health_grouped['Score'] = -df_health_grouped['Score']

    # Merge the data for a complete health DataFrame using 'health.category' ase key
    df_health = pd.merge(df_health_base, df_health_grouped, on='healthCategory', how='outer', suffixes=('_base', '_grouped'))
    # Rellena los valores NaN con los valores correspondientes en 'Score' y 'Issues'
    df_health['Score'] = df_health['Score_grouped'].fillna(df_health['Score_base']).astype(int)
    df_health['Issues'] = df_health['Issues_grouped'].fillna(df_health['Issues_base']).astype(int)
    df_health = df_health[['healthCategory', 'Score', 'Issues']]

    # Selecciona solamente las columnas necesarias y ajusta los nombres
    df_health_events = df.replace(r'\n', '|||', regex=True)

    save_dataframe_to_csv(df_health, 'PPDM-Dashboard-Health.csv')
    save_dataframe_to_csv(df_health_events, 'PPDM-Health_events.csv')



def process_job_group_activities(df):
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

    save_dataframe_to_csv(df_job_groups_complete, 'PPDM-Dashboard-JobGroupActivities.csv')



def process_activities_no_ok(df):
    """Process the Activities No OK DataFrame."""
    
    # Create DataFrame with number of ASSETS with ERRORS
    df_assets_with_errors = df.groupby(
        ["category", "result.status", "result.error.code","protectionPolicy.name", "asset.type"]
    ).agg(Count=("asset.name", "nunique")).reset_index()

    # Create DataFrame with number of HOSTS with ERRORS
    df_hosts_with_errors = df.groupby(
        ["category", "result.status", "result.error.code","protectionPolicy.name"]
    ).agg(Count=("host.name", "nunique")).reset_index()

    # Create DataFrame with all unique errors
    columns_errors = ['category', 'result.status', 'protectionPolicy.name', 'result.error.code', 'host.name', 'asset.name', 'inventorySource.type', 'result.error.detailedDescription', 'result.error.reason','result.error.extendedReason', 'result.error.remediation']
    df_errors = df[columns_errors]
    df_unique_errors = df_errors.drop_duplicates(subset=['category', 'result.status', 'protectionPolicy.name', 'result.error.code', 'host.name', 'asset.name', 'inventorySource.type'])
    
    # susstituir la cadena "\n" por "|||" en todo el contenido del DataFrame
    df_unique_errors = df_unique_errors.replace(r'\n', '|||', regex=True)

    # Save DataFrames as CSV
    save_dataframe_to_csv(df_assets_with_errors, 'PPDM-errorAssets.csv')
    save_dataframe_to_csv(df_hosts_with_errors, 'PPDM-errorHosts.csv')
    save_dataframe_to_csv(df_unique_errors, 'PPDM-jobErrors.csv')



def main():
    """Main function that coordinates all tasks."""
    
    # Process Health
    data = open_json_file('health_issues.json')
    df = convert_to_dataframe(data)
    process_health(df)

    # Process Dashboard Job Group Activities
    data = open_json_file('JobGroupActivities.json')
    df = convert_to_dataframe(data)
    process_job_group_activities(df)

    # Process Activities No OK
    data = open_json_file('activitiesNoOK.json')
    df = convert_to_dataframe(data)
    process_activities_no_ok(df)


if __name__ == '__main__':
    main()