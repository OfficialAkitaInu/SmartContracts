import base64
import time

import pytest
from algosdk.v2client import algod
from algosdk.future import transaction
from algosdk import account, mnemonic, constants
from algosdk.encoding import encode_address, is_valid_address
from algosdk.error import AlgodHTTPError, TemplateInputError
from akita_inu_asa_utils import read_local_state, read_global_state, wait_for_txn_confirmation, get_key_from_state
from .testing_utils import clear_build_folder

NUM_TEST_ASSET = int(1e6)

MIN_ALGO_AMOUNT = 2
MIN_ASA_AMOUNT = 15
DRIP_TIME_SEC = 15
DRIP_AMOUNT = 3

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
    import os
    wallet_mnemonic, private_key, public_key = generate_new_account()

    wallet_1 = {'mnemonic': wallet_mnemonic, 'public_key': public_key, 'private_key': private_key}

    # fund the wallet
    fund_account(wallet_1['public_key'], os.environ['fund_account_mnemonic'])
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
def app_id(test_config, asset_id, wallet_1):
    from contracts.asa_faucet.deployment import deploy

    algod_address = test_config['algodAddress']
    algod_token = test_config['algodToken']
    creator_mnemonic = wallet_1['mnemonic']
    app_id = deploy(algod_address, algod_token, creator_mnemonic, asset_id, DRIP_AMOUNT, DRIP_TIME_SEC, MIN_ALGO_AMOUNT, MIN_ASA_AMOUNT)
    return app_id

class TestASAFaucet:
    def test_build(self, client):
        from contracts.asa_faucet.program import compile_app
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

        global_state = read_global_state(client, public_key, app_id)
        assert get_key_from_state(global_state, b'asset_id_key') == asset_id
        assert get_key_from_state(global_state, b'drip_time') == DRIP_TIME_SEC
        assert get_key_from_state(global_state, b'min_algo_amount') == MIN_ALGO_AMOUNT
        assert get_key_from_state(global_state, b'min_asset_amount') == MIN_ASA_AMOUNT

    def test_opt_in(self, app_id, client, asset_id, wallet_1):
        from akita_inu_asa_utils import opt_in_app_signed_txn, wait_for_txn_confirmation

        public_key = wallet_1['public_key']
        private_key = wallet_1['private_key']
        txn, txn_id = opt_in_app_signed_txn(private_key, public_key, client.suggested_params(), app_id)
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

        local_state = read_local_state(client, public_key, app_id)
        assert time.time() - 60 <= get_key_from_state(local_state, b'user_last_claim_time') <= time.time()

    def test_opt_in_asset(self, app_id, client, asset_id, wallet_1):
        from akita_inu_asa_utils import get_application_address
        public_key = wallet_1['public_key']
        private_key = wallet_1['private_key']

        app_address = get_application_address(app_id)
        txn0 = transaction.PaymentTxn(public_key, client.suggested_params(), app_address, 201000)
        app_args = [
            "opt_in_asset".encode("utf-8")
        ]
        txn1 = transaction.ApplicationNoOpTxn(public_key, client.suggested_params(), app_id, app_args,
                                              foreign_assets=[asset_id])

        grouped = transaction.assign_group_id([txn0, txn1])
        grouped = [grouped[0].sign(private_key),
                   grouped[1].sign(private_key)]

        txn_id = client.send_transactions(grouped)
        wait_for_txn_confirmation(client, txn_id, 5)

    def test_fund_faucet(self, app_id, client, asset_id, wallet_1):
        from akita_inu_asa_utils import get_application_address, get_asset_balance
        public_key = wallet_1['public_key']
        private_key = wallet_1['private_key']

        app_address = get_application_address(app_id)

        txn0 = transaction.AssetTransferTxn(public_key, client.suggested_params(), app_address, NUM_TEST_ASSET - 20, asset_id)
        app_args = [
            "fund_faucet".encode("utf-8")
        ]
        txn1 = transaction.ApplicationNoOpTxn(public_key, client.suggested_params(), app_id, app_args, foreign_assets=[asset_id])

        grouped = transaction.assign_group_id([txn0, txn1])
        grouped = [grouped[0].sign(private_key),
                   grouped[1].sign(private_key)]

        txn_id = client.send_transactions(grouped)
        wait_for_txn_confirmation(client, txn_id, 5)

        assert get_asset_balance(client, app_address, asset_id) == (NUM_TEST_ASSET - 20)


    def test_claim(self, app_id, client, asset_id, wallet_1):
        from akita_inu_asa_utils import noop_app_signed_txn, get_asset_balance, get_application_address

        time.sleep(DRIP_TIME_SEC)
        public_key = wallet_1['public_key']
        private_key = wallet_1['private_key']
        wallet_balance_pre = get_asset_balance(client, public_key, asset_id)
        app_args = [
            "get_drip".encode("utf-8")
        ]
        app_address = get_application_address(app_id)
        txn0 = transaction.PaymentTxn(public_key, client.suggested_params(), app_address, 1000)
        txn1 = transaction.ApplicationNoOpTxn(public_key, client.suggested_params(), app_id, app_args, foreign_assets=[asset_id])
        grouped = transaction.assign_group_id([txn0, txn1])
        grouped = [grouped[0].sign(private_key),
                   grouped[1].sign(private_key)]
        txn_id = client.send_transactions(grouped)
        wait_for_txn_confirmation(client, txn_id, 5)

        local_state = read_local_state(client, public_key, app_id)
        assert get_asset_balance(client, public_key, asset_id) == wallet_balance_pre + DRIP_AMOUNT
        assert get_key_from_state(local_state, b'user_last_claim_time') <= (time.time() + 15)

    def test_claim_to_soon(self, app_id, client, asset_id, wallet_1):
        from akita_inu_asa_utils import get_application_address
        public_key = wallet_1['public_key']
        private_key = wallet_1['private_key']

        app_args = [
            "get_drip".encode("utf-8")
        ]
        app_address = get_application_address(app_id)
        txn0 = transaction.PaymentTxn(public_key, client.suggested_params(), app_address, 1000)
        txn1 = transaction.ApplicationNoOpTxn(public_key, client.suggested_params(), app_id, app_args,
                                              foreign_assets=[asset_id])
        grouped = transaction.assign_group_id([txn0, txn1])

        grouped = [grouped[0].sign(private_key),
                   grouped[1].sign(private_key)]

        with pytest.raises(AlgodHTTPError):
            txn_id = client.send_transactions(grouped)
            wait_for_txn_confirmation(client, txn_id, 5)


