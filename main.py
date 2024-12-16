import PPDMgetinfo
import getInfoDD
import PPDMprocessinfo
import PPDMgenerateXLSX

def main():
    PPDMgetinfo.main()
    #getInfoDD.main()
    PPDMprocessinfo.main()
    #createreportDC.main()
    PPDMgenerateXLSX.main()

if __name__ == "__main__":
    main()