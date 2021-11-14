import pytest
from algosdk.v2client import algod
from test.testingUtils import *

@pytest.fixture()
def client():
    import json
    fp = open('DeveloperConfig.json')
    config = json.load(fp)
    algod_address = config['algodAddress']
    algod_token = config['algodToken']
    client = algod.AlgodClient(algod_token, algod_address)
    return client

def clearBuildFolder():
    import os

    for file in os.scandir('./build'):
        os.remove(file.path)

class TestTimedAssetLockContract:
    def test_build(self, client):
        from contracts.TimedAssetLockContract.Program import compile
        clearBuildFolder()
        import os
        compile(client)
        assert os.path.exists('./build/assetTimedVault_Approval.compiled')
        assert os.path.exists('./build/assetTimedVault_Clear.compiled')
        assert os.path.exists('./build/assetTimedVault_Approval.teal')
        assert os.path.exists('./build/assetTimedVault_Clear.teal')
        assert os.path.exists('./build/globalSchema')
        assert os.path.exists('./build/globalSchema')

    #TODO smelly testing practice here, this test relies on already compiled files to exist, but I still want  the test to be independent
    def test_deploy(self):
        from contracts.TimedAssetLockContract.Deployment import deploy
        import time
        test_config = load_test_config()

        end_time = int(time.time()) + 60
        algod_address = test_config['algodAddress']
        algod_token = test_config['algodToken']
        creator_mnemonic = test_config['wallet1_Mnemonic']
        creater_public_key = test_config['wallet1_publicKey']
        asset_id = test_config['asset_id']
        app_id = deploy(algod_address, algod_token, creater_public_key, creator_mnemonic, asset_id, end_time)
        assert app_id
