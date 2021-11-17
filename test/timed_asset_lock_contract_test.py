
import base64
import time

import pytest
from algosdk.v2client import algod
from algosdk import account, mnemonic, constants
from algosdk.encoding import encode_address, is_valid_address
from algosdk.error import AlgodHTTPError, TemplateInputError
from akita_inu_asa_utils import read_local_state, read_global_state


NUM_TEST_ASSET = int(1e6)


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
    from testing_utils import fund_account
    wallet_mnemonic, private_key, public_key = generate_new_account()

    wallet_1 = {'mnemonic': wallet_mnemonic, 'publicKey': public_key, 'privateKey': private_key}

    # fund the wallet
    fund_account(wallet_1['publicKey'], test_config['fund_account_Mnemonic'])
    return wallet_1

#this wallet is supposed to represent an adversarial wallet that is NOT meant to interact/change state of any portion of the app
@pytest.fixture(scope='class')
def wallet_2(test_config, asset_id, client):
    from akita_inu_asa_utils import generate_new_account, opt_in_asset_signed_txn
    from testing_utils import fund_account
    wallet_mnemonic, private_key, public_key = generate_new_account()
    wallet_2 = {'mnemonic': wallet_mnemonic, 'publicKey': public_key, 'privateKey': private_key}
    fund_account(wallet_2['publicKey'], test_config['fund_account_Mnemonic'])

    params = client.suggested_params()
    opt_in_asset_signed_txn(private_key, public_key, params, asset_id)
    return wallet_2


@pytest.fixture(scope='class')
def asset_id(test_config, wallet_1, client):
    from akita_inu_asa_utils import create_asa_signed_txn, \
        asset_id_from_create_txn, \
        wait_for_txn_confirmation
    params = client.suggested_params()
    txn, txn_id = create_asa_signed_txn(wallet_1['publicKey'],
                                        wallet_1['privateKey'],
                                        params,
                                        total=NUM_TEST_ASSET)
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


def assert_adversary_actions(app_id, wallet_2, client, asset_id, end_time):
    from pyteal import Return, Int, compileTeal, Approve, Mode
    from akita_inu_asa_utils import (opt_in_app_signed_txn,
                                     noop_app_signed_txn,
                                     delete_app_signed_txn,
                                     update_app_signed_txn,
                                     wait_for_txn_confirmation,
                                     close_out_app_signed_txn,
                                     clear_state_out_app_signed_txn,
                                     compile_program)

    # try to opt in as advesary
    params = client.suggested_params()
    public_key = wallet_2['publicKey']
    private_key = wallet_2['privateKey']
    txn, txn_id = opt_in_app_signed_txn(private_key,
                                        public_key,
                                        params,
                                        app_id,
                                        foreign_assets=[asset_id])
    with pytest.raises(AlgodHTTPError):
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

    # attempt to call application
    txn, txn_id = noop_app_signed_txn(private_key, public_key, params, app_id, [asset_id])
    with pytest.raises(AlgodHTTPError):
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

    # attempt to delete application
    txn, txn_id = delete_app_signed_txn(private_key, public_key, params, app_id, [asset_id])
    with pytest.raises(AlgodHTTPError):
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

    # attempt to update the program
    new_approval_program = compileTeal(Approve(), Mode.Application, version=5)
    new_clear_program = compileTeal(Approve(), Mode.Application, version=5)

    new_approval_program = compile_program(client, new_approval_program)
    new_clear_program = compile_program(client, new_clear_program)
    txn, txn_id = update_app_signed_txn(private_key,
                                        public_key,
                                        params,
                                        app_id,
                                        new_approval_program,
                                        new_clear_program)
    with pytest.raises(AlgodHTTPError):
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

    # attempt to close out application
    txn, txn_id = close_out_app_signed_txn(private_key,
                                           public_key,
                                           params,
                                           app_id,
                                           [asset_id])
    with pytest.raises(AlgodHTTPError):
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

    # attempt to clear application state
    txn, txn_id = clear_state_out_app_signed_txn(private_key,
                                                 public_key,
                                                 params,
                                                 app_id,
                                                 [asset_id])
    with pytest.raises(AlgodHTTPError):
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)


def cash_out(client, public_key, private_key, app_id, asset_ids):
    from akita_inu_asa_utils import delete_app_signed_txn, wait_for_txn_confirmation
    params = client.suggested_params()
    txn, txn_id = delete_app_signed_txn(private_key, public_key, params, app_id, asset_ids=asset_ids)
    client.send_transactions([txn])
    wait_for_txn_confirmation(client, txn_id, 5)


