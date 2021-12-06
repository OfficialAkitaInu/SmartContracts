from akita_inu_asa_utils import *
from pyteal import *


def transfer_approval(asset_id, app_manager_address, royalty_permille, royalty_payouts):
    # app_manager_address: address that is allowed to execute privileged calls
    #                      on this app
    # royalty_permille:    royalty value in terms of permille of payment value
    # royalty_payouts:     list of dictionaries, each including an address and
    #                      the portion of the royalty paid to it

    ratio_sum = sum([r['ratio'] for r in royalty_payouts])

    # app_manager: stores app_manager_address on creation, can't be updated
    #              right now (may change this)
    # owner:       the address holding our NFT, according to transfer history
    # royalty:     stores royalty_permille on creation, can be updated via
    #              'set_royalty' calls
    app_manager = Bytes('app_manager')
    owner = Bytes('owner')
    royalty = Bytes('royalty')

    # This is how we actually test for ownership, the owner global is mainly
    # for convenience
    sender_has_nft = AssetHolding.balance(Txn.sender(), Int(0))
    default_frozen = AssetParam.defaultFrozen(Int(0))
    clawback = AssetParam.clawback(Int(0))
    manager = AssetParam.manager(Int(0))
    freeze = AssetParam.freeze(Int(0))
    royalty_minimum = Gtxn[1].amount() * App.globalGet(royalty) / Int(1000)
    royalty_payment = Gtxn[2].amount()

    # This function statically generates an inner transaction given an
    # item in royalty_payouts
    def payRoyalty(receiver):
        return Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.receiver: Addr(receiver['address']),
                    TxnField.amount:
                        royalty_payment * Int(receiver['ratio']) / Int(ratio_sum),
                    TxnField.fee: Int(0),
                }
            ),
            InnerTxnBuilder.Submit(),
        )

    on_create = Seq(
        sender_has_nft,
        Assert(sender_has_nft.value()),
        App.globalPut(app_manager, Addr(app_manager_address)),
        App.globalPut(owner, Addr(app_manager_address)),
        App.globalPut(royalty, Int(royalty_permille)),
        Approve()
    )

    #
    # The main transfer logic
    #
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
    #
    asset_transfer = Seq(
        default_frozen,
        clawback,
        manager,
        freeze,
        Assert(
            And(
                Txn.assets.length() == Int(1),
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
                manager.value() == clawback.value(),
                freeze.value() == clawback.value(),

                Gtxn[1].sender() == Gtxn[0].asset_receiver(),
                Gtxn[0].asset_sender() == Gtxn[1].receiver(),

                Or(
                    Gtxn[2].sender() == Gtxn[1].asset_sender(),
                    Gtxn[2].sender() == Gtxn[2].sender(),
                ),
                Gtxn[2].receiver() == Global.current_application_address(),

                royalty_payment >= royalty_minimum,
            )
        ),
        If(royalty_payment > Int(0))
        .Then(Seq(*[payRoyalty(r) for r in royalty_payouts])),
        App.globalPut(owner, Gtxn[0].asset_receiver()),
        Approve()
    )

    new_royalty = Btoi(Txn.application_args[1])
    set_royalty = Seq(
        sender_has_nft,
        Assert(
            And(
                Global.group_size() == Int(1),
                Txn.sender() == App.globalGet(app_manager),
                Or(
                    # Only allow increasing royalty while holding the asset
                    new_royalty < App.globalGet(royalty),
                    sender_has_nft.value()
                )
            )
        ),
        App.globalPut(royalty, new_royalty),
        Approve()
    )

    call = Txn.application_args[0]
    on_call = Cond(
        [call == Bytes('transfer'), asset_transfer],
        [call == Bytes('set_royalty'), set_royalty],
    )

    on_update = Seq(
        sender_has_nft,
        Return(
            And(
                Global.group_size() == Int(1),
                Txn.sender() == App.globalGet(app_manager),
                sender_has_nft.value(),
                Txn.rekey_to() == Global.zero_address()
            )
        )
    )

    on_delete = Seq(
        Assert(Txn.sender() == App.globalGet(app_manager)),
        Assert(
            # You can dump the remaining ALGO balance from the escrow (should
            # be 0.1), or just leave it and destroy everything
            Or(
                And(
                    Global.group_size() == Int(3),
                    Gtxn[0].type_enum() == TxnType.AssetConfig,
                    Gtxn[1].type_enum() == TxnType.Payment,
                    Gtxn[2].type_enum() == TxnType.ApplicationCall,

                    Gtxn[1].fee() == Int(0),
                    Gtxn[1].close_remainder_to() == Txn.sender(),

                    Gtxn[0].rekey_to() == Global.zero_address(),
                    Gtxn[1].rekey_to() == Global.zero_address(),
                    Gtxn[2].rekey_to() == Global.zero_address()
                ),
                And(
                    Global.group_size() == Int(2),
                    Gtxn[0].type_enum() == TxnType.AssetConfig,
                    Gtxn[1].type_enum() == TxnType.ApplicationCall,

                    Gtxn[0].rekey_to() == Global.zero_address(),
                    Gtxn[1].rekey_to() == Global.zero_address()
                ),
            )
        ),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.Payment,
                TxnField.close_remainder_to: Txn.sender(),
            }
        ),
        InnerTxnBuilder.Submit(),
        Approve()
    )

    program = Seq(
        Assert(
            Or(
                Txn.assets.length() == Int(0),
                And(
                    Txn.assets.length() == Int(1),
                    Txn.assets[Int(0)] == Int(asset_id),
                ),
            ),
        ),
        Cond(
            [Txn.application_id() == Int(0), on_create],
            [Txn.on_completion() == OnComplete.NoOp, on_call],
            [Txn.on_completion() == OnComplete.UpdateApplication, on_update],
            [Txn.on_completion() == OnComplete.DeleteApplication, on_delete],
            [Int(1), Reject()]
        )
    )
    return program


def escrow_approval(transfer_app_id=121):
    # Escrow contract/account
    app_txn_index = Global.group_size() - Int(1)

    program = Return(
        And(
            Txn.fee() == Int(0),
            Gtxn[app_txn_index].type_enum() == TxnType.ApplicationCall,
            Gtxn[app_txn_index].application_id() == Int(transfer_app_id),
        )
    )
    return program


def clear_program():
    return Reject()


def compile_transfer_app(algod_client,
                         asset_id,
                         app_manager_address,
                         royalty_permille,
                         royalty_payouts):
    check_build_dir()

    if not os.path.exists('build/nft_royalties'):
        os.mkdir('build/nft_royalties')

    transfer_teal = compileTeal(
            transfer_approval(asset_id,
                              app_manager_address,
                              royalty_permille,
                              royalty_payouts),
            mode=Mode.Application,
            version=5)
    with open('build/nft_royalties/transfer.teal', 'w') as f:
        f.write(transfer_teal)
    compile_program(
            algod_client,
            transfer_teal,
            'nft_royalties/transfer.compiled')
    compile_program(
            algod_client,
            compileTeal(clear_program(), mode=Mode.Application, version=5),
            'nft_royalties/clear.compiled')

    write_schema('nft_royalties/globalSchema', 1, 2)
    write_schema('nft_royalties/localSchema', 0, 0)


def compile_escrow_app(algod_client, transfer_app_id):
    teal = compileTeal(
                escrow_approval(transfer_app_id),
                mode=Mode.Signature,
                version=5
            )
    with open('build/nft_royalties/escrow.teal', 'w') as f:
        f.write(teal)
    compile_program(algod_client, teal, 'nft_royalties/escrow.compiled')
    return get_program_hash(algod_client, teal)
