import base64
from algosdk.v2client import algod
from algosdk.future import transaction
from joblib import dump, load
import json
import os


def check_build_dir():
    if not os.path.exists('build'):
        os.mkdir('build')


def compile_program(client, source_code, file_path=None):
    compile_response = client.compile(source_code)
    if file_path == None:
        return base64.b64decode(compile_response['result'])
    else:
        check_build_dir()
        dump(base64.b64decode(compile_response['result']), 'build/' + file_path)


def dump_teal_assembly(file_path, program_fn_pointer):
    check_build_dir()
    with open('build/' + file_path, 'w') as f:
        compiled = program_fn_pointer()
        f.write(compiled)


def load_compiled(file_path):
    try:
        compiled = load('build/' + file_path)
    except:
        print("Error reading source file...exiting")
        exit(-1)
    return compiled


def load_developer_config(file_path='DeveloperConfig.json'):
    fp = open(file_path)
    return json.load(fp)


def get_algod_client(token, address):
    return algod.AlgodClient(token, address)


def write_schema(file_path, num_ints, num_bytes):
    schema = transaction.StateSchema(num_ints, num_bytes)
    dump(schema, 'build/' + file_path)


def load_schema(file_path):
    load('build/' + file_path)


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


def create_app_signed_txn(private_key,
                          public_key,
                          params,
                          on_complete,
                          approval_program,
                          clear_program,
                          global_schema,
                          local_schema):

    # create unsigned transaction
    txn = transaction.ApplicationCreateTxn(public_key,
                                           params,
                                           on_complete,
                                           approval_program,
                                           clear_program,
                                           global_schema,
                                           local_schema)

    # sign transaction
    signed_tx = txn.sign(private_key)
    txID = signed_tx.transaction.get_txid()
    return signed_tx, txID


def create_app_unsigned_txn(
                       public_key,
                       params,
                       on_complete,
                       approval_program,
                       clear_program,
                       global_schema,
                       local_schema):

    # create unsigned transaction
    txn = transaction.ApplicationCreateTxn(public_key,
                                           params,
                                           on_complete,
                                           approval_program,
                                           clear_program,
                                           global_schema,
                                           local_schema)
    return txn

