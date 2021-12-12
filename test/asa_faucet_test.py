import base64
import time

import pytest
from algosdk.v2client import algod
from algosdk import account, mnemonic, constants
from algosdk.encoding import encode_address, is_valid_address
from algosdk.error import AlgodHTTPError, TemplateInputError
from akita_inu_asa_utils import read_local_state, read_global_state, wait_for_txn_confirmation

NUM_TEST_ASSET = int(1e6)

MIN_ALGO_AMOUNT = 2
MIN_ASA_AMOUNT = 15
DRIP_TIME_SEC = 15

@pytest.fixture(scope='class')
def test_config():
    from .testing_utils import load_test_config
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
    from .testing_utils import fund_account
    wallet_mnemonic, private_key, public_key = generate_new_account()

    wallet_1 = {'mnemonic': wallet_mnemonic, 'public_key': public_key, 'private_key': private_key}

    # fund the wallet
    fund_account(wallet_1['public_key'], test_config['fund_account_mnemonic'])
    return wallet_1


@pytest.fixture(scope='class')
def asset_id(test_config, wallet_1, client):
    from akita_inu_asa_utils import (create_asa_signed_txn,
                                     asset_id_from_create_txn)
    params = client.suggested_params()
    txn, txn_id = create_asa_signed_txn(wallet_1['public_key'],
                                        wallet_1['private_key'],
                                        params,
                                        total=NUM_TEST_ASSET)
    client.send_transactions([txn])
    wait_for_txn_confirmation(client, txn_id, 5)
    return asset_id_from_create_txn(client, txn_id)


# This fixture also serves as the deploy test
# Note this fixture also shares the exact same application with all the test....unfortunately order in which test are
# called in this file depend on order
@pytest.fixture(scope='class')
def app_id(test_config, asset_id, end_time, wallet_1):
    from contracts.asa_faucet.deployment import deploy

    algod_address = test_config['algodAddress']
    algod_token = test_config['algodToken']
    creator_mnemonic = wallet_1['mnemonic']
    app_id = deploy(algod_address, algod_token, creator_mnemonic, asset_id, DRIP_TIME_SEC, MIN_ALGO_AMOUNT, MIN_ASA_AMOUNT)
    return app_id


def clear_build_folder():
    import os
    for file in os.scandir('./build'):
        os.remove(file.path)


class TestTimedAssetLockContract:
    def test_build(self, client):
        from contracts.timed_asset_lock_contract.program import compile_app
        clear_build_folder()
        import os
        compile_app(client)
        assert os.path.exists('./build/asa_faucet_approval.compiled')
        assert os.path.exists('./build/asa_faucet_clear.compiled')
        assert os.path.exists('./build/asa_faucet_approval.teal')
        assert os.path.exists('./build/asa_faucet_clear.teal')
        assert os.path.exists('./build/globalSchema')
        assert os.path.exists('./build/globalSchema')

    def test_deploy(self, app_id, client, asset_id, wallet_1):
        assert app_id
        public_key = wallet_1['public_key']

        local_state = read_local_state(client, public_key, app_id)
        global_state = read_global_state(client, public_key, app_id)

    def test_opt_in(self, app_id, client, asset_id, wallet_1):
        pass

    def test_claim(self, app_id, client, asset_id, wallet_1):
        pass

    def test_claim_to_soon(self, app_id, client, asset_id, wallet_1):
        pass
