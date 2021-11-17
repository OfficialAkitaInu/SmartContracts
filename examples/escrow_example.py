import base64

from algosdk.future import transaction
from algosdk import mnemonic
from algosdk.v2client import algod
from pyteal import *

# user declared account mnemonics
benefactor_mnemonic = "REPLACE WITH YOUR OWN MNEMONIC"
sender_mnemonic = "REPLACE WITH YOUR OWN MNEMONIC"

# user declared algod connection parameters. Node must have EnableDeveloperAPI set to true in its config
algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

# helper function to compile_app program source
def compile_smart_signature(client, source_code):
    compile_response = client.compile_app(source_code)
    return compile_response['result'], compile_response['hash']

# helper function that converts a mnemonic passphrase into a private signing key
def get_private_key_from_mnemonic(mn) :
    private_key = mnemonic.to_private_key(mn)
    return private_key

# helper function that waits for a given txid to be confirmed by the network
def wait_for_confirmation(client, transaction_id, timeout):
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

def payment_transaction(creator_mnemonic, amt, rcv, algod_client)->dict:
    params = algod_client.suggested_params()
    add = mnemonic.to_public_key(creator_mnemonic)
    key = mnemonic.to_private_key(creator_mnemonic)
    unsigned_txn = transaction.PaymentTxn(add, params, rcv, amt)
    signed = unsigned_txn.sign(key)
    txid = algod_client.send_transaction(signed)
    pmtx = wait_for_confirmation(algod_client, txid , 5)
    return pmtx

def send_asset_optin_transaction(escrow_prog, escrow_address, asset, algod_client)->dict:
    params = algod_client.suggested_params()
    #unsigned_txn = transaction.AssetOptInTxn(escrow_address, params, asset)
    unsigned_txn = transaction.AssetTransferTxn(escrow_address, params, escrow_address, int(0), asset)
    encodedProg = escrow_prog.encode()
    program = base64.decodebytes(encodedProg)
    lsig = transaction.LogicSig(program)
    stxn = transaction.LogicSigTransaction(unsigned_txn, lsig)
    tx_id = algod_client.send_transaction(stxn)
    pmtx = wait_for_confirmation(algod_client, tx_id, 10)
    return pmtx

def send_asset_transaction(creator_mnemonic, amt, asset, rcv, algod_client)->dict:
    params = algod_client.suggested_params()
    add = mnemonic.to_public_key(creator_mnemonic)
    key = mnemonic.to_private_key(creator_mnemonic)
    unsigned_txn = transaction.AssetTransferTxn(add, params, rcv, amt, asset)
    signed = unsigned_txn.sign(key)
    txid = algod_client.send_transaction(signed)
    pmtx = wait_for_confirmation(algod_client, txid , 5)
    return pmtx

def lsig_payment_txn(escrowProg, escrow_address, amt, rcv, algod_client):
    params = algod_client.suggested_params()
    unsigned_txn = transaction.PaymentTxn(escrow_address, params, rcv, amt)
    encodedProg = escrowProg.encode()
    program = base64.decodebytes(encodedProg)
    lsig = transaction.LogicSig(program)
    stxn = transaction.LogicSigTransaction(unsigned_txn, lsig)
    tx_id = algod_client.send_transaction(stxn)
    pmtx = wait_for_confirmation(algod_client, tx_id, 10)
    return pmtx 

def lsig_send_asset_txn(escrowProg, escrow_address, amt, asset, rcv, algod_client):
    params = algod_client.suggested_params()
    unsigned_txn = transaction.AssetTransferTxn(escrow_address, params, rcv, amt, asset)
    encodedProg = escrowProg.encode()
    program = base64.decodebytes(encodedProg)
    lsig = transaction.LogicSig(program)
    stxn = transaction.LogicSigTransaction(unsigned_txn, lsig)
    tx_id = algod_client.send_transaction(stxn)
    pmtx = wait_for_confirmation(algod_client, tx_id, 10)
    return pmtx 

def lsig_send_optin_txn(escrowProg, escrow_address, asset, algod_client):
    params = algod_client.suggested_params()
    unsigned_txn = transaction.AssetTransferTxn(escrow_address, params, escrow_address, int(0), asset)
    encodedProg = escrowProg.encode()
    program = base64.decodebytes(encodedProg)
    lsig = transaction.LogicSig(program)
    stxn = transaction.LogicSigTransaction(unsigned_txn, lsig)
    tx_id = algod_client.send_transaction(stxn)
    pmtx = wait_for_confirmation(algod_client, tx_id, 10)
    return pmtx 

"""Basic Donation Escrow"""

def donation_escrow(benefactor):
    Fee = Int(1000)

    #Only the benefactor account can withdraw from this escrow
    program = And(
        Txn.type_enum() == TxnType.Payment,
        Txn.fee() <= Fee,
        Txn.asset_receiver() == Addr(benefactor),
        Global.group_size() == Int(1),
        Txn.first_valid() >= Int(17839475),
        Txn.created_asset_id() == Int(44314784),
        Txn.rekey_to() == Global.zero_address()
    )

    # Mode.Signature specifies that this is a smart signature
    return compileTeal(program, Mode.Signature, version=2)

"""Basic Donation Asset Escrow"""

def donation_asset_escrow(benefactor, algod_client):
    Fee = Int(1000)

    #Only the benefactor account can withdraw from this escrow
    program = And(
        Txn.type_enum() == TxnType.AssetTransfer,
        Txn.fee() <= Fee,
        Or(Txn.asset_receiver() == Addr(benefactor), And(Txn.asset_amount() == Int(0), Txn.amount() == Int(0))),
        Global.group_size() == Int(1),
        Txn.first_valid() >= Int(17839475),
        Txn.xfer_asset() == Int(44314784),
        Txn.rekey_to() == Global.zero_address()
    )

    # Mode.Signature specifies that this is a smart signature
    return compileTeal(program, Mode.Signature, version=5)

def main() :
    # initialize an algodClient
    algod_client = algod.AlgodClient(algod_token, algod_address)

    # define private keys
    receiver_public_key = mnemonic.to_public_key(benefactor_mnemonic)

    print("--------------------------------------------")
    print("Compiling Donation Smart Signature......")

    #stateless_program_teal = donation_escrow(receiver_public_key)
    stateless_program_teal = donation_asset_escrow(receiver_public_key, algod_client)
    escrow_result, escrow_address = compile_smart_signature(algod_client, stateless_program_teal)

    print("Program:", escrow_result)
    print("hash: ", escrow_address)

    print("--------------------------------------------")
    print("Activating Donation Smart Signature......")

    # Activate escrow contract by sending 2 algo and 1000 microalgo for transaction fee from creator
    amt = 1000000
    payment_transaction(sender_mnemonic, amt, escrow_address, algod_client)

    send_asset_optin_transaction(escrow_result, escrow_address, int(44314784), algod_client)
    lsig_send_optin_txn(escrow_result, escrow_address, int(44314784), algod_client)

    # send asset
    amt = 250
    send_asset_transaction(sender_mnemonic, amt, int(44314784), escrow_address, algod_client)

    print("--------------------------------------------")
    print("Withdraw from Donation Smart Signature......")

    # Withdraws some assets.
    withdrawal_amt = 125
    lsig_send_asset_txn(escrow_result, escrow_address, withdrawal_amt, int(44314784), receiver_public_key, algod_client)

    #withdrawal_amt = 397000
    #lsig_payment_txn(escrow_result, escrow_address, withdrawal_amt, receiver_public_key, algod_client)

main()

