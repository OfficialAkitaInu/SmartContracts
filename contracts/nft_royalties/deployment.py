from .program import compile_transfer_app, compile_escrow_app
from algosdk.future import transaction
from algosdk import account, mnemonic, logic, encoding
from akita_inu_asa_utils import *
from pyteal import *


def deploy_app(client, private_key, approval_program, clear_program, global_schema, local_schema, app_args):
    # define sender as creator
    public_key = account.address_from_private_key(private_key)

    # declare on_complete as NoOp
    on_complete = transaction.OnComplete.NoOpOC.real

    # get node suggested parameters
    params = client.suggested_params()

    signed_txn, tx_id = create_app_signed_txn(private_key,
                                              public_key,
                                              params,
                                              on_complete,
                                              approval_program,
                                              clear_program,
                                              global_schema,
                                              local_schema,
                                              app_args)

    # send transaction
    client.send_transactions([signed_txn])

    wait_for_txn_confirmation(client, tx_id, 5)

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    app_id = transaction_response['application-index']
    print("Deployed new app-id: " + str(app_id))
    print("Deployed application address: " +
          encoding.encode_address(encoding.checksum(b'appID' + app_id.to_bytes(8, 'big'))))

    return app_id


# asset_id:         ASA's ID, hardcoded into transfer app
# royalty_percent:  The minimum percent that must be paid in royalty while
#                   while transferring our ASA
# royalty_payouts:  List of dictionaries specifying payout addresses and ratios
def deploy(algod_address, algod_token, creator_mnemonic, asset_id, royalty_percent, royalty_payouts):
    private_key = mnemonic.to_private_key(creator_mnemonic)
    public_key = account.address_from_private_key(private_key)
    algod_client = get_algod_client(algod_token,
                                    algod_address)

    compile_transfer_app(algod_client, asset_id, royalty_percent, royalty_payouts)
    print("Program Compiled")

    approval_program = load_compiled(file_path='nft_royalties/transfer.compiled')
    clear_program = load_compiled(file_path='nft_royalties/clear.compiled')

    global_schema = load_schema(file_path='nft_royalties/globalSchema')
    local_schema = load_schema(file_path='nft_royalties/localSchema')

    app_args = []

    transfer_app_id = deploy_app(algod_client,
                        private_key,
                        approval_program,
                        clear_program,
                        global_schema,
                        local_schema,
                        app_args)
    escrow_hash = compile_escrow_app(algod_client, transfer_app_id)

    txn = transaction.AssetConfigTxn(sender=public_key,
                                     sp=algod_client.suggested_params(),
                                     index=asset_id,
                                     strict_empty_address_check=False,
                                     clawback=escrow_hash)
    signed_txn = txn.sign(private_key)
    algod_client.send_transaction(signed_txn)

    return (transfer_app_id, escrow_hash)
