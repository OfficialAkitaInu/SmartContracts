import Program
import Deployment
import AkitaInuASAUtils as AIASAU


def main():
    developerConfig = AIASAU.loadDeveloperConfig()

    algodAddress = developerConfig['algodAddress']
    algodToken = developerConfig['algodToken']
    algodClient = AIASAU.getAlgodClient(algodToken, algodAddress)

    Program.compile(algodClient)
    print("Program Compiled")
    Deployment.deploy()
    print("Program Deployed")

main()

