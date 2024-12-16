import os
import requests
import json
import urllib3
from datetime import datetime, timedelta
from password_manager import PasswordManager
import modules.functions as fn
import argparse

#Definicion de Variables
config_file = "config_encrypted.json"


# deshabilitar la advertencia de InsecureRequestWarning
#urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Script para obtener datos de sistemas.')
    parser.add_argument('--hours', type=int, default=24, help='Nmero de horas para el filtrado de actividades.')
    return parser.parse_args()


# Funcion para leer configuracion desde JSON
def load_config(config_file):
    with open(config_file, "r") as file:
        return json.load(file)
    

# functions to filter by date
def get_current_time():
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def get_hours_ago(hours):
    now = datetime.utcnow()
    time_ago = now - timedelta(hours=hours)
    return time_ago.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_filtered_results(url, headers, params, fields, cert_file):
    all_filtered_results = []
    page = 1
    total_pages = None

    while total_pages is None or page <= total_pages:
        response_data = requests.get(f"{url}?page={page}", headers=headers, params=params, verify=cert_file)
        response_data_json = response_data.json()

        if response_data.status_code != 200:
            print(f"Error: {response_data.status_code}")
            print(response_data.text)  # Error Details
            break

        if total_pages is None:
            total_pages = response_data_json['page']['totalPages']
            print("TOTAL PAGES: ", total_pages)
        
        # print(f"PAGE NUMBER: {page}")

        content_entries = response_data_json.get('content', [])
        filtered_results = fn.filter_entries(content_entries, fields)
        all_filtered_results.extend(filtered_results)

        page += 1  # Increase page for the next iteration

    return all_filtered_results


#Funcion to obtain the access token
def get_token_PPDM(instance, username, encrypted_password, cert_file):
    url = f'https://{instance}:8443/api/v2/login'
    headers = {
        'Content-Type': 'application/json'
    }

    # create instance of PasswordManager and decrypt password
    password_manager = PasswordManager()
    password = password_manager.decrypt_password(encrypted_password)

    data = {
        "username": username,
        "password": password
    }

    response = requests.post(url, headers=headers, data=json.dumps(data), verify=cert_file)

    if response.status_code == 200:
        response_json = response.json()
        access_token = response_json.get('access_token')
        refresh_token = response_json.get('refresh_token')
        return access_token, refresh_token
    else:
        print(f"Error: {response.status_code}")
    return None, None


# get health issues of the system
def get_health_issues(instance,access_token, cert_file):
    url = f'https://{instance}:8443/api/v2/system-health-issues'
    headers = {
        'Authorization': access_token
    }
    params = {}  
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
    return get_filtered_results(url, headers, params, fields, cert_file)


#get list of activities of type "job_group"
def get_job_group_activities(instance, access_token, cert_file, today, time_ago):
    url = f'https://{instance}:8443/api/v2/activities'
    headers = {
        'Authorization': access_token
    }
    filter_expression = (
        f'createTime ge "{time_ago}" and createTime lt "{today}" and classType eq "JOB_GROUP"'
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
    return get_filtered_results(url, headers, params, fields, cert_file)


# get list of activities with 'status' other than OK and 'protectionPolicy' and 'result.error.code' other than null
def get_activities_not_ok(instance, access_token, cert_file, today, time_ago):
    url = f'https://{instance}:8443/api/v2/activities'
    headers = {
        'Authorization': access_token
    }
    filter_expression = (
        f'createTime ge "{time_ago}" and createTime lt "{today}" '
        f'and result.status ne "OK" '
        f'and protectionPolicy.name ne null '        
        f'and (result.error.code ne null or host.name ne null or asset.name ne null)'   
    )
    params = {
        'filter': filter_expression
    }
    fields = [
        "category",
        "classType",
        "activityInitiatedType",
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
    return get_filtered_results(url, headers, params, fields, cert_file)


# get storage systems info
def get_storage_systems(instance,access_token, cert_file):
    url = f'https://{instance}:8443/api/v2/storage-systems'
    headers = {
        'Authorization': access_token
    }
    params = {}  
    fields = [
        "type",
        "name",
        "readiness",
        "details"
    ]

    return get_filtered_results(url, headers, params, fields, cert_file)


def main():
    args = parse_arguments()
    hours_ago = args.hours


    config = fn.load_json_file(config_file)
    base_path = config["basePath"]  # get the basePath from the config file
    json_relative_path = config["jsonPath"]
    jsonPath = os.path.join(base_path, json_relative_path)

    for system, system_data in config["systems"].items():
        json_files = system_data["files"]["json"]  # get the names of the JSON files
        for instance_info in system_data["instances"]:
            instance = instance_info["hostname"]
            username = instance_info["username"]
            encrypted_password = instance_info["encrypted_password"]

            if system == "PPDM":
                print("------------------------")
                print("PROCESANDO SISTEMA ", system)
                print("------------------------")

                print("------------------------")
                print("PROCESANDO", instance)
                print("------------------------")
                cert_relative_path = instance_info["certFile"]
                cert_file = os.path.join(base_path, cert_relative_path)            

                # get authentication token
                access_token, _ = get_token_PPDM(instance, username, encrypted_password, cert_file)            

                if not access_token:
                    print(f"Error: no se pudo obtener el token para {instance}.")
                    continue

                today = get_current_time()
                time_ago = get_hours_ago(hours_ago)

                print(instance, ": Fetching health issues...")                
                data = get_health_issues(instance, access_token, cert_file)
                fn.save_json(data, system, instance, json_files["systemHealthIssues"], jsonPath)

                print(instance, ": Fetching job group activities...")
                data = get_job_group_activities(instance, access_token, cert_file, today, time_ago)
                fn.save_json(data, system, instance, json_files["jobGroupActivitiesSummary"], jsonPath)

                print(instance, ": Fetching activities that are not OK...")
                data = get_activities_not_ok(instance, access_token, cert_file, today, time_ago)
                fn.save_json(data, system, instance, json_files["activitiesNotOK"], jsonPath)

                print(instance, ": Fetching storage systems...")
                data = get_storage_systems(instance, access_token, cert_file)
                fn.save_json(data, system, instance, json_files["storageSystems"], jsonPath)

    
if __name__ == "__main__":
    main()
