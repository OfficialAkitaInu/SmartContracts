"""
Massive thank you to the devs over on the Nekoin team, at the time of this commit our devs were all brand new to smart
contracts and still learning and ramping up on the whole process.
"""

from akita_inu_asa_utils import *
from pyteal import *

from pyteal import *
import sys


def approval_program():
    # Keys for the global data stored by this smart contract.

    # AssetID that this smart contract will freeze.
    asset_id_key = Bytes("asset_id")
    # Address of the wallet that will receive the funds in this smart contract when it is closed.
    receiver_address_key = Bytes("receiver_address_key")
    # Timestamp after which this smart contract can be closed.
    unlock_time_key = Bytes("unlock_time")

    # Sends all of the asset specified by assetID to the specified account.
    @Subroutine(TealType.none)
    def closeAssetsTo(assetID: Expr, account: Expr) -> Expr:
        asset_holding = AssetHolding.balance(Global.current_application_address(), assetID)
        return Seq(
            asset_holding,
            If(asset_holding.hasValue()).Then(
                Seq(
                    InnerTxnBuilder.Begin(),
                    InnerTxnBuilder.SetFields(
                        {
                            TxnField.type_enum: TxnType.AssetTransfer,
                            TxnField.xfer_asset: assetID,
                            TxnField.asset_close_to: account,
                        }
                    ),
                    InnerTxnBuilder.Submit(),
                )
            ),
        )

    # Sends all of the Algo's to the specified account.
    @Subroutine(TealType.none)
    def closeAccountTo(account: Expr) -> Expr:
        return If(Balance(Global.current_application_address()) != Int(0)).Then(
            Seq(
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.Payment,
                        TxnField.close_remainder_to: account,
                    }
                ),
                InnerTxnBuilder.Submit(),
            )
        )

    @Subroutine(TealType.uint64)
    def assert4Group() -> Expr:
        return And(Global.group_size() == Int(4),
                   Gtxn[1].on_completion() == OnComplete.OptIn,
                   Gtxn[3].on_completion() == OnComplete.NoOp)

    @Subroutine(TealType.uint64)
    def assert1Group() -> Expr:
        return Or(Global.group_size() == Int(1))

    # OnCreate handles creating this freeze smart contract.
    # arg[0]: the assetID of the asset we want to freeze. For Akita Inu ASA it is 384303832
    # arg[1]: the recipient of the assets held in this smart contract. Must be the creator.
    # arg[2]: the Unix timestamp of when this smart contract can be closed. When the
    #         contract is closed, everything is sent to the receiver.
    on_create_unlock_time = Btoi(Txn.application_args[2])
    on_create_receiver = Txn.application_args[1]
    on_create = Seq(
        Assert(
            And(
                # The unlock timestamp must be at some point in the future.
                # The transaction sender must be the recipient of the funds.
                Txn.sender() == on_create_receiver,
            ),
        ),
        App.globalPut(asset_id_key, Btoi(Txn.application_args[0])),
        App.globalPut(receiver_address_key, on_create_receiver),
        App.globalPut(unlock_time_key, on_create_unlock_time),
        Approve(),
    )

    # OnOptIn handles when a wallet request to opt into this smart contract. Only the
    # wallet receiving (and sending) the funds can opt into this smart contract.
    on_opt_in = Seq(
        Assert(
            # Only the original creator and receiver can opt into this smart contract.
            Gtxn[1].sender() == App.globalGet(receiver_address_key),
        ),
        Approve(),
    )

    # OnSetup handles setting up this freeze smart contract. Namely, it tells this smart
    # contract to opt into the asset it was created to hold. This smart contract must
    # hold enough Algo's to make this transaction.
    on_setup = Seq(
        Assert(
            And(
                # The wallet triggering the setup must be the original creator and receiver.
                Gtxn[2].sender() == App.globalGet(receiver_address_key),
                # Sender must be opted in
                App.optedIn(Gtxn[2].sender(), App.id()),
            )
        ),
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
        Approve(),
    )

    # OnDelete handles deleting the smart contract, which will trigger sending all the funds
    # held in this wallet to the receiver. This transaction will only be approved if the
    # latest_timestamp is after the unlock timestamp (the lock up has expired).
    on_delete = Seq(
        Assert(
            And(
                # The wallet triggering the close must be the original creator and receiver.
                Txn.sender() == App.globalGet(receiver_address_key),
                # The wallet must be opted in
                App.optedIn(Txn.sender(), App.id()),
                # The current timestamp must be greater than the unlock timestamp. Otherwise
                # this transaction will be rejected.
                App.globalGet(unlock_time_key) <= Global.latest_timestamp(),
            ),
        ),
        # These operations are only run if unlock timestamp has passed.
        # Close all the assets and Algo's held by this account to the receiver.
        closeAssetsTo(App.globalGet(asset_id_key), App.globalGet(receiver_address_key)),
        closeAccountTo(App.globalGet(receiver_address_key)),
        Approve(),
    )

    # Application router for this smart contract.
    program = Cond(
        [
            Or(
                # This smart contract cannot be closed out.
                Txn.on_completion() == OnComplete.CloseOut,
                # This smart contract cannot be updated.
                Txn.on_completion() == OnComplete.UpdateApplication,
                # This smart contract cannot be cleared of local state
                Txn.on_completion() == OnComplete.ClearState
            ),
            Reject(),
        ],

        # single transactions
        [And(assert1Group(), Txn.application_id() == Int(0)), on_create],
        [And(assert1Group(), Txn.on_completion() == OnComplete.DeleteApplication), on_delete],

        # four transaction
        [And(assert4Group(), Gtxn[Txn.group_index()].on_completion() == OnComplete.OptIn), on_opt_in],
        [And(assert4Group(), Txn.on_completion() == OnComplete.NoOp), on_setup],
    )

    return compileTeal(program, Mode.Application, version=5)


def clear_program():
    return compileTeal(Reject(), Mode.Application, version=5)


def compile_app(algod_client):
    dump_teal_assembly('asset_timed_vault_approval.teal', approval_program)
    dump_teal_assembly('asset_timed_vault_clear.teal', clear_program)

    compile_program(algod_client, approval_program(), 'asset_timed_vault_approval.compiled')
    compile_program(algod_client, clear_program(), 'asset_timed_vault_clear.compiled')

    write_schema(file_path='localSchema',
                 num_ints=0,
                 num_bytes=0)
    write_schema(file_path='globalSchema',
                 num_ints=3,
                 num_bytes=3)

