import pytest
from algosdk.v2client import algod
from algosdk import account, mnemonic, constants, encoding
from algosdk.future import transaction
from algosdk.encoding import encode_address, decode_address, is_valid_address
from algosdk.error import AlgodHTTPError, TemplateInputError
from akita_inu_asa_utils import read_local_state, read_global_state, wait_for_txn_confirmation, load_compiled
import base64


class App:
    __slots__ = ('id',
                 'creator',
                 'address',
                 'asset_id',
                 'royalty_permille',
                 'royalty_payouts',
                 'logic_sig'
                )


    def __init__(self, test_config, asset_id, creator, royalty_receivers):
        from contracts.nft_royalties.deployment import deploy

        algod_address = test_config['algodAddress']
        algod_token = test_config['algodToken']
        creator_mnemonic = creator['mnemonic']
        clear_build_folder()

        self.royalty_permille = 100
        self.royalty_payouts = [
                {
                    'address': royalty_receivers[0],
                    'ratio': 60
                },
                {
                    'address': royalty_receivers[1],
                    'ratio': 40
                },
            ]

        app_details = deploy(algod_address,
                             algod_token,
                             creator_mnemonic,
                             asset_id,
                             self.royalty_permille,
                             self.royalty_payouts)
        
        self.asset_id = asset_id
        self.creator = creator
        self.id = app_details[0]
        escrow_address = app_details[1]
        self.address = encode_address(encoding.checksum(b'appID' + self.id.to_bytes(8, 'big')))

        escrow_program = load_compiled(file_path='nft_royalties/escrow.compiled')
        self.logic_sig = transaction.LogicSigAccount(escrow_program)
        assert escrow_address == self.logic_sig.address()


    def perform_sale(self, client, sale, authed=True):
        params = client.suggested_params()
        buyer_address = sale.buyer['public_key']
        seller_address = sale.seller['public_key']
        buyer_key = sale.buyer['private_key']
        seller_key = sale.seller['private_key']
        txn0 = transaction.AssetTransferTxn(self.logic_sig.address(),
                                            params,
                                            buyer_address,
                                            1,
                                            self.asset_id,
                                            revocation_target=seller_address)
        txn0.fee = 0
        txn1 = transaction.PaymentTxn(buyer_address,
                                      params,
                                      seller_address,
                                      sale.price)
        txn1.fee = 4000 + 1000 * len(self.royalty_payouts)
        txn2 = transaction.PaymentTxn(buyer_address,
                                      params,
                                      self.address,
                                      int(sale.price * sale.royalty_permille / 1000))
        txn2.fee = 0
        txn3 = transaction.ApplicationCallTxn(seller_address,
                                              params,
                                              self.id,
                                              transaction.OnComplete.NoOpOC.real,
                                              foreign_assets=[self.asset_id],
                                              app_args=['transfer'],
                                              accounts=[r['address']
                                                        for r in self.royalty_payouts])
        txn3.fee = 0
        
        grouped = transaction.assign_group_id([txn0, txn1, txn2, txn3])
        grouped = [transaction.LogicSigTransaction(grouped[0], self.logic_sig),
                   grouped[1].sign(buyer_key),
                   grouped[2].sign(buyer_key),
                   grouped[3].sign(seller_key if authed else buyer_key)]

        txn_id = client.send_transactions(grouped)
        wait_for_txn_confirmation(client, txn_id, 5)


    def reconfigure_asset(self, client):
        params = client.suggested_params()
        txn0 = transaction.AssetConfigTxn(self.logic_sig.address(),
                                          params,
                                          index=self.asset_id,
                                          strict_empty_address_check=False,
                                          manager=self.logic_sig.address(),
                                          freeze=self.logic_sig.address(),
                                          clawback=self.logic_sig.address(),
                                         )
        txn0.fee = 0
        txn1 = transaction.ApplicationDeleteTxn(self.creator['public_key'],
                                                params,
                                                self.id)
        txn1.fee = 2000
        grouped = transaction.assign_group_id([txn0, txn1])
        grouped = [transaction.LogicSigTransaction(grouped[0], self.logic_sig),
                   grouped[1].sign(self.creator['private_key'])]
        client.send_transactions(grouped)
    
    
    def set_royalty(self, client, royalty_permille):
        params = client.suggested_params()
        txn = transaction.ApplicationCallTxn(self.creator['public_key'],
                                             params,
                                             self.id,
                                             transaction.OnComplete.NoOpOC.real,
                                             app_args=['set_royalty',
                                                       royalty_permille],
                                             foreign_assets=[self.asset_id],
                                             )
        client.send_transaction(txn.sign(self.creator['private_key']))


    def delete_without_destroy(self, client):
        params = client.suggested_params()
        txn0 = transaction.PaymentTxn(self.logic_sig.address(),
                                      params,
                                      self.creator['public_key'],
                                      0,
                                      close_remainder_to=self.creator['public_key'])
        txn0.fee = 0
        txn1 = transaction.ApplicationDeleteTxn(self.creator['public_key'],
                                                params,
                                                self.id,
                                                foreign_assets=[self.asset_id])
        txn1.fee = 3000
        grouped = transaction.assign_group_id([txn0, txn1])
        grouped = [transaction.LogicSigTransaction(grouped[0], self.logic_sig),
                   grouped[1].sign(self.creator['private_key'])]
        client.send_transactions(grouped)


    def destroy_without_delete(self, client):
        # Really should never succeed, since the escrow requires a txn fee of
        # 0 and a valid call to the application, but just in case
        params = client.suggested_params()
        txn = transaction.AssetDestroyTxn(self.logic_sig.address(),
                                          params,
                                          self.asset_id)
        client.send_transaction(transaction.LogicSigTransaction(txn, self.logic_sig))


    def delete(self, client):
        params = client.suggested_params()
        txn0 = transaction.AssetDestroyTxn(self.logic_sig.address(),
                                           params,
                                           self.asset_id)
        txn0.fee = 0
        txn1 = transaction.PaymentTxn(self.logic_sig.address(),
                                      params,
                                      self.creator['public_key'],
                                      0,
                                      close_remainder_to=self.creator['public_key'])
        txn1.fee = 0
        txn2 = transaction.ApplicationDeleteTxn(self.creator['public_key'],
                                                params,
                                                self.id,
                                                foreign_assets=[self.asset_id])
        txn2.fee = 3000
        grouped = transaction.assign_group_id([txn0, txn1, txn2])
        grouped = [transaction.LogicSigTransaction(grouped[0], self.logic_sig),
                   transaction.LogicSigTransaction(grouped[1], self.logic_sig),
                   grouped[2].sign(self.creator['private_key'])]
        client.send_transactions(grouped)


