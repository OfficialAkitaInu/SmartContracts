'''
This tool is meant to be a CLI help tool that lets you fill in information about the various interactions and
transactiosn with the timed_asset_lock_contract and to dump the transaction to a base64 string which could then
be used with tools with non power users
'''

from algosdk.future import transaction
from algosdk import encoding
from akita_inu_asa_utils import get_algod_client, load_developer_config, load_compiled, load_schema
from .program import compile_app


alreadyCollected = {}


def collect_info(info_key, store=True):
    if info_key in alreadyCollected.keys():
        return alreadyCollected[info_key]
    value = input("Enter " + info_key + "\n")
    if store:
        alreadyCollected[info_key] = value
    return value


def main():
    config = load_developer_config()
    client = get_algod_client(config["algodToken"], config["algodAddress"])
    selection = int(input("Select Transaction To Build...\n"
                          "1.) App Creation \n"
                          "2.) Pay Algo \n"
                          "3.) App Opt In \n"
                          "4.) App Setup \n"
                          "5.) Pay Asset \n"
                          "6.) App Delete \n"
                          "7.) Exit Utility \n"))
    txn = None
    if selection == 1:
        compile_app(client)
        txn = transaction.ApplicationCreateTxn(sender=collect_info("sender public key"),
                                               sp=client.suggested_params(),
                                               on_complete=transaction.OnComplete.NoOpOC.real,
                                               approval_program=load_compiled(file_path='asset_timed_vault_approval.compiled'),
                                               clear_program=load_compiled(file_path='asset_timed_vault_clear.compiled'),
                                               global_schema=load_schema(file_path='globalSchema'),
                                               local_schema=load_schema(file_path='localSchema'),
                                               app_args=[int(collect_info("asset id")).to_bytes(8, "big"),
                                                         encoding.decode_address(str(collect_info("escrow receiver"))),
                                                         int(collect_info("end time unix UTC")).to_bytes(8, "big")]
                                               )
    elif selection == 2:
        txn = transaction.PaymentTxn(sender=collect_info("sender public key"),
                                     sp=client.suggested_params(),
                                     receiver=collect_info("escrow address"),
                                     amt=int(1.3 * 1e6))  # microAlgos
    elif selection == 3:
        txn = transaction.ApplicationOptInTxn(sender=collect_info("sender public key"),
                                              sp=client.suggested_params(),
                                              index=int(collect_info("app id")),
                                              foreign_assets=[int(collect_info("asset id"))],)
    elif selection == 4:
        txn = transaction.ApplicationNoOpTxn(sender=collect_info("sender public key"),
                                             sp=client.suggested_params(),
                                             index=int(collect_info("app id")),
                                             foreign_assets=[int(collect_info("asset id"))])
    elif selection == 5:
        txn = transaction.AssetTransferTxn(sender=collect_info("sender public key"),
                                           sp=client.suggested_params(),
                                           receiver=collect_info("escrow address"),
                                           amt=int(collect_info("asset amount to send", False)),
                                           index=int(int(collect_info("asset id"))))
    elif selection == 6:
        txn = transaction.ApplicationDeleteTxn(sender=collect_info("sender public key"),
                                               sp=client.suggested_params(),
                                               index=int(collect_info("app id")),
                                               foreign_assets=[int(collect_info("asset id"))])
    elif selection == 7:
        exit()

    print("\n" + encoding.msgpack_encode(txn) + "\n")
    main()


main()
