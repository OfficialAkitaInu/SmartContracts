
import base64
import time

import pytest
from algosdk.v2client import algod
from algosdk import account, mnemonic, constants
from algosdk.encoding import encode_address, is_valid_address
from algosdk.error import AlgodHTTPError, TemplateInputError
from akita_inu_asa_utils import read_local_state, read_global_state, wait_for_txn_confirmation


NUM_TEST_ASSET = int(1e6)
ESCROW_TIME_LENGTH = int(90)


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


#this wallet is supposed to represent an adversarial wallet that is NOT meant to interact/change state of any portion of the app
@pytest.fixture(scope='class')
def wallet_2(test_config, asset_id, client):
    from akita_inu_asa_utils import generate_new_account, opt_in_asset_signed_txn
    from .testing_utils import fund_account
    wallet_mnemonic, private_key, public_key = generate_new_account()
    wallet_2 = {'mnemonic': wallet_mnemonic, 'public_key': public_key, 'private_key': private_key}
    fund_account(wallet_2['public_key'], test_config['fund_account_mnemonic'])

    params = client.suggested_params()
    txn, txn_id = opt_in_asset_signed_txn(private_key, public_key, params, asset_id)
    client.send_transactions([txn])
    wait_for_txn_confirmation(client, txn_id, 5)
    return wallet_2


@pytest.fixture(scope='class')
def asset_id(test_config, wallet_1, client):
    from akita_inu_asa_utils import( create_asa_signed_txn,
        asset_id_from_create_txn)
    params = client.suggested_params()
    txn, txn_id = create_asa_signed_txn(wallet_1['public_key'],
                                        wallet_1['private_key'],
                                        params,
                                        total=NUM_TEST_ASSET)
    client.send_transactions([txn])
    wait_for_txn_confirmation(client, txn_id, 5)
    return asset_id_from_create_txn(client, txn_id)


@pytest.fixture(scope='class')
def end_time():
    import time
    return int(time.time()) + ESCROW_TIME_LENGTH


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


def clear_build_folder():
    import os
    for file in os.scandir('./build'):
        os.remove(file.path)


def assert_state(local_state, global_state, asset_id, receiver_address, unlock_time):
    assert local_state is None
    assert len(global_state) == 3
    expected_vars = {b'asset_id': asset_id,
                    b'receiver_address_key': receiver_address,
                    b'unlock_time': unlock_time}

    # unfortunately it seems that values get put into program state randomly so I have to do this smelly stuff
    for i in range(0, 3):
        key = base64.b64decode(global_state[i]['key'])
        assert key in expected_vars.keys()
        if key == b'receiver_address_key':
            assert encode_address(base64.b64decode(global_state[i]['value']['bytes'])) == expected_vars[key]
        else:
            assert global_state[i]['value']['uint'] == expected_vars[key]


def assert_adversary_actions(app_id, wallet, client, asset_id,):
    from akita_inu_asa_utils import get_application_address
    public_key = wallet['public_key']
    private_key = wallet['private_key']

    with pytest.raises(AlgodHTTPError):
        send_3_group(public_key, private_key, get_application_address(app_id), app_id, 100000, 100000, asset_id, client)


def cash_out(client, public_key, private_key, app_id, asset_ids):
    from akita_inu_asa_utils import delete_app_signed_txn
    params = client.suggested_params()
    txn, txn_id = delete_app_signed_txn(private_key, public_key, params, app_id, asset_ids=asset_ids)
    client.send_transactions([txn])
    wait_for_txn_confirmation(client, txn_id, 5)


def opt_out(wallet, app_id, asset_ids, client):
    from akita_inu_asa_utils import clear_state_out_app_signed_txn

    params = client.suggested_params()
    public_key = wallet['public_key']
    private_key = wallet['private_key']
    txn, txn_id = clear_state_out_app_signed_txn(private_key,
                                                 public_key,
                                                 params,
                                                 app_id,
                                                 asset_ids)
    client.send_transactions([txn])
    wait_for_txn_confirmation(client, txn_id, 5)


