
from akita_inu_asa_utils import *
from pyteal import *

from pyteal import *
import sys

def approval_program():
    # Keys for the global data stored by this smart contract.

    # AssetID that this smart contract will drip.
    asset_id_key = Bytes("asset_id_key")
    # Time in seconds to allow drip
    drip_time = Bytes("drip_time")
    drip_amount = Bytes("drip_amount")

    min_algo_amount = Bytes("min_algo_amount")
    min_asset_amount = Bytes("min_asset_amount")

    # keys for local data stored by this smart contract
    user_last_claim_time = Bytes("user_last_claim_time")

    asset_balance = AssetHolding.balance(Txn.sender(), App.globalGet(asset_id_key))
    app_asset_balance = AssetHolding.balance(Global.current_application_address(), App.globalGet(asset_id_key))
    asset_holding = Assert(And(asset_balance.value() >= App.globalGet(min_asset_amount),
                        Balance(Txn.sender()) >= App.globalGet(min_algo_amount)))
    assert_fees = Assert(And(Global.group_size() == Int(2), Gtxn[0].amount() == Int(1000)))
    assert_time = Assert(Global.latest_timestamp() - App.localGet(Int(0), user_last_claim_time) >= App.globalGet(drip_time))
    assert_has_volume = Assert(app_asset_balance.value())

    on_get_drip = Seq(
        asset_balance,
        app_asset_balance,
        asset_holding,
        assert_fees,
        assert_time,
        assert_has_volume,
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.asset_receiver: Txn.sender(),
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: App.globalGet(asset_id_key),
                TxnField.asset_amount: App.globalGet(drip_amount),
            }
        ),
        InnerTxnBuilder.Submit(),
        App.localPut(Int(0), user_last_claim_time, Global.latest_timestamp()),
        Approve()
    )

    fund_faucet = Seq(
        Assert(And(Global.group_size() == Int(2),
                   Gtxn[0].type_enum() == TxnType.AssetTransfer,
                   Gtxn[0].asset_receiver() == Global.current_application_address(),
                   Gtxn[0].xfer_asset() == App.globalGet(asset_id_key),
                   Gtxn[0].asset_amount() > Int(0))),
        Approve()
    )

    on_opt_in_asset = Seq(
        Assert(And(Global.group_size() == Int(2),
                   Gtxn[0].type_enum() == TxnType.Payment,
                   Gtxn[0].amount() == Int(201000))),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                # Send 0 units of the asset to itself to opt-in.
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: App.globalGet(asset_id_key),
                TxnField.asset_receiver: Global.current_application_address(),
            }
        ),
        InnerTxnBuilder.Submit(),
        Approve()
    )

    on_create = Seq(
        App.globalPut(asset_id_key, Btoi(Txn.application_args[0])),
        App.globalPut(drip_time, Btoi(Txn.application_args[1])),
        App.globalPut(min_algo_amount, Btoi(Txn.application_args[2])),
        App.globalPut(min_asset_amount, Btoi(Txn.application_args[3])),
        App.globalPut(drip_amount, Btoi(Txn.application_args[4])),
        Approve(),
    )

    on_delete = Seq(
        Assert(Txn.sender() == Global.creator_address()),
        Approve(),
    )

    on_opt_in = Seq(
        App.localPut(Int(0), user_last_claim_time, Global.latest_timestamp()),
        Approve()
    )

    # Application router for this smart contract.
    program = Cond(
        [
            Or(
                # Your fees shouldn't exceed an unreasonable amount
                Txn.fee() > Int(4000),
                # No rekeys allowed (just to be safe)
                Txn.rekey_to() != Global.zero_address(),
                # This smart contract cannot be closed out.
                Txn.on_completion() == OnComplete.CloseOut,
                # This smart contract cannot be updated.
                Txn.on_completion() == OnComplete.UpdateApplication,
                # This smart contract cannot be cleared of local state
                Txn.on_completion() == OnComplete.ClearState,
            ),
            Reject(),
        ],

        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.OptIn, on_opt_in],
        [And(Txn.on_completion() == OnComplete.NoOp, Txn.application_args.length() == Int(1), Txn.application_args[0] == Bytes("opt_in_asset")), on_opt_in_asset],
        [And(Txn.on_completion() == OnComplete.NoOp, Txn.application_args.length() == Int(1), Txn.application_args[0] == Bytes("get_drip")), on_get_drip],
        [And(Txn.on_completion() == OnComplete.NoOp, Txn.application_args.length() == Int(1), Txn.application_args[0] == Bytes("fund_faucet")), fund_faucet],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_delete],
        [Int(1), Reject()]
    )

    return compileTeal(program, Mode.Application, version=5)


def clear_program():
    return compileTeal(Reject(), Mode.Application, version=5)


def compile_app(algod_client):
    dump_teal_assembly('asa_faucet_approval.teal', approval_program)
    dump_teal_assembly('asa_faucet_clear.teal', clear_program)

    compile_program(algod_client, approval_program(), 'asa_faucet_approval.compiled')
    compile_program(algod_client, clear_program(), 'asa_faucet_clear.compiled')

    write_schema(file_path='localSchema',
                 num_ints=1,
                 num_bytes=0)
    write_schema(file_path='globalSchema',
                 num_ints=5,
                 num_bytes=0)

