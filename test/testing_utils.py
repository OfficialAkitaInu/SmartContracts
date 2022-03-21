import json
from algosdk import mnemonic, account
from algosdk.error import IndexerHTTPError
from algosdk.v2client import indexer
from akita_inu_asa_utils import wait_for_txn_confirmation, \
    payment_signed_txn, \
    get_algod_client
import time


def load_test_config(file_path='./test/testConfig.json'):
    fp = open(file_path)
    return json.load(fp)

def clear_build_folder():
    import os
    for file in os.scandir('./build'):
        if not file.path.endswith('.gitkeep'):
            os.remove(file.path)


def fund_account(address, sender_mnemonic, initial_funds=2000000):
    test_config = load_test_config('./test/testConfig.json')
    private_key = mnemonic.to_private_key(sender_mnemonic)
    public_key = account.address_from_private_key(private_key)
    client = get_algod_client(test_config['algodToken'], test_config['algodAddress'])
    txn, txn_id = payment_signed_txn(
        private_key,
        public_key,
        address,
        initial_funds,
        client.suggested_params(),
    )
    client.send_transaction(txn)
    wait_for_txn_confirmation(client, txn_id, 5)


#WARNING INDEXER IS NOT AVAILABLE IN TESTNET/MAINNET
def indexer_client():
    """Instantiate and return Indexer client object."""

    indexer_address = "http://localhost:8980"
    indexer_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    return indexer.IndexerClient(indexer_token, indexer_address)


def transaction_info_indexer(transaction_id, indexer_timeout=61):
    """Return transaction with provided id."""
    timeout = 0
    while timeout < indexer_timeout:
        try:
            transaction = indexer_client().transaction(transaction_id)
            break
        except IndexerHTTPError:
            time.sleep(1)
            timeout += 1
    else:
        raise TimeoutError(
            "Timeout reached waiting for transaction to be available in indexer"
        )

    return transaction


def devnet_asset_id_from_create_txn(txn_id):
    return transaction_info_indexer(txn_id)['transaction']['created-asset-index']
