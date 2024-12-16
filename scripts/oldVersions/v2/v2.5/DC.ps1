# Define la ruta del archivo de log
$logFile = "C:\github\dailycheck-PPDM\logs\log.txt"

# Asegúrate de que el archivo de log exista o se cree vacío
New-Item -ItemType File -Path $logFile -Force | Out-Null

# Define los comandos a ejecutar
$commands = @(
    @("E:\WPy64-310111\python-3.10.11.amd64\python.exe", "C:\github\dailycheck-PPDM\scripts\v2.5\getinfoDC.py"),
    @("E:\WPy64-310111\python-3.10.11.amd64\python.exe", "C:\github\dailycheck-PPDM\scripts\v2.5\processinfoDailycheck.py"),
    @("E:\WPy64-310111\python-3.10.11.amd64\python.exe", "C:\github\dailycheck-PPDM\scripts\v2.5\createreportDC.py"),
    @("E:\WPy64-310111\python-3.10.11.amd64\python.exe", "C:\github\dailycheck-PPDM\scripts\v2.5\createreportDCI.py")
)

# Ejecutar cada comando y guardar la salida en el archivo de log
foreach ($command in $commands) {
    try {
        # Construir el comando a ejecutar
        $executable = $command[0]
        $arguments = $command[1]
        Write-Output "Ejecutando: $executable $arguments" | Out-File -FilePath $logFile -Append
        # Ejecutar el comando
        & $executable $arguments *>&1 | Out-File -FilePath $logFile -Append
        Write-Output "Comando finalizado: $executable $arguments" | Out-File -FilePath $logFile -Append
    } catch {
        Write-Output "Error ejecutando: $executable $arguments. Error: $_" | Out-File -FilePath $logFile -Append
    }
}

Write-Output "Todos los comandos se han ejecutado. Revisa el archivo de log: $logFile"
