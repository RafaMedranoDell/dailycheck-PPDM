import requests
import json
import urllib3
from datetime import datetime, timedelta


#Definicion
ppdm = 'ppdm-01'
username = 'DCOapi'
password = 'Password123!'


# deshabilitar la advertencia de InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Funciones para filtrar por fecha
def get_current_time():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

def get_24_hours_ago():
    now = datetime.utcnow()
    twenty_four_hours_ago = now - timedelta(hours=24)
    return twenty_four_hours_ago.strftime("%Y-%m-%dT%H:%M:%SZ")


#Funcion para obtener el token
def get_tokens(username, password):
    url = f'https://{ppdm}:8443/api/v2/login'
    headers = {
        'Content-Type': 'application/json'
    }

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


#Función Auxiliar: Maneja la paginacion y aplica los filtros necesarios a los resultados obtenidos
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

        page += 1  # Incrementar la pgina para la siguiente iteracion

    return all_filtered_results


#recorre un diccionario anidado para obtener el valor correspondiente a una lista de claves.
def get_value_from_nested_keys(data, keys):
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


#toma una lista de diccionarios anidados y aplanara cada uno de estos diccionarios segun los campos especificados en fields. 
#Cada campo a extraer puede ser especificado con su ruta completa, y el valor correspondiente sera almacenado en el diccionario resultante usando el nombre de campo completo.
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


def get_activities_not_ok(access_token, today, twenty_four_hours_ago):
    url = f'https://{ppdm}:8443/api/v2/activities'
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


def get_job_group_activities(access_token, today, twenty_four_hours_ago):
    url = f'https://{ppdm}:8443/api/v2/activities'
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


def get_health_issues(access_token):
    url = f'https://{ppdm}:8443/api/v2/system-health-issues'
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


# Obtener fecha actual y fecha de hace 24 horas
today = get_current_time()
twenty_four_hours_ago = get_24_hours_ago()


# Obtenemos los tokens
access_token, refresh_token = get_tokens(username, password)


# Si obtenemos los tokens correctamente, hacemos las llamadas a las otras APIs
if access_token:
    print("Fetching activities that are not OK...")
    not_ok_activities = get_activities_not_ok(access_token, today, twenty_four_hours_ago)
    save_results_to_json('activitiesNoOK.json', not_ok_activities)
    print("Saved not OK activities to activitiesNoOK.json")

    print("Fetching job group activities...")
    job_group_activities = get_job_group_activities(access_token, today, twenty_four_hours_ago)
    save_results_to_json('JobGroupActivities.json', job_group_activities)
    print("Saved job group activities to JobGroupActivities.json")

    print("Fetching health issues...")
    health_issues = get_health_issues(access_token)
    save_results_to_json('health_issues.json', health_issues)
    print("Saved health issues to health_issues.json")
    
else:
    print("Failed to obtain access token.")