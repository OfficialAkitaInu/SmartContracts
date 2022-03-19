import base64
import math
import os
import time

import pytest
from algosdk.v2client import algod
from algosdk import account, mnemonic, constants
from algosdk.future import transaction
from algosdk.encoding import encode_address, is_valid_address
from algosdk.error import AlgodHTTPError, TemplateInputError
from akita_inu_asa_utils import read_local_state, read_global_state, wait_for_txn_confirmation, get_application_address
from .testing_utils import clear_build_folder

TESTASSETNAME = "TEST"
TESTUNITNAME = "TESTU"
TESTNUMDECIMALS = 6
TESTSUPPLY = int(1e9) * 10**TESTNUMDECIMALS
TESTSWAPRATIO = 1
TESTURL = "TESTURL"
TESTMULTIPLY = 10**TESTNUMDECIMALS


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
    fund_account(wallet_1['public_key'], os.environ['fund_account_mnemonic'], 4000000)
    return wallet_1

@pytest.fixture(scope='class')
def new_asset(test_config, wallet_1, client):
    from akita_inu_asa_utils import (create_asa_signed_txn, asset_id_from_create_txn, wait_for_txn_confirmation)
    params = client.suggested_params()
    txn, txn_id = create_asa_signed_txn(wallet_1['public_key'], wallet_1['private_key'], params, total=int(1e9) * TESTMULTIPLY, decimals=6)
    client.send_transactions([txn])
    wait_for_txn_confirmation(client, txn_id, 5)
    return asset_id_from_create_txn(client, txn_id)

@pytest.fixture(scope='class')
def swap_asset(test_config, wallet_1, client):
    from akita_inu_asa_utils import (create_asa_signed_txn, asset_id_from_create_txn, wait_for_txn_confirmation)
    params = client.suggested_params()
    txn, txn_id = create_asa_signed_txn(wallet_1['public_key'], wallet_1['private_key'], params, total=int(1e9))
    client.send_transactions([txn])
    wait_for_txn_confirmation(client, txn_id, 5)
    return asset_id_from_create_txn(client, txn_id)

@pytest.fixture(scope='class')
def wallet_2(test_config, swap_asset, wallet_1, client):
    from akita_inu_asa_utils import generate_new_account, opt_in_asset_signed_txn, payment_signed_txn
    from .testing_utils import fund_account
    wallet_mnemonic, private_key, public_key = generate_new_account()
    wallet_2 = {'mnemonic': wallet_mnemonic, 'public_key': public_key, 'private_key': private_key}
    fund_account(wallet_2['public_key'], os.environ['fund_account_mnemonic'])

    params = client.suggested_params()
    txn, txn_id = opt_in_asset_signed_txn(private_key, public_key, params, swap_asset)
    client.send_transactions([txn])
    wait_for_txn_confirmation(client, txn_id, 5)

    params = client.suggested_params()
    txn, txn_id = payment_signed_txn(wallet_1['private_key'], wallet_1['public_key'], wallet_2['public_key'], 16000, params, swap_asset)
    client.send_transactions([txn])
    wait_for_txn_confirmation(client, txn_id, 5)
    return wallet_2

@pytest.fixture(scope='class')
def app_id(test_config, wallet_1, swap_asset):
    from contracts.AkitaTokenSwapper.deployment import deploy

    algod_address = test_config['algodAddress']
    algod_token = test_config['algodToken']
    creator_mnemonic = wallet_1['mnemonic']
    app_id = deploy(algod_address, algod_token, creator_mnemonic)
    return app_id

def opt_in_assets_txn(app_id, client, wallet_1, swap_asset, new_asset):
    public_key = wallet_1['public_key']
    private_key = wallet_1['private_key']

    app_address = get_application_address(app_id)
    params = client.suggested_params()
    txn0 = transaction.PaymentTxn(public_key, params, app_address, 302000)
    app_args = [
        swap_asset.to_bytes(8, "big"),
        new_asset.to_bytes(8, "big")
    ]
    txn1 = transaction.ApplicationNoOpTxn(public_key, params, app_id, app_args, foreign_assets=[swap_asset, new_asset])

    grouped = transaction.assign_group_id([txn0, txn1])
    grouped = [grouped[0].sign(private_key),
               grouped[1].sign(private_key)]

    txn_id = client.send_transactions(grouped)
    wait_for_txn_confirmation(client, txn_id, 5)

