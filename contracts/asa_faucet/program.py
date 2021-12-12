
from akita_inu_asa_utils import *
from pyteal import *

from pyteal import *
import sys

def approval_program():
    # Keys for the global data stored by this smart contract.

    # AssetID that this smart contract will drip.
    asset_id_key = Bytes("asset_id")
    # Time in seconds to allow drip
    drip_time = Bytes("drip_time")
    drip_amount = Bytes("drip_amount")

    min_algo_amount = Bytes("min_algo_amount")
    min_asset_amount = Bytes("min_asset_amount")

    # keys for local data stored by this smart contract
    user_last_claim_time = Bytes("last_claim_time")

    @Subroutine(TealType.none)
    def on_get_drip():
        asset_holding = And(AssetHolding.balance(Txn.sender(), App.globalGet(asset_id_key)),
                            Balance(Txn.sender()) >= min_algo_amount)
        assert_fees = Assert(And(Global.group_size() == Int(2), Gtxn[0].amount() == Int(1000)))
        assert_time = Assert(Global.latest_timestamp() - user_last_claim_time >= drip_time)
        assert_has_volume = Assert(AssetHolding.balance(Global.current_application_address(), asset_id_key))

        claim = Seq(
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
        return Cond([And(asset_holding, assert_fees, assert_time, assert_has_volume), claim])

    on_create = Seq(
        App.globalPut(asset_id_key, Btoi(Txn.application_args[0])),
        App.globalPut(drip_time, Btoi(Txn.application_args[1])),
        App.globalPut(min_algo_amount, Btoi(Txn.application_args[2])),
        App.globalPut(min_asset_amount, Btoi(Txn.application_args[3])),
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
        [Txn.on_completion() == OnComplete.NoOp, on_get_drip],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_delete],
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