class Sale:
    __slots__ = 'seller', 'buyer', 'price', 'royalty_permille'

    def __init__(self, seller, buyer, price, royalty_permille=100):
        self.seller = seller
        self.buyer = buyer
        self.price = price
        self.royalty_permille = royalty_permille


@pytest.fixture(scope='class')
def test_config():
    from .testing_utils import load_test_config
    return load_test_config()


@pytest.fixture(scope='class')
def client(test_config):
    algod_address = test_config['algodAddress']
    algod_token = test_config['algodToken']
    client = algod.AlgodClient(algod_token, algod_address)
    return client


def new_wallet(client, funding_account=None, opt_in_asset=None):
    from akita_inu_asa_utils import generate_new_account
    from .testing_utils import fund_account
    wallet_mnemonic, private_key, public_key = generate_new_account()

    wallet = {'mnemonic': wallet_mnemonic, 'public_key': public_key, 'private_key': private_key}

    if funding_account:
        fund_account(wallet['public_key'], funding_account)

    if opt_in_asset:
        params = client.suggested_params()
        optin = transaction.AssetOptInTxn(wallet['public_key'],
                                          params,
                                          opt_in_asset)
        client.send_transaction(optin.sign(wallet['private_key']))

    return wallet


@pytest.fixture(scope='class')
def creator(test_config):
    return new_wallet(client, test_config['fund_account_mnemonic'])


@pytest.fixture(scope='class')
def wallet_1(test_config, asset_id, client):
    return new_wallet(client, test_config['fund_account_mnemonic'], asset_id)


