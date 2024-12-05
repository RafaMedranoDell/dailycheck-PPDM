import os
import requests
import json
import urllib3
from password_manager import PasswordManager
import modules.functions as fn


# deshabilitar la advertencia de InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


#Definicion de Variables
config_file = "config_encrypted.json"


#Funcion para obtener el token
def get_token_DD(instance, username, encrypted_password, cert_file):
    url = f'https://ddve-01:3009/rest/v1.0/auth'
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
    #response = requests.post(url, headers=headers, data=json.dumps(data), verify=cert_file)
    
    if response.status_code == 201:        
        access_token = response.headers.get('X-DD-AUTH-TOKEN')
        return access_token
    else:
        print(f"Error: {response.status_code}")
    return None


def dd_get_alerts (instance, access_token, cert_file):
    url = f'https://{instance}:3009/rest/v2/dd-systems/0/alerts'
    headers = {
        "X-DD-AUTH-TOKEN": access_token
    }

    filter_expression = "status = active"
    page_size = "50"

    params = {
        'filter': filter_expression,
        'size': page_size
    }

    response_data = requests.get(url, headers=headers, params=params, verify=False)
    response_data_json = response_data.json()

    if response_data.status_code != 200:
        print(f"Error: {response_data.status_code}")
        print(response_data.text)  # Detalles del error

    # filtrar campos

    fields = [
        "id",
        "alert_id",
        "event_id",
        "status",
        "class",        
        "severity",
        "name",
        "alert_gen_epoch",
        "description",
        "msg",
        "additional_info",
        "clear_additional_info",
        "action"
    ]

    content_entries = response_data_json.get('alert_list', [])
    filtered_results = fn.filter_entries(content_entries, fields)    

    return filtered_results


def dd_get_services (instance, access_token, cert_file):
    url = f'https://{instance}:3009/rest/v1.0/dd-systems/0/services'
    headers = {
        "X-DD-AUTH-TOKEN": access_token
    }
    filter_expression = "name = ntp|snmp|iscsi|asup|nfs|filesys|encryption|cloud|ddboost"
    params = {
        "filter": filter_expression
    }
    
    response_data = requests.get(url, headers=headers, params=params, verify=False)
    response_data_json = response_data.json()

    if response_data.status_code != 200:
        print(f"Error: {response_data.status_code}")
        print(response_data.text)  # Detalles del error


    # filtrar campos

    fields = [
        "name",
        "status"
    ]

    content_entries = response_data_json.get('services', [])
    filtered_results = fn.filter_entries(content_entries, fields)    

    return filtered_results


def main():
    config = fn.load_json_file(config_file)
    base_path = config["basePath"]  # Obtener la ruta base desde el archivo de configuración
    json_relative_path = config["jsonPath"]
    jsonPath = os.path.join(base_path, json_relative_path)

    for system, system_data in config["systems"].items():
        json_files = system_data["files"]["json"]  # Obtener los nombres de los archivos JSON del sistema
        for instance_info in system_data["instances"]:
            instance = instance_info["hostname"]
            username = instance_info["username"]
            encrypted_password = instance_info["encrypted_password"]

            if system == "DD":
                print("------------------------")
                print("PROCESANDO SISTEMAS ", system)
                print("------------------------")

                print("------------------------")
                print("PROCESANDO", instance)
                print("------------------------")                
                cert_relative_path = config['systems']['PPDM']['files']['cert']
                cert_file = os.path.join(base_path, cert_relative_path)  

                access_token = get_token_DD(instance, username, encrypted_password, cert_file)

                if not access_token:
                    print(f"Error: no se pudo obtener el token para {instance}.")
                    continue

                print("Fetching active alerts...")
                data = dd_get_alerts(instance, access_token, cert_file)
                fn.save_json(data, system, instance, json_files["activeAlerts"], jsonPath)                            

                print("Fetching state of services...")
                data = dd_get_services(instance, access_token, cert_file)
                fn.save_json(data, system, instance, json_files["services"], jsonPath)


if __name__ == "__main__":
    main()
