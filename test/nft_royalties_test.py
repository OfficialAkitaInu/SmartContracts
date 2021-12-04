import pytest
from algosdk.v2client import algod
from algosdk import account, mnemonic, constants, encoding
from algosdk.encoding import encode_address, is_valid_address
from algosdk.error import AlgodHTTPError, TemplateInputError
from akita_inu_asa_utils import read_local_state, read_global_state, wait_for_txn_confirmation, load_compiled
import base64


class App:
    __slots__ = ('id',
                 'creator',
                 'address',
                 'escrow_address',
                 'escrow_program',
                 'asset_id',
                 'royalty_receivers'
                )


    def __init__(self, test_config, asset_id, creator, royalty_receivers):
        from contracts.nft_royalties.deployment import deploy

        algod_address = test_config['algodAddress']
        algod_token = test_config['algodToken']
        creator_mnemonic = creator['mnemonic']
        clear_build_folder()

        royalty_percent = 10
        royalty_payouts = [
                {
                    "address": royalty_receivers[0],
                    "ratio": 60
                },
                {
                    "address": royalty_receivers[1],
                    "ratio": 40
                },
            ]

        app_details = deploy(algod_address,
                             algod_token,
                             creator_mnemonic,
                             asset_id,
                             royalty_percent,
                             royalty_payouts)
        
        self.asset_id = asset_id
        self.creator = creator
        self.id = app_details[0]
        self.escrow_address = app_details[1]
        self.address = encode_address(encoding.checksum(b'appID' + self.id.to_bytes(8, 'big')))
        self.escrow_program = load_compiled(file_path='nft_royalties/escrow.compiled')
        self.royalty_receivers = royalty_receivers


    def perform_sale(self, client, sale):
        from algosdk.future import transaction
        params = client.suggested_params()
        buyer_address = sale.buyer["public_key"]
        seller_address = sale.seller["public_key"]
        buyer_key = sale.buyer["private_key"]
        seller_key = sale.seller["private_key"]
        txn0 = transaction.AssetTransferTxn(self.escrow_address,
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
        txn1.fee = 6000
        txn2 = transaction.PaymentTxn(buyer_address,
                                      params,
                                      self.address,
                                      int(sale.price / (100 / sale.royalty_percent)))
        txn2.fee = 0
        txn3 = transaction.ApplicationCallTxn(seller_address,
                                              params,
                                              self.id,
                                              transaction.OnComplete.NoOpOC.real,
                                              foreign_assets=[self.asset_id],
                                              accounts=self.royalty_receivers)
        
        logic_sig = transaction.LogicSigAccount(self.escrow_program)
        grouped = transaction.assign_group_id([txn0, txn1, txn2, txn3])
        grouped = [transaction.LogicSigTransaction(grouped[0], logic_sig),
                   grouped[1].sign(buyer_key),
                   grouped[2].sign(buyer_key),
                   grouped[3].sign(seller_key)]

        txn_id = client.send_transactions(grouped)
        wait_for_txn_confirmation(client, txn_id, 5)


    def perform_unauthed_sale(self, client, sale):
        # Previous version allowed sales of this sort, performed without
        # any input from the seller/asset owner
        from algosdk.future import transaction
        params = client.suggested_params()
        buyer_address = sale.buyer["public_key"]
        seller_address = sale.seller["public_key"]
        buyer_key = sale.buyer["private_key"]
        seller_key = sale.seller["private_key"]
        txn0 = transaction.AssetTransferTxn(self.escrow_address,
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
        txn1.fee = 4000 + 1000 * len(self.royalty_receivers)
        txn2 = transaction.PaymentTxn(buyer_address,
                                      params,
                                      self.address,
                                      int(sale.price / (100 / sale.royalty_percent)))
        txn2.fee = 0
        txn3 = transaction.ApplicationCallTxn(buyer_address,
                                              params,
                                              self.id,
                                              transaction.OnComplete.NoOpOC.real,
                                              foreign_assets=[self.asset_id],
                                              accounts=self.royalty_receivers)
        
        logic_sig = transaction.LogicSigAccount(self.escrow_program)
        grouped = transaction.assign_group_id([txn0, txn1, txn2, txn3])
        grouped = [transaction.LogicSigTransaction(grouped[0], logic_sig),
                   grouped[1].sign(buyer_key),
                   grouped[2].sign(buyer_key),
                   grouped[3].sign(buyer_key)]

        txn_id = client.send_transactions(grouped)
        wait_for_txn_confirmation(client, txn_id, 5)


    def delete(self, client):
        from algosdk.future import transaction
        params = client.suggested_params()
        txn = transaction.ApplicationDeleteTxn(self.creator['public_key'],
                                               params,
                                               self.id)
        client.send_transaction(txn.sign(self.creator['private_key']))
    

class Sale:
    __slots__ = 'seller', 'buyer', 'price', 'royalty_percent'

    def __init__(self, seller, buyer, price, royalty_percent=10):
        self.seller = seller
        self.buyer = buyer
        self.price = price
        self.royalty_percent = royalty_percent


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
    from algosdk.future import transaction
    from akita_inu_asa_utils import generate_new_account
    from .testing_utils import fund_account
    wallet_mnemonic, private_key, public_key = generate_new_account()

    wallet = {'mnemonic': wallet_mnemonic, 'public_key': public_key, 'private_key': private_key}

    if funding_account:
        fund_account(wallet['public_key'], funding_account)

    if opt_in_asset:
        params = client.suggested_params()
        optin = transaction.AssetOptInTxn(wallet["public_key"],
                                          params,
                                          opt_in_asset)
        client.send_transaction(optin.sign(wallet["private_key"]))

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
    return [test_config["fund_account_public_key"], creator["public_key"]]


@pytest.fixture(scope='class')
def app(test_config, asset_id, creator, royalty_receivers):
    return App(test_config, asset_id, creator, royalty_receivers)


def clear_build_folder():
    import os
    for file in os.scandir('./build/nft_royalties'):
        os.remove(file.path)


def fund_accounts(client, creator, app):
    from algosdk.future import transaction
    params = client.suggested_params()
    txn = transaction.PaymentTxn(creator["public_key"],
                                 params,
                                 app.address,
                                 100000)
    signed_txn = txn.sign(creator["private_key"])
    txn_id = client.send_transaction(signed_txn)

    txn = transaction.PaymentTxn(creator["public_key"],
                                 params,
                                 app.escrow_address,
                                 100000)
    signed_txn = txn.sign(creator["private_key"])
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
        app.perform_sale(client, Sale(creator, wallet_1, 0, 10))


    def test_sell(self, client, app, wallet_1, wallet_2):
        app.perform_sale(client, Sale(wallet_1, wallet_2, 1000000, 10))

    
    def test_no_authority(self, client, app, wallet_1, wallet_2):
        with pytest.raises(AlgodHTTPError):
            app.perform_unauthed_sale(client, Sale(wallet_2, wallet_1, 0, 10))


    def test_insufficient_royalty(self, client, app, wallet_1, wallet_2):
        assert asset_id
        assert app.id
        with pytest.raises(AlgodHTTPError):
            app.perform_sale(client, Sale(wallet_2, wallet_1, 10000, 5))
        app.perform_sale(client, Sale(wallet_2, wallet_1, 10000, 10))


    def test_delete_app(self, client, app, wallet_1, creator):
        with pytest.raises(AlgodHTTPError):
            # We want delete to fail if the creator doesn't hold the NFT
            app.delete(client)
        app.perform_sale(client, Sale(wallet_1, creator, 0, 10))
        app.delete(client)