@pytest.fixture(scope='class')
def wallet_2(test_config, asset_id, client):
    return new_wallet(client, test_config['fund_account_mnemonic'], asset_id)


@pytest.fixture(scope='class')
def asset_id(test_config, creator, client):
    from akita_inu_asa_utils import( create_asa_signed_txn,
        asset_id_from_create_txn)
    params = client.suggested_params()
    txn, txn_id = create_asa_signed_txn(creator['public_key'],
                                        creator['private_key'],
                                        params,
                                        default_frozen=True,
                                        total=1)
    client.send_transactions([txn])
    wait_for_txn_confirmation(client, txn_id, 5)
    return asset_id_from_create_txn(client, txn_id)


@pytest.fixture(scope='class')
def royalty_receivers(test_config, creator):
    return [test_config['fund_account_public_key'], creator['public_key']]


@pytest.fixture(scope='class')
def app(test_config, asset_id, creator, royalty_receivers):
    return App(test_config, asset_id, creator, royalty_receivers)


def clear_build_folder():
    import os
    for file in os.scandir('./build/nft_royalties'):
        os.remove(file.path)


def fund_accounts(client, creator, app):
    params = client.suggested_params()
    txn = transaction.PaymentTxn(creator['public_key'],
                                 params,
                                 app.address,
                                 100000)
    signed_txn = txn.sign(creator['private_key'])
    txn_id = client.send_transaction(signed_txn)

    txn = transaction.PaymentTxn(creator['public_key'],
                                 params,
                                 app.logic_sig.address(),
                                 100000)
    signed_txn = txn.sign(creator['private_key'])
    txn_id = client.send_transaction(signed_txn)


class TestNFTRoyalties:
    def test_build(self, app):
        import os
        assert os.path.exists('./build/nft_royalties/transfer.compiled')
        assert os.path.exists('./build/nft_royalties/clear.compiled')
        assert os.path.exists('./build/nft_royalties/escrow.teal')
        assert os.path.exists('./build/nft_royalties/escrow.compiled')
        assert os.path.exists('./build/nft_royalties/globalSchema')
        assert os.path.exists('./build/nft_royalties/localSchema')


    def test_distribute(self, client, app, creator, wallet_1):
        assert app.asset_id
        assert app.id
        fund_accounts(client, creator, app)
        app.perform_sale(client, Sale(creator, wallet_1, 0, 0))


    def test_sell(self, client, app, wallet_1, wallet_2):
        app.perform_sale(client, Sale(wallet_1, wallet_2, 1000000, 100))


    def test_insufficient_royalty(self, client, app, wallet_1, wallet_2):
        with pytest.raises(AlgodHTTPError):
            # Should fail before we decrease the minimum royalty
            app.perform_sale(client, Sale(wallet_2, wallet_1, 10000, 50))


    def test_reduce_royalty(self, client, app, wallet_1, wallet_2):
        app.set_royalty(client, 40)
        app.perform_sale(client, Sale(wallet_2, wallet_1, 10000, 50))

    
    def test_no_authority(self, client, app, creator, wallet_1, wallet_2):
        with pytest.raises(AlgodHTTPError):
            app.perform_sale(client, Sale(wallet_1, wallet_2, 0, 0), authed=False)
        with pytest.raises(AlgodHTTPError):
            app.perform_sale(client, Sale(creator, wallet_2, 0, 0))


    def test_reconfigure(self, client, app):
        with pytest.raises(AlgodHTTPError):
            app.reconfigure_asset(client)


    def test_not_holding(self, client, app):
        # All the manager calls that should fail when not holding our NFT
        with pytest.raises(AlgodHTTPError):
            app.delete(client)
        with pytest.raises(AlgodHTTPError):
            app.set_royalty(client, 100)


    def test_delete_app(self, client, app, wallet_1, creator):
        app.perform_sale(client, Sale(wallet_1, creator, 0, 0))
        app.set_royalty(client, 100)

        # Should only be able to delete the app and destroy the asset together
        with pytest.raises(AlgodHTTPError):
            app.delete_without_destroy(client)
        with pytest.raises(AlgodHTTPError):
            app.destroy_without_delete(client)

        app.delete(client)
