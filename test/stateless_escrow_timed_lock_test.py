
import base64
import time
from algosdk.testing.dryrun import DryrunRequest
import pytest
from algosdk.v2client import algod
from algosdk import account, mnemonic, constants
from algosdk.encoding import encode_address, is_valid_address
from algosdk.error import AlgodHTTPError, TemplateInputError
from akita_inu_asa_utils import wait_for_txn_confirmation


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


#@pytest.fixture(scope='class')
def wallet_1(test_config):
    from akita_inu_asa_utils import generate_new_account
    from .testing_utils import fund_account
    wallet_mnemonic, private_key, public_key = generate_new_account()

    wallet_1 = {'mnemonic': wallet_mnemonic, 'public_key': public_key, 'private_key': private_key}

    # fund the wallet
    fund_account(wallet_1['public_key'], test_config['fund_account_mnemonic'])
    return wallet_1


@pytest.fixture(scope='class')
def wallet_2(test_config, asset_id, client):
    from akita_inu_asa_utils import generate_new_account, opt_in_asset_signed_txn
    from .testing_utils import fund_account
    wallet_mnemonic, private_key, public_key = generate_new_account()
    wallet_2 = {'mnemonic': wallet_mnemonic, 'public_key': public_key, 'private_key': private_key}
    fund_account(wallet_2['public_key'], test_config['fund_account_mnemonic'])

    params = client.suggested_params()
    opt_in_asset_signed_txn(private_key, public_key, params, asset_id)
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
def escrow_address(client, test_config, asset_id, end_time, wallet_1):
    from contracts.stateless_escrow.deployment import deploy
    creator_mnemonic = wallet_1['mnemonic']
    escrow_address = deploy(client, creator_mnemonic, asset_id, NUM_TEST_ASSET - 1, end_time)
    return escrow_address


def clear_build_folder():
    import os
    for file in os.scandir('./build'):
        os.remove(file.path)


def assert_adversary_actions(app_id, wallet, client, asset_id, adversary_wallet=True, fail_clear=False):
    pass


def cash_out(client, public_key, private_key, app_id, asset_ids):
    pass


class TestTimedAssetLockContract:
    def test_build(self, client, wallet_1):
        from contracts.stateless_escrow.program import compile_app
        clear_build_folder()
        import os
        compile_app(client, wallet_1['public_key'])
        assert os.path.exists('./build/stateless_escrow_timed_lock.compiled')
        assert os.path.exists('./build/stateless_escrow_timed_lock.teal')

    def test_deploy(self, escrow_address, client, asset_id, wallet_1, wallet_2, end_time):
        from akita_inu_asa_utils import get_asset_balance
        assert escrow_address
        assert 1 == get_asset_balance(client, wallet_1['public_key'], asset_id)

    def test_claim(self, client, wallet_1, escrow_address, asset_id):
        from akita_inu_asa_utils import get_asset_balance
        from contracts.stateless_escrow.deployment import sign_claim_group, generate_unsigned_claim_txn
        claim_group = sign_claim_group(generate_unsigned_claim_txn(client,
                                                                   wallet_1['public_key'],
                                                                   asset_id))

        tx_id = client.send_transactions(claim_group)
        wait_for_txn_confirmation(client, tx_id, 5)
        assert 0 == get_asset_balance(client, escrow_address, asset_id)
        assert NUM_TEST_ASSET == get_asset_balance(client, wallet_1['public_key'], asset_id)
