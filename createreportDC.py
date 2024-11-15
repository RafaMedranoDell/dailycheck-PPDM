import pandas as pd
import webbrowser
import tempfile
import jinja2


# Cargar los archivos CSV en DataFrames
df_health = pd.read_csv("PPDM-PPDM-01-Dashboard-Health.csv")
df_job_group = pd.read_csv("PPDM-PPDM-01-Dashboard-JobGroupActivities.csv")


# Definir la función para colorear las celdas en la columna "Score"
def color_score(val):
    if val == 0:
        color = 'background-color: green'
    elif 0 > val >= -20:
        color = 'background-color: yellow'
    elif val < -20:
        color = 'background-color: red'
    else:
        color = ''
    return color


# Definir la funcion para colorear la celda en la columna "Num" de la fila "FAILED" en la segunda tabla
def color_failed(row):
    if row['result.status'] == 'FAILED' and row['Num'] != 0:
        return ['background-color: red'] * len(row)
    return [''] * len(row)


# Aplicar el estilo solo en la columna "Score"
styled_health = df_health.style.applymap(color_score, subset=['Score'])
styled_job_group = df_job_group.style.apply(color_failed, axis=1)


# Convertir cada DataFrame a HTML sin aplicar estilos adicionales
html_health = styled_health.to_html()
#html_job_group = df_job_group.to_html(index=False)
html_job_group = styled_job_group.to_html()


# Crear el cuerpo HTML del correo con el título
html_body = f"""
<html>
    <body>
        <h2 style="font-family: Arial, sans-serif; color: #0044cc;">DAILYCHECK PPDM</h2>
        <p style="font-family: Arial, sans-serif; color: #333;">Reporte Diario de Sistemas:</p>
        
        <!-- Insertar cada tabla como HTML -->
        <div style="padding: 10px;">
            {html_health}
        </div>
        
        <div style="padding: 10px;">
            {html_job_group}
        </div>
    </body>
</html>
"""


# Guardar el HTML en un archivo temporal y abrirlo en el navegador
with tempfile.NamedTemporaryFile('w', delete=False, suffix='.html') as f:
    f.write(html_body)
    temp_file_path = f.name


# Abrir el archivo en el navegador predeterminado
webbrowser.open(f'file://{temp_file_path}')


