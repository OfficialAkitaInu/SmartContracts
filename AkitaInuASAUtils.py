import base64
from pyteal import *
from algosdk.v2client import algod
from algosdk.future import transaction
from joblib import dump, load
import json
import os


def checkBuildDir():
    if not os.path.exists('build'):
        os.mkdir('build')


def compileProgram(client, source_code, filePath=None):
    compile_response = client.compile(source_code)
    if filePath == None:
        return base64.b64decode(compile_response['result'])
    else:
        checkBuildDir()
        dump(base64.b64decode(compile_response['result']), 'build/' + filePath)


def dumpTealAssembly(filePath, programFnPointer):
    checkBuildDir()
    with open('build/' + filePath, 'w') as f:
        compiled = programFnPointer()
        f.write(compiled)


def loadCompiled(filePath):
    try:
        compiled = load('build/' + filePath)
    except:
        print("Error reading source file...exiting")
        exit(-1)
    return compiled

def loadDeveloperConfig(filePath='DeveloperConfig.json'):
    fp = open(filePath)
    return json.load(fp)

def getAlgodClient(token, address):
    return algod.AlgodClient(token, address)


def writeSchema(filePath, numInts, numBytes):
    schema = transaction.StateSchema(numInts, numBytes)
    dump(schema, 'build/' + filePath)


def loadSchema(filePath):
    load('build/' + filePath)


def waitForTXnConfirmation(client, transaction_id, timeout):
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

def createAppSignedTxn(privateKey,
                       publicKey,
                       params,
                       onComplete,
                       approvalProgram,
                       clearProgram,
                       globalSchema,
                       localSchema):

    # create unsigned transaction
    txn = transaction.ApplicationCreateTxn(publicKey,
                                           params,
                                           onComplete,
                                           approvalProgram,
                                           clearProgram,
                                           globalSchema,
                                           localSchema)

    # sign transaction
    signedTxn = txn.sign(privateKey)
    txID = signedTxn.transaction.get_txid()
    return signedTxn, txID

def createAppUnSignedTxn(
                       publicKey,
                       params,
                       onComplete,
                       approvalProgram,
                       clearProgram,
                       globalSchema,
                       localSchema):

    # create unsigned transaction
    txn = transaction.ApplicationCreateTxn(publicKey,
                                           params,
                                           onComplete,
                                           approvalProgram,
                                           clearProgram,
                                           globalSchema,
                                           localSchema)
    return txn

