from algosdk.v2client import algod, indexer
from algosdk.future import transaction
from algosdk import encoding, account, mnemonic

import json
import os
import base64

BALANCE_PER_ASSET = 100000


def get_application_address(app_id):
    return encoding.encode_address(encoding.checksum(b'appID' + app_id.to_bytes(8, 'big')))


def check_build_dir():
    if not os.path.exists('build'):
        os.mkdir('build')


def get_asset_balance(client, public_key, asset_id):
    for asset in client.account_info(public_key)['assets']:
        if asset['asset-id'] == asset_id:
            return asset['amount']
    return 0


def is_opted_into_asset(client, public_key, asset_id):
    for asset in client.account_info(public_key)['assets']:
        print(asset['asset-id'])
        if asset['asset-id'] == asset_id:
            return True
    return False


def get_algo_balance(client, public_key):
    return client.account_info(public_key)['amount']

def get_min_algo_balance(number_assets):
    return BALANCE_PER_ASSET + (BALANCE_PER_ASSET * number_assets)

def generate_new_account():
    private_key, address = account.generate_account()
    return mnemonic.from_private_key(private_key), private_key, address


def delete_all_apps(client, private_key):
    public_key = account.address_from_private_key(private_key)
    apps = client.account_info(public_key)['created-apps']
    for app in apps:
        app_id = app['id']
        signed_txn, txn_id = delete_app_signed_txn(private_key, public_key, client.suggested_params(), app_id)
        try:
            client.send_transactions([signed_txn])
            wait_for_txn_confirmation(client, txn_id, 5)
            print("app: " + str(app_id) + " deleted")
        except:
            print("app: " + str(app_id) + " not deleted")


def compile_program(client, source_code, file_path=None):
    compile_response = client.compile(source_code)
    if file_path == None:
        return base64.b64decode(compile_response['result'])
    else:
        check_build_dir()
        fp = open('build/' + file_path, "wb")
        fp.write(base64.b64decode(compile_response['result']))
        fp.close()


# read user local state
def read_local_state(client, addr, app_id):
    results = client.account_info(addr)
    output = {}
    for app in results['apps-local-state']:
        if app['id'] == app_id:
            for key_value in app['key-value']:
                if key_value['value']['type'] == 1:
                    value = key_value['value']['bytes']
                else:
                    value = key_value['value']['uint']
                output[base64.b64decode(key_value['key']).decode()] = value
            return output

def get_translated_local_state(client, app_id, public_key):
    local_state = read_local_state(client, public_key, app_id)
    for key in local_state.keys():
        if type(local_state[key]) != int:
            local_state[key] = int.from_bytes(base64.b64decode(local_state[key]), "big")
    return local_state


# read app global state
def read_global_state(client, app_id):
    output = {}
    for key_value in client.application_info(app_id)['params']['global-state']:
        if key_value['value']['type'] == 1:
            value = base64.b64decode(key_value['value']['bytes'])
        else:
            value = key_value['value']['uint']
        output[base64.b64decode(key_value['key']).decode()] = value
    return output

def get_translated_global_state(client, app_id):
    global_state = read_global_state(client, app_id)
    for key in global_state.keys():
        if type(global_state[key]) != int:
            global_state[key] = int.from_bytes(global_state[key], "big")
    return global_state

def pretty_print_state(state):
    for keyvalue in state:
        print(base64.b64decode(keyvalue['key']))
        print(keyvalue['value'])
    print("\n\n\n")


def get_key_from_state(state, key):
    for i in range(0, len(state)):
        found_key = base64.b64decode(state[i]['key'])
        if found_key == key:
            if state[i]['value']['type'] == 1:
                return base64.b64decode(state[i]['value']['bytes'])
            elif state[i]['value']['type'] == 2:
                return state[i]['value']['uint']


def dump_teal_assembly(file_path, program_fn_pointer, args=None):
    check_build_dir()
    with open('build/' + file_path, 'w') as f:
        if args != None:
            compiled = program_fn_pointer(*args)
        else:
            compiled = program_fn_pointer()
        f.write(compiled)


def load_compiled(file_path):
    try:
        fp = open('build/' + file_path, "rb")
        compiled = fp.read()
        fp.close()
    except:
        print("Error reading source file...exiting")
        exit(-1)
    return compiled


def asset_id_from_create_txn(client, txn_id):
    ptx = client.pending_transaction_info(txn_id)
    asset_id = ptx["asset-index"]
    return asset_id


def load_developer_config(file_path='DeveloperConfig.json'):
    fp = open(file_path)
    return json.load(fp)


def get_algod_client(token, address):
    return algod.AlgodClient(token, address)


def write_schema(file_path, num_ints, num_bytes):
    f = open('build/' + file_path, "w")
    json.dump({"num_ints": num_ints,
               "num_bytes": num_bytes}, f)
    f.close()


