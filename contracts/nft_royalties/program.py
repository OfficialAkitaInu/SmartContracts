from pyteal import *

def transfer_approval(royalty_percent, royalty_payouts):
    ratio_sum = sum([r["ratio"] for r in royalty_payouts])

    indices = range(len(royalty_payouts))

    default_frozen = AssetParam.defaultFrozen(Int(0))
    clawback = AssetParam.clawback(Int(0))
    manager = AssetParam.manager(Int(0))
    freeze = AssetParam.freeze(Int(0))
    royalty_minimum = Gtxn[1].amount() / Int(royalty_percent) # might store in scratch?

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

                Gtxn[0].close_remainder_to() == Global.zero_address(),
                Gtxn[0].rekey_to() == Global.zero_address(),
                Gtxn[1].close_remainder_to() == Global.zero_address(),
                Gtxn[1].rekey_to() == Global.zero_address(),
                Gtxn[2].close_remainder_to() == Global.zero_address(),
                Gtxn[2].rekey_to() == Global.zero_address(),
                Gtxn[3].close_remainder_to() == Global.zero_address(),
                Gtxn[3].rekey_to() == Global.zero_address(),

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
        Approve()
    )

    on_delete = Return(Txn.sender() == Global.creator_address())

    program = Cond(
        [Txn.application_id() == Int(0), Approve()],
        [Txn.on_completion() == OnComplete.NoOp, on_call],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_delete],
        [Int(1), Reject()]
    )
    return program


def escrow_approval(transfer_app_id = 121):
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


if __name__ == "__main__":
    royalty_percent = 10
    royalty_payouts = [
            {
                "address": "ECNHJST6SMCFXH6R6Z2L4D4ZYHG6FZFULY7O3XFTXORWBRZJUF2MSQRGZA",
                "ratio": 6
            },
            {
                "address": "XFNIWS5CZ67DKPR5767PR3YIWDZFYSFNLPPEAE6YKFIMUUIZC7WGYK22IA",
                "ratio": 4
            },
        ]

    with open("escrow.teal", "w") as f:
        compiled = compileTeal(escrow_approval(), mode=Mode.Application, version=5)
        f.write(compiled)

    with open("transfer_split.teal", "w") as f:
        compiled = compileTeal(transfer_approval(royalty_percent, royalty_payouts), mode=Mode.Application, version=5)
        f.write(compiled)
