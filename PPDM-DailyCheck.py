import argparse
import PPDMgetinfo
import getInfoDD
import PPDMprocessinfo
import PPDMgenerateXLSX
from PPDMcreatereportDC import PPDM_create_daily_check_report
from PPDMcreatereportDCI import PPDM_create_daily_investigation_report

def main():
    parser = argparse.ArgumentParser(description="Script para PPDM Daily Check")
    parser.add_argument('--hours', type=int, default=24, help='Número de horas atrás')
    args = parser.parse_args()

    configFile = "config_encrypted.json"
    
    PPDMgetinfo.main(hours_ago=args.hours, config_file=configFile)   
    PPDMprocessinfo.main(config_file=configFile)    
    PPDMgenerateXLSX.main(config_file=configFile)
    PPDM_create_daily_check_report(configFile)
    PPDM_create_daily_investigation_report(configFile)

    #getInfoDD.main()
    #createreportDC.main()

if __name__ == "__main__":
    main()