def load_schema(file_path):
    f = open('build/' + file_path, 'r')
    stateJSON = json.load(f)
    return transaction.StateSchema(stateJSON['num_ints'], stateJSON['num_bytes'])


def wait_for_txn_confirmation(client, transaction_id, timeout):
    """
    Wait until the transaction is confirmed or rejected, or until 'timeout'
    number of rounds have passed.
    Args:
        transaction_id (str): the transaction to wait for
        timeout (int): maximum number of rounds to wait
    Returns:
        dict: pending transaction information, or throws an error if the transaction
            is not confirmed or rejected in the next timeout rounds
    """
    start_round = client.status()["last-round"] + 1
    current_round = start_round

    while current_round < start_round + timeout:
        try:
            pending_txn = client.pending_transaction_info(transaction_id)
        except Exception:
            return
        if pending_txn.get("confirmed-round", 0) > 0:
            return pending_txn
        elif pending_txn["pool-error"]:
            raise Exception(
                'pool error: {}'.format(pending_txn["pool-error"]))
        client.status_after_block(current_round)
        current_round += 1
    raise Exception(
        'pending tx not found in timeout rounds, timeout value = : {}'.format(timeout))


def sign_txn(unsigned_txn, private_key):
    """
        signs the provided unsigned transaction
            Args:
                unsigned_txn (???): transaction to be signed
                private_key (str): private key of sender
            Returns:
                ???: signed transaction
    """
    signed_tx = unsigned_txn.sign(private_key)
    return signed_tx


def send_transactions(client, transactions):
    transaction_id = client.send_transactions(transactions)
    wait_for_txn_confirmation(client, transaction_id, 5)
    return transaction_id

def get_remote_indexer(token="", address="https://algoindexer.algoexplorerapi.io/", headers={'User-Agent':'Random'}):
    return indexer.IndexerClient(token, address, headers)

def create_app_signed_txn(private_key,
                          public_key,
                          params,
                          on_complete,
                          approval_program,
                          clear_program,
                          global_schema,
                          local_schema,
                          app_args,
                          pages):
    """
        Creates an signed "create app" transaction to an application
            Args:
                private_key (str): private key of sender
                public_key (str): public key of sender
                params (???): parameters obtained from algod
                on_complete (???):
                approval_program (???): compiled approval program
                clear_program (???): compiled clear program
                global_schema (???): global schema variables
                local_schema (???): local schema variables
            Returns:
                tuple: Tuple containing the signed transaction and signed transaction id
    """
    unsigned_txn = transaction.ApplicationCreateTxn(public_key,
                                                    params,
                                                    on_complete,
                                                    approval_program,
                                                    clear_program,
                                                    global_schema,
                                                    local_schema,
                                                    app_args,
                                                    extra_pages=pages)
    signed_txn = sign_txn(unsigned_txn, private_key)
    return signed_txn, signed_txn.transaction.get_txid()


def update_app_signed_txn(private_key,
                          public_key,
                          params,
                          app_id,
                          approval_program,
                          clear_program,
                          app_args=None):
    """
        Creates an signed "update app" transaction to an application
            Args:
                private_key (str): private key of sender
                public_key (str): public key of sender
                params (???): parameters obtained from algod
                app_id (int): app id to be updated
                approval_program (???): compiled approval program
                clear_program (???): compiled clear program
                app_args (???): app arguments
            Returns:
                tuple: Tuple containing the signed transaction and signed transaction id
    """

    unsigned_txn = transaction.ApplicationUpdateTxn(public_key,
                                                    params,
                                                    app_id,
                                                    approval_program,
                                                    clear_program,
                                                    app_args)

    signed_txn = sign_txn(unsigned_txn, private_key)
    return signed_txn, signed_txn.transaction.get_txid()


def opt_in_app_signed_txn(private_key,
                          public_key,
                          params,
                          app_id,
                          foreign_assets=None,
                          app_args=None):
    """
    Creates and signs an "opt in" transaction to an application
        Args:
            private_key (str): private key of sender
            public_key (str): public key of sender
            params (???): parameters obtained from algod
            app_id (int): id of application
        Returns:
            tuple: Tuple containing the signed transaction and signed transaction id
    """
    txn = transaction.ApplicationOptInTxn(public_key,
                                          params,
                                          app_id,
                                          foreign_assets=foreign_assets,
                                          app_args=app_args)
    signed_txn = sign_txn(txn, private_key)
    return signed_txn, signed_txn.transaction.get_txid()


def opt_in_asset_signed_txn(private_key,
                            public_key,
                            params,
                            asset_id):
    txn = transaction.AssetOptInTxn(public_key,
                                    params,
                                    asset_id)
    signed_txn = sign_txn(txn, private_key)
    return signed_txn, signed_txn.transaction.get_txid()