class TestTimedAssetLockContract:
    def test_build(self, client):
        from contracts.timed_asset_lock_contract.program import compile_app
        clear_build_folder()
        import os
        compile_app(client)
        assert os.path.exists('./build/assetTimedVault_Approval.compiled')
        assert os.path.exists('./build/assetTimedVault_Clear.compiled')
        assert os.path.exists('./build/assetTimedVault_Approval.teal')
        assert os.path.exists('./build/assetTimedVault_Clear.teal')
        assert os.path.exists('./build/globalSchema')
        assert os.path.exists('./build/globalSchema')

    def test_deploy(self, app_id, client, asset_id, wallet_1, wallet_2, end_time):
        from akita_inu_asa_utils import (
            getApplicationAddress,
            payment_signed_txn,
            wait_for_txn_confirmation
        )
        assert app_id
        public_key = wallet_1['publicKey']
        private_key = wallet_1['privateKey']

        local_state = read_local_state(client, public_key, app_id)
        global_state = read_global_state(client, public_key, app_id)
        assert_state(local_state, global_state, asset_id, public_key, end_time)

        # got to fund the contract with algo
        app_public_key = getApplicationAddress(app_id)

        params = client.suggested_params()
        txn, txn_id = payment_signed_txn(private_key,
                                         public_key,
                                         app_public_key, 300000, params)
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)
        assert_adversary_actions(app_id, wallet_2, client, asset_id, end_time)

    def test_on_setup(self, app_id, wallet_1, wallet_2, asset_id, client, end_time):
        from akita_inu_asa_utils import (
            noop_app_signed_txn,
            wait_for_txn_confirmation,
            getApplicationAddress,
            payment_signed_txn,
            get_asset_balance
        )
        params = client.suggested_params()
        public_key = wallet_1['publicKey']
        private_key = wallet_1['privateKey']

        txn, txn_id = noop_app_signed_txn(private_key,
                                          public_key,
                                          params,
                                          app_id,
                                          [asset_id])
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

        local_state = read_local_state(client, public_key, app_id)

        global_state = read_global_state(client, public_key, app_id)
        assert_state(local_state, global_state, asset_id, public_key, end_time)

        # got to fund the app with the asset NUM_TEST_ASSET - 1
        app_public_key = getApplicationAddress(app_id)
        assert get_asset_balance(client, public_key, asset_id) == NUM_TEST_ASSET
        assert 0 == get_asset_balance(client, app_public_key, asset_id)
        txn, txn_id = payment_signed_txn(private_key,
                                         public_key,
                                         app_public_key,
                                         NUM_TEST_ASSET - 1,
                                         params,
                                         asset_id=asset_id)
        client.send_transactions([txn])
        wait_for_txn_confirmation(client, txn_id, 5)

        assert get_asset_balance(client, public_key, asset_id) == 1
        assert NUM_TEST_ASSET - 1 == get_asset_balance(client, app_public_key, asset_id)
        assert_adversary_actions(app_id, wallet_2, client, asset_id, end_time)

    def test_on_opt_in(self, app_id, wallet_1, wallet_2, client, asset_id, end_time):
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

        local_state = read_local_state(client, public_key, app_id)
        global_state = read_global_state(client, public_key, app_id)
        assert_state(local_state, global_state, asset_id, public_key, end_time)
        assert_adversary_actions(app_id, wallet_2, client, asset_id, end_time)

# WARNING DELETE TESTS DO NOT WORK IF YOUR RUNNING SANDBOX IN DEV MODE DUE TO TIMESTAMPING IN DEV MODE
    def test_on_delete_too_soon(self, app_id, wallet_1, wallet_2, client, asset_id, end_time):
        from algosdk.error import AlgodHTTPError
        from akita_inu_asa_utils import (delete_app_signed_txn,
                                         wait_for_txn_confirmation,
                                         get_asset_balance,
                                         getApplicationAddress)

        public_key = wallet_1['publicKey']
        private_key = wallet_1['privateKey']
        params = client.suggested_params()

        txn, txn_id = delete_app_signed_txn(private_key, public_key, params, app_id, [asset_id])
        with pytest.raises(AlgodHTTPError):
            client.send_transactions([txn])
            wait_for_txn_confirmation(client, txn_id, 5)

        local_state = read_local_state(client, public_key, app_id)
        global_state = read_global_state(client, public_key, app_id)

        assert_state(local_state, global_state, asset_id, public_key, end_time)
        assert get_asset_balance(client, public_key, asset_id) == 1
        app_public_key = getApplicationAddress(app_id)
        assert NUM_TEST_ASSET - 1 == get_asset_balance(client, app_public_key, asset_id)
        assert_adversary_actions(app_id, wallet_2, client, asset_id, end_time)

    def test_on_delete_on_time(self, app_id, wallet_1, wallet_2, client, end_time, asset_id):
        from akita_inu_asa_utils import (delete_app_signed_txn,
                                         wait_for_txn_confirmation,
                                         getApplicationAddress,
                                         get_asset_balance)

        sleep_time = (end_time + 10) - int(time.time())

        time.sleep(sleep_time)

        # try to cash out as the adversarial wallet
        with pytest.raises(AlgodHTTPError):
            cash_out(client, wallet_2['publicKey'], wallet_2['privateKey'], app_id, [asset_id])

        # cash out as the intended wallet
        public_key = wallet_1['publicKey']
        private_key = wallet_1['privateKey']
        cash_out(client, public_key, private_key, app_id, [asset_id])

        local_state = read_local_state(client, public_key, app_id)
        global_state = read_global_state(client, public_key, app_id)
        assert local_state is None
        assert global_state is None

        assert get_asset_balance(client, public_key, asset_id) == NUM_TEST_ASSET
        app_public_key = getApplicationAddress(app_id)
        assert 0 == get_asset_balance(client, app_public_key, asset_id)
