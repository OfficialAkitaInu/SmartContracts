import sys
sys.path.append('/home/palmerss/Desktop/SmartContracts/test')
import time

import pytest
from algosdk.v2client import algod

from algosdk import account, mnemonic, constants
from algosdk.encoding import encode_address, is_valid_address
from algosdk.error import AlgodHTTPError, TemplateInputError

@pytest.fixture(scope='class')
def test_config():
    from test.testing_utils import load_test_config
    return load_test_config()

@pytest.fixture(scope='class')
def client(test_config):
    algod_address = test_config['algodAddress']
    algod_token = test_config['algodToken']
    client = algod.AlgodClient(algod_token, algod_address)
    return client

@pytest.fixture(scope='class')
def wallet_1(test_config):
    from akita_inu_asa_utils import generate_new_account
    wallet_mnemonic, private_key, public_key = generate_new_account()
    from testing_utils import fund_account
    wallet_1 = {}
    wallet_1['mnemonic'] = wallet_mnemonic
    wallet_1['publicKey'] = public_key
    wallet_1['privateKey'] = private_key

    # fund the wallet
    fund_account(wallet_1['publicKey'], test_config['fund_account_Mnemonic'])
    return wallet_1

@pytest.fixture(scope='class')
def wallet_2(test_config):
    from akita_inu_asa_utils import generate_new_account
    wallet_mnemonic, private_key, public_key = generate_new_account()
    wallet_2 = {}
    wallet_2['mnemonic'] = wallet_mnemonic
    wallet_2['publicKey'] = public_key
    wallet_2['privateKey'] = private_key
    return wallet_2


@pytest.fixture(scope='class')
def asset_id(test_config, wallet_1, client):
    from akita_inu_asa_utils import create_asa_signed_txn, \
        asset_id_from_create_txn, \
        wait_for_txn_confirmation
    params = client.suggested_params()
    txn, txn_id = create_asa_signed_txn(wallet_1['publicKey'],
                                        wallet_1['privateKey'],
                                        params)
    client.send_transactions([txn])
    wait_for_txn_confirmation(client, txn_id, 5)
    return asset_id_from_create_txn(client, txn_id)


@pytest.fixture(scope='class')
def end_time():
    import time
    return int(time.time()) + 60

# This fixture also serves as the deploy test
# Note this fixture also shares the exact same application with all the test....unfortunately order in which test are
# called in this file depend on order
@pytest.fixture(scope='class')
def app_id(test_config, asset_id, end_time, wallet_1):
    from contracts.timed_asset_lock_contract.deployment import deploy

    algod_address = test_config['algodAddress']
    algod_token = test_config['algodToken']
    creator_mnemonic = wallet_1['mnemonic']
    app_id = deploy(algod_address, algod_token, creator_mnemonic, asset_id, end_time)
    return app_id


def clearBuildFolder():
    import os

    for file in os.scandir('./build'):
        os.remove(file.path)


class TestTimedAssetLockContract:
    def test_build(self, client):
        from contracts.timed_asset_lock_contract.program import compile
        clearBuildFolder()
        import os
        compile(client)
        assert os.path.exists('./build/assetTimedVault_Approval.compiled')
        assert os.path.exists('./build/assetTimedVault_Clear.compiled')
        assert os.path.exists('./build/assetTimedVault_Approval.teal')
        assert os.path.exists('./build/assetTimedVault_Clear.teal')
        assert os.path.exists('./build/globalSchema')
        assert os.path.exists('./build/globalSchema')

    def test_deploy(self, app_id, client, asset_id, wallet_1):
        from akita_inu_asa_utils import (
            getApplicationAddress,
            payment_signed_txn,
            wait_for_txn_confirmation
        )
        assert app_id

        # got to fund the contract with algo
        app_public_key = getApplicationAddress(app_id)
        params = client.suggested_params()
        txn, txn_id = payment_signed_txn(wallet_1['privateKey'],
                                         wallet_1['publicKey'],
                                         app_public_key, 300000, params)
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

    def test_on_setup(self, app_id, wallet_1, asset_id, client):
        from akita_inu_asa_utils import (
            noop_app_signed_txn,
            wait_for_txn_confirmation,
            getApplicationAddress,
            payment_signed_txn
        )
        params = client.suggested_params()

        txn, txn_id = noop_app_signed_txn(wallet_1['privateKey'],
                                          wallet_1['publicKey'],
                                          params,
                                          app_id,
                                          [asset_id])
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

        #got to fund the app with the asset
        app_public_key = getApplicationAddress(app_id)
        txn, txn_id = payment_signed_txn(wallet_1['privateKey'],
                                         wallet_1['publicKey'],
                                         app_public_key,
                                         100,
                                         params,
                                         asset_id=asset_id)
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

    def test_on_opt_in(self, app_id, wallet_1, client, asset_id):
        from algosdk import mnemonic
        from akita_inu_asa_utils import opt_in_app_signed_txn, wait_for_txn_confirmation

        public_key = wallet_1['publicKey']
        private_key = wallet_1['privateKey']

        params = client.suggested_params()

        txn, txn_id = opt_in_app_signed_txn(private_key,
                                            public_key,
                                            params,
                                            app_id,
                                            foreign_assets=[asset_id])
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

# WARNING DELETE TESTS DO NOT WORK IF YOUR RUNNING SANDBOX IN DEV MODE DUE TO TIMESTAMPING IN DEV MODE
    def test_on_delete_too_soon(self, app_id, wallet_1, client):
        from algosdk.error import AlgodHTTPError
        from akita_inu_asa_utils import delete_app_signed_txn, wait_for_txn_confirmation

        public_key = wallet_1['publicKey']
        private_key = wallet_1['privateKey']
        params = client.suggested_params()

        txn, txn_id = delete_app_signed_txn(private_key, public_key, params, app_id)
        with pytest.raises(AlgodHTTPError):
            client.send_transactions([txn])
            wait_for_txn_confirmation(client, txn_id, 5)

    def test_on_delete_on_time(self, app_id, wallet_1, client, end_time, asset_id):
        from akita_inu_asa_utils import delete_app_signed_txn, wait_for_txn_confirmation, getApplicationAddress

        public_key = wallet_1['publicKey']
        private_key = wallet_1['privateKey']
        params = client.suggested_params()

        txn, txn_id = delete_app_signed_txn(private_key, public_key, params, app_id, asset_ids=[asset_id])
        sleep_time = (end_time + 10) - int(time.time())

        time.sleep(sleep_time)
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)
