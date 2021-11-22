from pyteal import *
from akita_inu_asa_utils import *

CLIENT_ADDRESS_STRING = ""


def lock_escrow():
    client = Addr(CLIENT_ADDRESS_STRING)
    is_valid_fund = And(
        Global.group_size() == Int(3),
        # Seed with funds
        Gtxn[0].type_enum() == TxnType.Payment,
        Gtxn[0].sender() == client,
        Gtxn[0].amount() == Int(int(0.3 * 1e6)),  # 0.3 algos
        Gtxn[0].close_remainder_to() == Global.zero_address(),
        # Opt escrow into asset
        Gtxn[1].type_enum() == TxnType.AssetTransfer,
        Gtxn[1].asset_amount() == Int(0),
        Gtxn[1].asset_receiver() == Gtxn[1].sender(),
        Gtxn[1].asset_receiver() == Gtxn[0].receiver(),
        # Xfer asset from creator to escrow
        Gtxn[2].type_enum() == TxnType.AssetTransfer,
        Gtxn[2].asset_receiver() == Gtxn[0].receiver(),
        Gtxn[2].sender() == Gtxn[0].sender(),
        Gtxn[2].asset_close_to() == Global.zero_address(),
        Gtxn[2].xfer_asset() == Gtxn[1].xfer_asset(),
    )

    is_valid_claim = And(
        Global.group_size() == Int(2),
        Global.latest_timestamp() >= Int(0),
        # Close Asset to Client
        Gtxn[0].type_enum() == TxnType.AssetTransfer,
        Gtxn[0].asset_close_to() == client,
        Gtxn[0].asset_amount() == Int(0),

        # Close algos back to client
        Gtxn[1].type_enum() == TxnType.Payment,
        Gtxn[1].amount() == Int(0),
        Gtxn[1].close_remainder_to() == client,
    )

    return Cond(
        [Gtxn[0].sender() == client, Return(Or(is_valid_fund))],
        [Gtxn[0].sender() != client, Return(Or(is_valid_claim))],
    )


def get_contract():
    return compileTeal(
        lock_escrow(), mode=Mode.Signature, version=5, assembleConstants=True
    )


def compile_app(algod_client, client_address_string):
    global CLIENT_ADDRESS_STRING
    CLIENT_ADDRESS_STRING = client_address_string
    dump_teal_assembly('stateless_escrow_timed_lock.teal', get_contract)
    compile_program(algod_client, get_contract(), 'stateless_escrow_timed_lock.compiled')
