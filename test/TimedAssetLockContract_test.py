import pytest
from contracts.TimedAssetLockContract.Program import compile
from algosdk.v2client import algod

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
        clearBuildFolder()
        import os
        compile(client)
        assert os.path.exists('./build/assetTimedVault_Approval.compiled')
        assert os.path.exists('./build/assetTimedVault_Clear.compiled')
        assert os.path.exists('./build/assetTimedVault_Approval.teal')
        assert os.path.exists('./build/assetTimedVault_Clear.teal')
        assert os.path.exists('./build/globalSchema')
        assert os.path.exists('./build/globalSchema')



