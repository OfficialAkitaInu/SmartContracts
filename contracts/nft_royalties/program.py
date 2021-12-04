from akita_inu_asa_utils import *
from pyteal import *


def transfer_approval(asset_id, royalty_percent, royalty_payouts):
    ratio_sum = sum([r["ratio"] for r in royalty_payouts])

    indices = range(len(royalty_payouts))

    owner = Bytes("owner")
    royalty = Bytes("royalty")

    default_frozen = AssetParam.defaultFrozen(Int(0))
    clawback = AssetParam.clawback(Int(0))
    manager = AssetParam.manager(Int(0))
    freeze = AssetParam.freeze(Int(0))
    royalty_minimum = Gtxn[1].amount() / App.globalGet(royalty) # might store in scratch?

    def payRoyalty(receiver):
        return Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.receiver: Addr(receiver["address"]),
                    TxnField.amount:
                        royalty_minimum * Int(receiver["ratio"]) / Int(ratio_sum),
                    TxnField.fee: Int(0),
                }
            ),
            InnerTxnBuilder.Submit(),
        )

    on_create = Seq(
        App.globalPut(owner, Txn.sender()),
        App.globalPut(royalty, Int(int(100 / royalty_percent))),
        Approve()
    )

    # Gtxn[0]
    #     * Asset transfer via clawback, must be signed with escrow's
    #       code
    #     * Fee should be 0, voere by either party in transfer
    #     * Amount should be 1
    #
    # Gtxn[1]
    #     * Payment for asset
    #     * Must be going opposite direction from Gtxn[0]
    # 
    # Gtxn[2]
    #     * Royalty payment
    #     * Must be going to application account
    #     * Can be paid by either party(?)
    #
    # Gtxn[3]
    #     * This call
    on_call = Seq(
        default_frozen,
        clawback,
        manager,
        freeze,
        Assert(
            And(
                Global.group_size() == Int(4),
                Gtxn[0].type_enum() == TxnType.AssetTransfer,
                Gtxn[1].type_enum() == TxnType.Payment,
                Gtxn[2].type_enum() == TxnType.Payment,
                Gtxn[3].type_enum() == TxnType.ApplicationCall,

                Gtxn[0].fee() == Int(0),
                Gtxn[0].asset_amount() == Int(1),
                Gtxn[0].xfer_asset() == Int(asset_id),

                Gtxn[0].close_remainder_to() == Global.zero_address(),
                Gtxn[0].rekey_to() == Global.zero_address(),
                Gtxn[1].close_remainder_to() == Global.zero_address(),
                Gtxn[1].rekey_to() == Global.zero_address(),
                Gtxn[2].close_remainder_to() == Global.zero_address(),
                Gtxn[2].rekey_to() == Global.zero_address(),
                Gtxn[3].close_remainder_to() == Global.zero_address(),
                Gtxn[3].rekey_to() == Global.zero_address(),

                Txn.sender() == Gtxn[0].asset_sender(),

                default_frozen.hasValue(),
                default_frozen.value(),
                clawback.value() != Global.zero_address(),
                manager.value() == Global.zero_address(),
                freeze.value() == Global.zero_address(),

                Gtxn[1].sender() == Gtxn[0].asset_receiver(),
                Gtxn[0].asset_sender() == Gtxn[1].receiver(),

                Or(
                    Gtxn[2].sender() == Gtxn[1].asset_sender(),
                    Gtxn[2].sender() == Gtxn[2].sender(),
                ),
                Gtxn[2].receiver() == Global.current_application_address(),

                Gtxn[2].amount() >= royalty_minimum,
            )
        ),
        Seq(*[payRoyalty(royalty_payouts[i]) for i in indices]),
        App.globalPut(owner, Gtxn[0].asset_receiver()),
        Approve()
    )

    on_delete = Return(
        And(
            Txn.sender() == Global.creator_address(),
            Txn.sender() == App.globalGet(owner)
        )
    )

    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp, on_call],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_delete],
        [Int(1), Reject()]
    )
    return program


def escrow_approval(transfer_app_id=121):
    # Escrow contract/account
    on_call = Seq(
        Assert(
            And(
                Txn.fee() == Int(0),
                Gtxn[3].type_enum() == TxnType.ApplicationCall,
                Gtxn[3].application_id() == Int(transfer_app_id),
            ),
        ),
        Approve(),
    )

    program = Cond(
        [Txn.on_completion() == OnComplete.NoOp, on_call],
        [Int(1), Reject()]
    )
    return program


def clear_program():
    return Reject()


def compile_transfer_app(algod_client, asset_id, royalty_percent, royalty_payouts):
    check_build_dir()

    if not os.path.exists('build/nft_royalties'):
        os.mkdir('build/nft_royalties')

    compile_program(
            algod_client,
            compileTeal(
                transfer_approval(asset_id, royalty_percent, royalty_payouts),
                mode=Mode.Application,
                version=5),
            'nft_royalties/transfer.compiled')
    compile_program(
            algod_client,
            compileTeal(clear_program(), mode=Mode.Application, version=5),
            'nft_royalties/clear.compiled')

    write_schema("nft_royalties/globalSchema", 1, 1)
    write_schema("nft_royalties/localSchema", 0, 0)


def compile_escrow_app(algod_client, transfer_app_id):
    teal = compileTeal(
                escrow_approval(transfer_app_id),
                mode=Mode.Signature,
                version=5
            )
    with open("build/nft_royalties/escrow.teal", "w") as f:
        f.write(teal)
    return compile_program(algod_client, teal, "nft_royalties/escrow.compiled")
