from pyteal import *

def escrow_approval():
    # Escrow contract/account

    # At the moment this is deferring to the contract whose app ID is provided
    # for all logic, it might be a good idea to add extra precautions and
    # requirements into this contract directly

    # Create the logic app, this escrow, and the logicsig together
    logic_app_id = Bytes("logic_app_id")
    on_create = Seq(
        Assert(
            And(
                Global.group_size() == Int(2),
                Txn.group_index() == Int(1),

                Gtxn[0].type_enum() == TxnType.ApplicationCall,
                Gtxn[0].application_id() == Int(0),
            ),
        ),
        App.globalPut(logic_app_id, GeneratedID(0)),
        Approve()
    )
    
    on_call = Seq(
        Assert(
            And(
                Txn.fee() == Int(0),
                Gtxn[0].type_enum() == TxnType.ApplicationCall,
                Gtxn[0].application_id() == App.globalGet(logic_app_id),
            ),
        ),
        Approve(),
    )

    on_delete = Seq(
        Assert(Txn.sender() == Global.creator_address()),
        Approve()
    )

    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp, on_call],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_delete],
        [Int(1), Reject()]
    )
    return program


def transfer_approval(royalties_account):
    on_create = Seq(
        Assert(
            And(
                Global.group_size() == Int(2),
                Txn.group_index() == Int(0),

                Gtxn[1].type_enum() == TxnType.ApplicationCall,
                Gtxn[1].application_id() == Int(0),
            )
        ),
        Approve()
    )

    # Gtxn[0]
    #     * This call
    #     * Fee should be 0, paid by either party in transfer
    # 
    # Gtxn[1]
    #     * Asset transfer via clawback, must be signed with escrow's
    #       code
    #     * Fee should be 0, paid by either party in transfer
    #
    # Gtxn[2]
    #     * Payment for asset
    #     * Must be going opposite direction from Gtxn[1]
    # 
    # Gtxn[3]
    #     * Royalty payment
    #     * Must be going to address specified by contract (hardcoded right now)
    #     * Can be paid by either party(?)
    #     * Should be at least some portion of payment (hardcoded 10% right now)
    default_frozen = AssetParam.defaultFrozen(Int(0))
    clawback = AssetParam.clawback(Int(0))
    manager = AssetParam.manager(Int(0))
    freeze = AssetParam.freeze(Int(0))
    on_call = Seq(
        default_frozen,
        clawback,
        manager,
        freeze,
        Assert(
            And(
                Global.group_size() == Int(4),
                Gtxn[0].type_enum() == TxnType.ApplicationCall,
                Gtxn[1].type_enum() == TxnType.AssetTransfer,
                Gtxn[2].type_enum() == TxnType.Payment,
                Gtxn[3].type_enum() == TxnType.Payment,

                Txn.fee() == Int(0),

                Gtxn[1].fee() == Int(0),
                # Since this is for NFTs, it should be transferring the one
                # and only asset in full
                Gtxn[1].asset_amount() == Int(1),
                default_frozen.hasValue(),
                default_frozen.value(),
                clawback.value() != Global.zero_address(),
                manager.value() == Global.zero_address(),
                freeze.value() == Global.zero_address(),

                Gtxn[2].sender() == Gtxn[1].receiver(),
                Gtxn[1].sender() == Gtxn[2].receiver(),

                Or(
                    Gtxn[3].sender() == Gtxn[1].sender(),
                    Gtxn[3].sender() == Gtxn[2].sender(),
                ),
                Gtxn[3].receiver() == Addr(royalties_account),

                # 10% of payment amount (plus tip!) goes to our multisig
                Gtxn[3].amount() >= Gtxn[2].amount() / Int(10)
            )
        ),
        Approve()
    )

    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp, on_call],
        [Int(1), Reject()]
    )
    return program


def logicsig_approval(multisig, addresses, ratio_terms):
    # LogicSig for spending from multisig account
    # Can only pay out to the provided addresses in the provided ratio

    assert(len(addresses) == len(ratio_terms))

    ratio_sum = sum(ratio_terms)

    def static_for_each(xs, f, wrap=Seq):
        return [f(x) for x in xs]

    indices = range(len(addresses))

    num_parties = Int(len(addresses))
    i = ScratchVar()
    total_paid_out = ScratchVar()

    all_payments_valid = And(
        # Only valid after sum of payments calculated
        total_paid_out.load() > Int(0),

        # Generate checks for every party in the contract
        And(*static_for_each(
            indices,
            lambda i:
                And(
                    Gtxn[i].type_enum() == TxnType.Payment,
                    Gtxn[i].sender() == Addr(multisig),
                    Gtxn[i].receiver() == Addr(addresses[i]),
                    Gtxn[i].amount() == total_paid_out.load() * Int(ratio_terms[i]) / Int(ratio_sum),
                ),
        ))
    )
    
    program = Seq(
        i.store(Int(0)),
        total_paid_out.store(Int(0)),
        Assert(Global.group_size() == num_parties),
        For(i.store(Int(0)), i.load() < num_parties, i.store(i.load() + Int(1)))
        .Do(
            total_paid_out.store(total_paid_out.load() + Gtxn[i.load()].amount()),
        ),
        Assert(all_payments_valid),
        Approve()
    )

    return program


if __name__ == "__main__":
    with open("escrow.teal", "w") as f:
        compiled = compileTeal(escrow_approval(), mode=Mode.Application, version=5)
        f.write(compiled)

    with open("transfer.teal", "w") as f:
        compiled = compileTeal(transfer_approval("ES5AYWETGOE4PZKCAQJ7FF77M5NEXT5KFTCLZEMYLSZVKEY66BL45KDS2Y"), mode=Mode.Application, version=5)
        f.write(compiled)

    with open("logicsig.teal", "w") as f:
        compiled = compileTeal(logicsig_approval("ES5AYWETGOE4PZKCAQJ7FF77M5NEXT5KFTCLZEMYLSZVKEY66BL45KDS2Y", ["ECNHJST6SMCFXH6R6Z2L4D4ZYHG6FZFULY7O3XFTXORWBRZJUF2MSQRGZA","XFNIWS5CZ67DKPR5767PR3YIWDZFYSFNLPPEAE6YKFIMUUIZC7WGYK22IA"], [60,40]), mode=Mode.Application, version=5)
        f.write(compiled)
