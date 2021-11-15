import pytest
from algosdk.v2client import algod

@pytest.fixture(scope='class')
def test_config():
    from test.testingUtils import load_test_config
    return load_test_config()

@pytest.fixture
def client(test_config):
    algod_address = test_config['algodAddress']
    algod_token = test_config['algodToken']
    client = algod.AlgodClient(algod_token, algod_address)
    return client

#This fixture also serves as the deploy test
#Note this fixture also shares the exact same application with all the test....unfortunately order in which test are
#called in this file depend on order
@pytest.fixture(scope='class')
def app_id(test_config):
    from contracts.TimedAssetLockContract.Deployment import deploy
    import time

    end_time = int(time.time()) + 60
    algod_address = test_config['algodAddress']
    algod_token = test_config['algodToken']
    creator_mnemonic = test_config['wallet1_Mnemonic']
    creater_public_key = test_config['wallet1_publicKey']
    asset_id = test_config['asset_id']
    app_id = deploy(algod_address, algod_token, creater_public_key, creator_mnemonic, asset_id, end_time)
    return app_id

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

    def test_deploy(self, app_id):
        assert app_id

    def test_on_setup(self, app_id, test_config, client):
        from algosdk import mnemonic
        from akita_inu_asa_utils import noop_app_signed_txn, wait_for_txn_confirmation, getApplicationAddress, \
            transfer_signed_txn

        public_key = test_config['wallet1_publicKey']
        creator_mnemonic = test_config['wallet1_Mnemonic']
        asset_id = test_config['asset_id']
        private_key = mnemonic.to_private_key(creator_mnemonic)
        params = client.suggested_params()

        #got to fund the contract
        app_public_key = getApplicationAddress(app_id)
        txn, txn_id = transfer_signed_txn(private_key, public_key, app_public_key, 300000, params)
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

        txn, txn_id = noop_app_signed_txn(private_key,
                                          public_key,
                                          params,
                                          app_id,
                                          [asset_id])
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)
