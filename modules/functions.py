import json
import os
import csv
import pandas as pd



# Funcion para leer configuracion desde JSON
def load_json_file(json_file):
    with open(json_file, "r") as file:
        return json.load(file)


def save_dataframe_to_csv(df, file_path):
    """Saves the DataFrame to a CSV file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_csv(file_path, index=False, quoting=csv.QUOTE_ALL, escapechar='\\')
    
    if os.path.exists(file_path):  # Cambiar 'csv_path' a 'file_path'
        print(f'    File saved succesfully: {file_path}')
    else:
        print(f'    Error saving the file: {file_path}')


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


# Guardar los datos en un archivo JSON
def save_json(data, system, instance, query_name, base_path):
    #print("rafa")
    output_file = os.path.join(base_path, f"{system}-{instance}-{query_name}")
    with open(output_file, "w") as file:
        json.dump(data, file, indent=4)
    print(f"Data saved in: {output_file}")