def opt_in(public_key, private_key, params, app_public_key, app_id,asset_id, client):
    send_3_group(public_key, private_key, app_public_key, app_id, 0, 0, asset_id, client)


def send_3_group(public_key, private_key, app_public_key, app_id, numAlgos, numAsset, asset_id, client):
    from algosdk.future import transaction
    params = client.suggested_params()
    txn0 = transaction.PaymentTxn(public_key,
                                  params,
                                  app_public_key,
                                  numAlgos)
    txn1 = transaction.ApplicationOptInTxn(public_key,
                                           params,
                                           app_id,
                                           foreign_assets=[asset_id])

    txn2 = transaction.AssetTransferTxn(public_key,
                                        params,
                                        app_public_key,
                                        numAsset,
                                        asset_id)

    grouped = transaction.assign_group_id([txn0, txn1, txn2])
    grouped = [grouped[0].sign(private_key),
               grouped[1].sign(private_key),
               grouped[2].sign(private_key)]

    txn_id = client.send_transactions(grouped)
    wait_for_txn_confirmation(client, txn_id, 5)


def send_3_group_out_of_order(public_key, private_key, app_public_key, app_id, numAlgos, numAsset, asset_id, client):
    from algosdk.future import transaction
    params = client.suggested_params()
    txn2 = transaction.PaymentTxn(public_key,
                                  params,
                                  app_public_key,
                                  numAlgos)
    txn0 = transaction.ApplicationOptInTxn(public_key,
                                           params,
                                           app_id,
                                           foreign_assets=[asset_id])

    txn1 = transaction.AssetTransferTxn(public_key,
                                        params,
                                        app_public_key,
                                        numAsset,
                                        asset_id)

    grouped = transaction.assign_group_id([txn0, txn1, txn2])
    grouped = [grouped[0].sign(private_key),
               grouped[1].sign(private_key),
               grouped[2].sign(private_key)]

    txn_id = client.send_transactions(grouped)
    wait_for_txn_confirmation(client, txn_id, 5)

class TestTimedAssetLockContract:
    def test_build(self, client):
        from contracts.timed_asset_lock_contract.program import compile_app
        clear_build_folder()
        import os
        compile_app(client)
        assert os.path.exists('./build/asset_timed_vault_approval.compiled')
        assert os.path.exists('./build/asset_timed_vault_clear.compiled')
        assert os.path.exists('./build/asset_timed_vault_approval.teal')
        assert os.path.exists('./build/asset_timed_vault_clear.teal')
        assert os.path.exists('./build/globalSchema')
        assert os.path.exists('./build/globalSchema')

    def test_deploy(self, app_id, client, asset_id, wallet_1, wallet_2, end_time):
        assert app_id
        public_key = wallet_1['public_key']

        local_state = read_local_state(client, public_key, app_id)
        global_state = read_global_state(client, public_key, app_id)
        assert_state(local_state, global_state, asset_id, public_key, end_time)

    def test_3_group_out_of_order(self, client, app_id, wallet_1, wallet_2, asset_id, end_time):
        from akita_inu_asa_utils import (get_application_address, get_asset_balance)

        private_key = wallet_1['private_key']
        public_key = wallet_1['public_key']

        app_public_key = get_application_address(app_id)
        assert_adversary_actions(app_id, wallet_2, client, asset_id)
        local_state = read_local_state(client, public_key, app_id)
        global_state = read_global_state(client, public_key, app_id)
        assert_state(local_state, global_state, asset_id, public_key, end_time)
        # got to fund the contract with algo

        with pytest.raises(AlgodHTTPError):
            send_3_group_out_of_order(public_key, private_key, app_public_key, app_id, int(1e6 * 0.3), NUM_TEST_ASSET - 1,
                         asset_id, client)
        assert get_asset_balance(client, public_key, asset_id) == NUM_TEST_ASSET

        assert_adversary_actions(app_id, wallet_2, client, asset_id)
        local_state = read_local_state(client, public_key, app_id)
        global_state = read_global_state(client, public_key, app_id)
        assert_state(local_state, global_state, asset_id, public_key, end_time)

    def test_3_group(self, client, app_id, wallet_1, wallet_2, asset_id, end_time):
        from akita_inu_asa_utils import (get_application_address, get_asset_balance)

        private_key = wallet_1['private_key']
        public_key = wallet_1['public_key']

        app_public_key = get_application_address(app_id)
        assert_adversary_actions(app_id, wallet_2, client, asset_id)
        local_state = read_local_state(client, public_key, app_id)
        global_state = read_global_state(client, public_key, app_id)
        assert_state(local_state, global_state, asset_id, public_key, end_time)
        # got to fund the contract with algo

        send_3_group(public_key, private_key, app_public_key, app_id, int(1e6 * 0.3), NUM_TEST_ASSET - 1,
                     asset_id, client)
        assert get_asset_balance(client, app_public_key, asset_id) == NUM_TEST_ASSET - 1

        assert_adversary_actions(app_id, wallet_2, client, asset_id)
        local_state = read_local_state(client, public_key, app_id)
        global_state = read_global_state(client, public_key, app_id)
        assert_state(local_state, global_state, asset_id, public_key, end_time)

