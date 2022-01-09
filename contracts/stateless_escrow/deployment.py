from akita_inu_asa_utils import *


def generate_unsigned_deploy_txn(algod_client, sender_public_key, asset_id, asset_total_to_lock):
    compiled_teal = load_compiled(file_path='stateless_escrow_timed_lock.compiled')
    lsig_account = transaction.LogicSigAccount(compiled_teal)

    # get node suggested parameters
    params = algod_client.suggested_params()

    # fund with algos
    algo_fund = transaction.PaymentTxn(sender_public_key,
                                       params,
                                       lsig_account.address(),
                                       int(0.3 * 1e6))
    # opt escrow into asset
    opt_escrow_in = transaction.AssetTransferTxn(lsig_account.address(),
                                                 params,
                                                 lsig_account.address(),
                                                 0,
                                                 asset_id)
    #transfer the asset to the escrow
    asset_fund = transaction.AssetTransferTxn(sender_public_key,
                                              params,
                                              lsig_account.address(),
                                              asset_total_to_lock,
                                              asset_id)

    grouped = transaction.assign_group_id([algo_fund, opt_escrow_in, asset_fund])

    return grouped, lsig_account


def generate_unsigned_claim_txn(algod_client, client_public_key, asset_id):
    compiled_teal = load_compiled(file_path='stateless_escrow_timed_lock.compiled')
    lsig = transaction.LogicSigAccount(compiled_teal)

    params = algod_client.suggested_params()

    # close out asset
    asset_close_out = transaction.AssetTransferTxn(lsig.address(),
                                                   params,
                                                   lsig.address(),
                                                   0,
                                                   asset_id,
                                                   close_assets_to=client_public_key)
    # close out algos
    algo_close_out = transaction.PaymentTxn(lsig.address(),
                                            params,
                                            lsig.address(),
                                            0,
                                            close_remainder_to=client_public_key)

    grouped = transaction.assign_group_id([asset_close_out, algo_close_out])

    return grouped


def sign_claim_group(group):
    compiled_teal = load_compiled(file_path='stateless_escrow_timed_lock.compiled')
    lsig = transaction.LogicSigAccount(compiled_teal)
    txn1 = transaction.LogicSigTransaction(group[0], lsig)
    txn2 = transaction.LogicSigTransaction(group[1], lsig)
    transaction.write_to_file([txn1, txn2], './build/txnfile.txn')
    return [txn1,
            txn2]


def sign_deployment_group(group, private_key, lsig_account):
    return [group[0].sign(private_key),
              transaction.LogicSigTransaction(group[1], lsig_account),
              group[2].sign(private_key)]


# asset_id is the ASAs ID
# end time is the time to allow withdrawel from escrow
def deploy(algod_client, client_mnemonic, asset_id, asset_total_to_lock, end_time):

    private_key = mnemonic.to_private_key(client_mnemonic)
    public_key = account.address_from_private_key(private_key)

    grouped_txns, lsig_account = generate_unsigned_deploy_txn(algod_client,
                                                              public_key,
                                                              asset_id,
                                                              asset_total_to_lock)
    signed_group_txns = sign_deployment_group(grouped_txns, private_key, lsig_account)
    tx_id = algod_client.send_transactions(signed_group_txns)
    wait_for_txn_confirmation(algod_client, tx_id, 5)
    return lsig_account.address()

