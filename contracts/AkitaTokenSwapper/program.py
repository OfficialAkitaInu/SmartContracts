from akita_inu_asa_utils import *

from pyteal import *


def approval_program():

    swap_asset_ID = Bytes("Swap_Asset_ID")
    new_asset_ID = Bytes("New_Asset_ID")
    multiplier = Bytes("Multiply")

    swap_asset_balance = AssetHolding.balance(Txn.sender(), App.globalGet(swap_asset_ID))
    new_asset_balance = AssetHolding.balance(Txn.sender(), App.globalGet(new_asset_ID))
    asset_decimal = AssetParam.decimals(App.globalGet(new_asset_ID))

    @Subroutine(TealType.none)
    def opt_into_asset(asset_id):
       return Seq(
           InnerTxnBuilder.Begin(),
           InnerTxnBuilder.SetFields
            (
               {
                   TxnField.type_enum: TxnType.AssetTransfer,
                   TxnField.xfer_asset: asset_id,
                   TxnField.asset_receiver: Global.current_application_address(),
               }
           ),
           InnerTxnBuilder.Submit(),
       )

    @Subroutine(TealType.none)
    def swap_token(amount_to_swap):
        return Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.asset_receiver: Txn.sender(),
                    TxnField.asset_amount: amount_to_swap,
                    TxnField.xfer_asset: App.globalGet(new_asset_ID),
                }
            ),
            InnerTxnBuilder.Submit(),
        )

    opt_in_assets = Seq(
        Assert(And(
                   App.globalGet(swap_asset_ID) == Int(0),
                   App.globalGet(new_asset_ID) == Int(0),
                   Global.group_size() == Int(2),
                   Gtxn[0].type_enum() == TxnType.Payment,
                   Gtxn[0].receiver() == Global.current_application_address(),
                   Gtxn[0].sender() == Global.creator_address(),
                   Gtxn[0].amount() == Int(801000),

                   Gtxn[1].application_args.length() == Int(3),
                   Gtxn[1].application_id() == Global.current_application_id(),
                   Gtxn[1].on_completion() == OnComplete.NoOp)
               ),

        opt_into_asset(Btoi(Txn.application_args[1])),
        opt_into_asset(Btoi(Txn.application_args[2])),
        App.globalPut(swap_asset_ID, Btoi(Txn.application_args[1])),
        App.globalPut(new_asset_ID, Btoi(Txn.application_args[2])),
        asset_decimal,
        Assert(asset_decimal.hasValue()),
        App.globalPut(multiplier, Exp(Int(10),asset_decimal.value())),
        Approve()
    )

    swap = Seq(
        swap_asset_balance,
        new_asset_balance,
        Assert(And(Global.group_size() == Int(3),
                   Gtxn[0].type_enum() == TxnType.Payment,
                   Gtxn[0].amount() == Int(1000),
                   Gtxn[0].receiver() == Global.current_application_address(),

                   Gtxn[1].type_enum() == TxnType.AssetTransfer,
                   Gtxn[1].asset_amount() > Int(0),
                   Gtxn[1].xfer_asset() == App.globalGet(swap_asset_ID),
                   Gtxn[1].asset_receiver() == Global.current_application_address(),

                   Gtxn[2].on_completion() == OnComplete.NoOp,
                   Gtxn[2].application_args.length() == Int(1),
                   #user must be opted into old asset
                   swap_asset_balance.hasValue(),
                   #user must be opted into new asset
                   new_asset_balance.hasValue())),
        swap_token(Gtxn[1].asset_amount() * App.globalGet(multiplier)),
        Approve()
    )

    # Application router for this smart contract.
    program = Cond(
        [
            Or(
                # Your fees shouldn't exceed an unreasonable amount
                Txn.fee() > Int(1000),
                # No rekeys allowed
                Txn.rekey_to() != Global.zero_address(),
                # This smart contract cannot be closed out.
                Txn.on_completion() == OnComplete.CloseOut,
                # This smart contract cannot be updated.
                Txn.on_completion() == OnComplete.UpdateApplication,
                # This smart contract cannot be cleared of local state
                Txn.on_completion() == OnComplete.ClearState,
                # This smart contract cannot be deleted
                Txn.on_completion() == OnComplete.DeleteApplication,
                # This smart contract cannot be opted in to
                Txn.on_completion() == OnComplete.OptIn,
                # no closing out algo allowed
                Txn.close_remainder_to() != Global.zero_address(),
                Txn.asset_close_to() != Global.zero_address()
            ),
            Reject(),
        ],

        [Txn.application_id() == Int(0), Approve()],
        [Txn.application_args[0] == Bytes("opt_in_assets"), opt_in_assets],
        [Txn.application_args[0] == Bytes("swap"), swap]
    )

    return compileTeal(program, Mode.Application, version=5)

def clear_program():
    return compileTeal(Reject(), Mode.Application, version=5)

def compile_app(algod_client):
    dump_teal_assembly('akita_token_swapper_approval.teal', approval_program)
    dump_teal_assembly('akita_token_swapper_clear.teal', clear_program)

    compile_program(algod_client, approval_program(), 'akita_token_swapper_approval.compiled')
    compile_program(algod_client, clear_program(), 'akita_token_swapper_clear.compiled')

    write_schema(file_path='localSchema',
                 num_ints=0,
                 num_bytes=0)
    write_schema(file_path='globalSchema',
                 num_ints=3,
                 num_bytes=0)