# WARNING DELETE TESTS DO NOT WORK IF YOUR RUNNING SANDBOX IN DEV MODE DUE TO TIMESTAMPING IN DEV MODE
    def test_on_delete_too_soon(self, app_id, wallet_1, wallet_2, client, asset_id, end_time):
        from algosdk.error import AlgodHTTPError
        from akita_inu_asa_utils import (delete_app_signed_txn,
                                         wait_for_txn_confirmation,
                                         get_asset_balance,
                                         get_application_address)

        public_key = wallet_1['public_key']
        private_key = wallet_1['private_key']
        params = client.suggested_params()

        txn, txn_id = delete_app_signed_txn(private_key, public_key, params, app_id, [asset_id])
        with pytest.raises(AlgodHTTPError):
            client.send_transactions([txn])
            wait_for_txn_confirmation(client, txn_id, 5)

        local_state = read_local_state(client, public_key, app_id)
        global_state = read_global_state(client, public_key, app_id)

        assert_state(local_state, global_state, asset_id, public_key, end_time)
        assert get_asset_balance(client, public_key, asset_id) == 1
        app_public_key = get_application_address(app_id)
        assert NUM_TEST_ASSET - 1 == get_asset_balance(client, app_public_key, asset_id)

    def test_on_delete_on_time(self, app_id, wallet_1, wallet_2, client, end_time, asset_id):
        from akita_inu_asa_utils import (get_application_address,
                                         get_asset_balance)

        sleep_time = (end_time + 10) - int(time.time())

        time.sleep(sleep_time)

        # try to cash out as the adversarial wallet
        with pytest.raises(AlgodHTTPError):
            cash_out(client, wallet_2['public_key'], wallet_2['private_key'], app_id, [asset_id])

        public_key = wallet_1['public_key']
        private_key = wallet_1['private_key']

        # try to cash out as the intended wallet, but not opted in
        opt_out(wallet_1, app_id, [asset_id], client)
        with pytest.raises(AlgodHTTPError):
            cash_out(client, public_key, private_key, app_id, [asset_id])
        
        # opt back in so you can fully cash out
        opt_in(public_key,private_key, client.suggested_params(), get_application_address(app_id), app_id, asset_id, client)

        cash_out(client, public_key, private_key, app_id, [asset_id])
        local_state = read_local_state(client, public_key, app_id)
        assert local_state is None
        global_state = read_global_state(client, public_key, app_id)
        assert global_state is None

        # check that balance had returned to the rightful owner
        assert get_asset_balance(client, public_key, asset_id) == NUM_TEST_ASSET
        app_public_key = get_application_address(app_id)
        assert 0 == get_asset_balance(client, app_public_key, asset_id)
