import os
import requests
import json
import urllib3
from datetime import datetime, timedelta
from password_manager import PasswordManager

#Definicion de Variables
config_file = "config_encrypted.json"


# deshabilitar la advertencia de InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Funcion para leer configuracion desde JSON
def load_config(config_file):
    with open(config_file, "r") as file:
        return json.load(file)
    

# Funciones para filtrar fecha
def get_current_time():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def get_24_hours_ago():
    now = datetime.utcnow()
    twenty_four_hours_ago = now - timedelta(hours=24)
    return twenty_four_hours_ago.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_filtered_results(url, headers, params, fields):
    all_filtered_results = []
    page = 1
    total_pages = None

    while total_pages is None or page <= total_pages:
        response_data = requests.get(f"{url}?page={page}", headers=headers, params=params, verify=False)
        response_data_json = response_data.json()

        if response_data.status_code != 200:
            print(f"Error: {response_data.status_code}")
            print(response_data.text)  # Detalles del error
            break

        if total_pages is None:
            total_pages = response_data_json['page']['totalPages']
            print("TOTAL PAGES: ", total_pages)
        
        print(f"PAGE NUMBER: {page}")

        content_entries = response_data_json.get('content', [])
        filtered_results = filter_entries(content_entries, fields)
        all_filtered_results.extend(filtered_results)

        page += 1  # Incrementar la pgina para la siguiente iteracin

    return all_filtered_results


def get_value_from_nested_keys(data, keys):
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def filter_entries(entries, fields):
    filtered_results = []
    for entry in entries:
        filtered_entry = {}
        for field in fields:
            keys = field.split('.')
            value = get_value_from_nested_keys(entry, keys)
            filtered_entry[field] = value
        filtered_results.append(filtered_entry)
    return filtered_results


##### LLAMADAS PPDM ######

#Funcion para obtener el token
def get_token_PPDM(instance,username, encrypted_password):
    url = f'https://{instance}:8443/api/v2/login'
    headers = {
        'Content-Type': 'application/json'
    }

    # Crear instancia de PasswordManager y desencriptar la contraseña
    password_manager = PasswordManager()
    password = password_manager.decrypt_password(encrypted_password)

    data = {
        "username": username,
        "password": password
    }

    response = requests.post(url, headers=headers, data=json.dumps(data), verify=False)

    if response.status_code == 200:
        response_json = response.json()
        access_token = response_json.get('access_token')
        refresh_token = response_json.get('refresh_token')
        return access_token, refresh_token
    else:
        print(f"Error: {response.status_code}")
    return None, None


def get_activities_not_ok(instance, access_token, today, twenty_four_hours_ago):
    url = f'https://{instance}:8443/api/v2/activities'
    headers = {
        'Authorization': access_token
    }
    filter_expression = (
        f'createTime ge "{twenty_four_hours_ago}" and createTime lt "{today}" '
        f'and result.status ne "OK" '
        f'and protectionPolicy.name ne null '
        f'and result.error.code ne null'
    )
    params = {
        'filter': filter_expression
    }
    fields = [
        "category",
        "classType",
        "result.status",
        "result.error.code",
        "result.error.detailedDescription",
        "result.error.extendedReason",
        "result.error.reason",
        "result.error.remediation",
        "asset.name",
        "asset.type",
        "host.name",
        "host.type",
        "inventorySource.type",
        "protectionPolicy.name",
        "protectionPolicy.type",
        "createTime",
        "endTime"
    ]
    return get_filtered_results(url, headers, params, fields)


def get_job_group_activities(instance, access_token, today, twenty_four_hours_ago):
    url = f'https://{instance}:8443/api/v2/activities'
    headers = {
        'Authorization': access_token
    }
    filter_expression = (
        f'createTime ge "{twenty_four_hours_ago}" and createTime lt "{today}" and classType eq "JOB_GROUP"'
    )
    params = {
        'filter': filter_expression
    }
    fields = [
        "category",
        "classType",
        "result.status",
        "createTime",
        "endTime"
    ]
    return get_filtered_results(url, headers, params, fields)


def get_health_issues(instance,access_token):
    url = f'https://{instance}:8443/api/v2/system-health-issues'
    headers = {
        'Authorization': access_token
    }
    params = {}  # No especificaste filtros, dejando vaco
    fields = [
        "healthCategory",
        "severity",
        "scoreDeduction",
        "componentType",
        "componentName",
        "messageID",
        "detailedDescription",
        "responseAction"
    ]
    return get_filtered_results(url, headers, params, fields)


def save_results_to_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


# Guardar los datos en un archivo JSON
def save_json(data, system, instance, query_name, base_path):
    output_file = os.path.join(base_path, f"{system}-{instance}-{query_name}")
    with open(output_file, "w") as file:
        json.dump(data, file, indent=4)
    print(f"Datos guardados en: {output_file}")


def main():
    config = load_config(config_file)
    base_path = config["basePath"]  # Obtener la ruta base desde el archivo de configuración

    for system, system_data in config["systems"].items():
        json_files = system_data["files"]["json"]  # Obtener los nombres de los archivos JSON del sistema
        for instance_info in system_data["instances"]:
            instance = instance_info["hostname"]
            username = instance_info["username"]            
            # Cambiar password por encrypted_password
            encrypted_password = instance_info["encrypted_password"]
            print(f'{instance} {username} {encrypted_password}')

            if system == "PPDM":
                # Obtener token de autenticación
                access_token, _ = get_token_PPDM(instance, username, encrypted_password)
                print(system)
                print(system, instance, access_token)

                if not access_token:
                    print(f"Error: no se pudo obtener el token para {instance}.")
                    continue

                today = get_current_time()
                twenty_four_hours_ago = get_24_hours_ago()

                print("Fetching health issues...")
                data = get_health_issues(instance, access_token)
                save_json(data, system, instance, json_files["systemHealthIssues"], base_path)

                print("Fetching job group activities...")
                data = get_job_group_activities(instance, access_token, today, twenty_four_hours_ago)
                save_json(data, system, instance, json_files["jobGroupActivitiesSummary"], base_path)

                print("Fetching activities that are not OK...")
                data = get_activities_not_ok(instance, access_token, today, twenty_four_hours_ago)
                save_json(data, system, instance, json_files["activitiesNotOK"], base_path)

    
if __name__ == "__main__":
    main()
