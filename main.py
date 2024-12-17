import argparse
import PPDMgetinfo
import getInfoDD
import PPDMprocessinfo
import PPDMgenerateXLSX
from PPDMcreatereportDC import PPDM_create_daily_check_report
from PPDMcreatereportDCI import PPDM_create_daily_investigation_report

def main():
    parser = argparse.ArgumentParser(description="Script para PPDM Daily Check")
    parser.add_argument('--hours', type=int, required=True, help='Número de horas atrás')
    args = parser.parse_args()

    config_file = "config_encrypted.json"
    
    PPDMgetinfo.main(hours_ago=args.hours, config_file)
    #getInfoDD.main()
    PPDMprocessinfo.main()
    #createreportDC.main()
    PPDMgenerateXLSX.main()
    PPDM_create_daily_check_report(config_file)
    PPDM_create_daily_investigation_report(config_file)

if __name__ == "__main__":
    main()