def swap(app_id, client, wallet_1, wallet_2, swap_asset, amount):
    public_key = wallet_2['public_key']
    private_key = wallet_2['private_key']
    new_asset = read_global_state(client, wallet_1["public_key"], app_id)["New_Asset_ID"]

    app_address = get_application_address(app_id)

    params = client.suggested_params()
    txn0 = transaction.AssetTransferTxn(public_key, params, public_key, 0, new_asset)
    txn1 = transaction.AssetTransferTxn(public_key, params, app_address, amount, swap_asset)
    app_args = []
    txn2 = transaction.ApplicationNoOpTxn(public_key, params, app_id, app_args, foreign_assets=[swap_asset, new_asset])
    txn2.fee = 2000
    grouped = transaction.assign_group_id([txn0, txn1, txn2])
    grouped = [grouped[0].sign(private_key),
               grouped[1].sign(private_key),
               grouped[2].sign(private_key)]

    txn_id = client.send_transactions(grouped)
    wait_for_txn_confirmation(client, txn_id, 5)

class TestAkitaTokenSwapperContract:
    def test_build(self, client):
        from contracts.AkitaTokenSwapper.program import compile_app
        clear_build_folder()
        import os
        compile_app(client)
        assert os.path.exists('./build/akita_token_swapper_approval.compiled')
        assert os.path.exists('./build/akita_token_swapper_clear.compiled')
        assert os.path.exists('./build/akita_token_swapper_approval.teal')
        assert os.path.exists('./build/akita_token_swapper_clear.teal')
        assert os.path.exists('./build/globalSchema')
        assert os.path.exists('./build/globalSchema')

    def test_deploy(self, app_id, client, swap_asset):
        assert app_id

    def test_optin(self, app_id, client, wallet_1, swap_asset, new_asset):
        opt_in_assets_txn(app_id, client, wallet_1, swap_asset, new_asset)
        public_key = wallet_1['public_key']
        global_state = read_global_state(client, public_key, app_id)
        local_state = read_local_state(client, public_key, app_id)
        assert global_state["Swap_Asset_ID"] == swap_asset
        assert global_state["New_Asset_ID"]
        assert local_state is None

        #try to configure twice (this shouldn't work)
        with pytest.raises(AlgodHTTPError):
            opt_in_assets_txn(app_id, client, wallet_1, swap_asset, new_asset)

    def test_fund(self, app_id, client, wallet_1, new_asset):
        app_address = get_application_address(app_id)
        txn = transaction.AssetTransferTxn(wallet_1['public_key'], client.suggested_params(), app_address, int(1e9) * TESTMULTIPLY, new_asset)
        txn = txn.sign(wallet_1['private_key'])
        txn_id = client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

    def test_swap_user_not_opted(self, app_id, client, wallet_2, swap_asset):
        public_key = wallet_2['public_key']
        private_key = wallet_2['private_key']

        app_address = get_application_address(app_id)
        params = client.suggested_params()

        txn0 = transaction.PaymentTxn(public_key, params, app_address, 1000)
        txn1 = transaction.AssetTransferTxn(public_key, params, app_address, 15999, app_id)
        app_args = [
            "swap".encode("utf-8"),
        ]
        txn2 = transaction.ApplicationNoOpTxn(public_key, params, app_id, app_args, foreign_assets=[swap_asset])

        grouped = transaction.assign_group_id([txn0, txn1, txn2])
        grouped = [grouped[0].sign(private_key),
                   grouped[1].sign(private_key),
                   grouped[2].sign(private_key)]

        with pytest.raises(AlgodHTTPError):
            txn_id = client.send_transactions(grouped)
            wait_for_txn_confirmation(client, txn_id, 5)

    def test_swap(self, app_id, client, wallet_1, wallet_2, swap_asset):
        from akita_inu_asa_utils import get_asset_balance
        public_key = wallet_2['public_key']
        swap(app_id, client, wallet_1, wallet_2, swap_asset, 16000)
        global_state = read_global_state(client, wallet_1["public_key"], app_id)
        local_state = read_local_state(client, public_key, app_id)
        assert global_state["Swap_Asset_ID"] == swap_asset
        assert global_state["New_Asset_ID"]
        assert local_state is None
        assert get_asset_balance(client, public_key, global_state["New_Asset_ID"]) / 10**TESTNUMDECIMALS == 16000
        #try to swap 0 tokens
        with pytest.raises(AlgodHTTPError):
            swap(app_id, client, wallet_1, wallet_2, swap_asset, 0)

