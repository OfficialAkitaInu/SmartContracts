from algosdk.future import transaction
from algosdk import account, mnemonic, logic

import AkitaInuASAUtils as AIASAU


def deployApp(client, privateKey, approvalProgram, clearProgram, global_schema, local_schema):
    # define sender as creator
    publicKey = account.address_from_private_key(privateKey)

    # declare on_complete as NoOp
    onComplete = transaction.OnComplete.NoOpOC.real

    # get node suggested parameters
    params = client.suggested_params()

    signedTxn, txId = AIASAU.createAppSignedTxn(privateKey,
                              publicKey,
                              params,
                              onComplete,
                              approvalProgram,
                              clearProgram,
                              global_schema,
                              local_schema)

    # send transaction
    client.send_transactions([signedTxn])

    AIASAU.waitForTXnConfirmation(client, txId, 5)

    # display results
    transaction_response = client.pending_transaction_info(txId)
    app_id = transaction_response['application-index']
    print("Deployed new app-id:", app_id)

    return app_id

def deploy():
    developerConfig = AIASAU.loadDeveloperConfig()

    algodAddress = developerConfig['algodAddress']
    algodToken = developerConfig['algodToken']
    creator_mnemonic = developerConfig['creatorMnemonic']

    privateKey = mnemonic.to_private_key(creator_mnemonic)
    algodClient = AIASAU.getAlgodClient(algodToken,
                                 algodAddress)

    approvalProgram = AIASAU.loadCompiled(filePath='assetTimedVault_Approval.compiled')
    clearProgram = AIASAU.loadCompiled(filePath='assetTimedVault_Clear.compiled')

    globalSchema = AIASAU.loadSchema(filePath='globalSchema')
    localSchema = AIASAU.loadSchema(filePath='localSchema')

    deployApp(algodClient, privateKey, approvalProgram, clearProgram, globalSchema, localSchema)

