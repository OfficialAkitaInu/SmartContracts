from algosdk.v2client import algod
from algosdk.future import transaction
from algosdk import mnemonic
import os
import sys
os.chdir("/home/palmerss/Desktop/SmartContracts")
from contracts.AkitaTokenSwapper.deployment import deploy
from akita_inu_asa_utils import get_application_address, wait_for_txn_confirmation

swap_asset = 384303832
new_asset = 523683256

algod_address = "http://localhost:4001"
algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
client = algod.AlgodClient(algod_token, algod_address)
creator_mnemonic = "INPUT MNEMONIC HERE, DO NOT COMMIT YOUR MNEMONIC"
app_id = deploy(algod_address, algod_token, creator_mnemonic)


public_key = mnemonic.to_public_key(creator_mnemonic)
private_key = mnemonic.to_private_key(creator_mnemonic)

app_address = get_application_address(app_id)
params = client.suggested_params()
txn0 = transaction.PaymentTxn(public_key, params, app_address, 302000)
app_args = [
            swap_asset.to_bytes(8, "big"),
            new_asset.to_bytes(8, "big")
            ]
txn1 = transaction.ApplicationNoOpTxn(public_key, params, app_id, app_args, foreign_assets=[swap_asset, new_asset])

grouped = transaction.assign_group_id([txn0, txn1])
grouped = [grouped[0].sign(private_key),
           grouped[1].sign(private_key)]

txn_id = client.send_transactions(grouped)
wait_for_txn_confirmation(client, txn_id, 5)

print(app_id)
print(app_address)
