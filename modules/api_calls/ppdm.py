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
                print(f'{instance} {username} {encrypted_password}')
                cert_relative_path = config['systems']['PPDM']['files']['cert']
                cert_file = os.path.join(base_path, cert_relative_path)  

                access_token = get_token_DD(instance, username, encrypted_password, cert_file)

                if not access_token:
                    print(f"Error: no se pudo obtener el token para {instance}.")
                    continue

                print("Fetching active alerts...")
                data = dd_get_alerts(instance, access_token, cert_file)
                save_json(data, system, instance, json_files["activeAlerts"], jsonPath)                            

                print("Fetching state of services...")
                data = dd_get_services(instance, access_token, cert_file)
                save_json(data, system, instance, json_files["services"], jsonPath)