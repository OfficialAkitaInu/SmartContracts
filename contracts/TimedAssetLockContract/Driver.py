import Program
import Deployment
from akita_inu_asa_utils import *


def main():
    developer_config = load_developer_config()

    algod_address = developer_config['algodAddress']
    algod_token = developer_config['algodToken']
    algod_client = get_algod_client(algod_token, algod_address)

    Program.compile(algod_client)
    print("Program Compiled")
    #Deployment.deploy()
    #print("Program Deployed")


main()