def noop_app_signed_txn(private_key,
                        public_key,
                        params,
                        app_id,
                        app_args=None,
                        asset_ids=None):
    """
    Creates and signs an "noOp" transaction to an application
        Args:
            private_key (str): private key of sender
            public_key (str): public key of sender
            params (???): parameters obtained from algod
            app_id (int): id of application
            asset_id (int): id of asset if any
        Returns:
            tuple: Tuple containing the signed transaction and signed transaction id
    """
    txn = transaction.ApplicationNoOpTxn(public_key,
                                         params,
                                         app_id,
                                         app_args=app_args,
                                         foreign_assets=asset_ids)
    signed_txn = sign_txn(txn, private_key)
    return signed_txn, signed_txn.transaction.get_txid()


def close_out_app_signed_txn(private_key,
                             public_key,
                             params,
                             app_id,
                             asset_ids=None):
    """
    Creates and signs an "close out" transaction to an application
        Args:
            private_key (str): private key of sender
            public_key (str): public key of sender
            params (???): parameters obtained from algod
            app_id (int): id of application
            asset_ids (list<int>): ids of assets if any
        Returns:
            tuple: Tuple containing the signed transaction and signed transaction id
    """

    txn = transaction.ApplicationCloseOutTxn(public_key,
                                             params,
                                             app_id,
                                             foreign_assets=asset_ids)
    signed_txn = sign_txn(txn, private_key)
    return signed_txn, signed_txn.transaction.get_txid()


def clear_state_out_app_signed_txn(private_key,
                                   public_key,
                                   params,
                                   app_id,
                                   asset_ids=None):
    """
        Creates and signs an "clear state" transaction to an application
            Args:
                private_key (str): private key of sender
                public_key (str): public key of sender
                params (???): parameters obtained from algod
                app_id (int): id of application
                asset_ids (list<int>): ids of assets if any
            Returns:
                tuple: Tuple containing the signed transaction and signed transaction id
    """
    txn = transaction.ApplicationClearStateTxn(public_key,
                                               params,
                                               app_id,
                                               foreign_assets=asset_ids)

    signed_txn = sign_txn(txn, private_key)
    return signed_txn, signed_txn.transaction.get_txid()


def delete_app_signed_txn(private_key,
                          public_key,
                          params,
                          app_id,
                          asset_ids=None):
    """
        Creates and signs an "delete app" transaction to an application
            Args:
                private_key (str): private key of sender
                public_key (str): public key of sender
                params (???): parameters obtained from algod
                app_id (int): id of application
                asset_ids (list<int>): ids of assets if any
            Returns:
                tuple: Tuple containing the signed transaction and signed transaction id
    """

    txn = transaction.ApplicationDeleteTxn(public_key,
                                           params,
                                           app_id,
                                           foreign_assets=asset_ids)
    signed_txn = sign_txn(txn, private_key)
    return signed_txn, signed_txn.transaction.get_txid()


def create_asa_signed_txn(public_key, private_key, params, name="FOO", total=1e6, default_frozen=False, decimals=0):
    """
        Creates and signs an "create asa" transaction to an application
            Args:
                public_key (str): public key of sender
                private_key (str): private key of sender
                params (???): parameters obtained from algod
                name (str): name of the asset
                total (int): total supply of the asset
                default_frozen (bool): the assets frozen state
                decimals (int): number of decimal places
            Returns:
                tuple: Tuple containing the signed transaction and signed transaction id
    """
    txn = transaction.AssetConfigTxn(
        sender=public_key,
        sp=params,
        asset_name=name,
        total=total,
        default_frozen=default_frozen,
        manager=public_key,
        reserve=public_key,
        freeze=public_key,
        clawback=public_key,
        url="https://path/to/my/asset/details",
        decimals=decimals)

    signed_txn = sign_txn(txn, private_key)
    return signed_txn, signed_txn.transaction.get_txid()


def payment_signed_txn(sender_private_key,
                       sender_public_key,
                       receiver_public_key,
                       amount,
                       params,
                       asset_id=None):
    """
        Creates and signs an "payment" transaction to an application, this works with algo or asa
            Args:
                sender_private_key (str): private key of sender
                sender_public_key (str): public key of sender
                receiver_public_key (str): public key of receiver
                amount (int): number of tokens/asset to send
                params (???): parameters obtained from algod
                asset_id (int): id of assets if any
            Returns:
                tuple: Tuple containing the signed transaction and signed transaction id
    """
    if asset_id is None:
        txn = transaction.PaymentTxn(sender_public_key,
                                     params,
                                     receiver_public_key,
                                     amount)

    else:
        txn = transaction.AssetTransferTxn(sender_public_key,
                                           params,
                                           receiver_public_key,
                                           amount,
                                           asset_id)

    signed_txn = sign_txn(txn, sender_private_key)
    return signed_txn, signed_txn.transaction.get_txid()

