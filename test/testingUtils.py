import json

def load_test_config(file_path='./test/testConfig.json'):
    fp = open(file_path)
    return json.load(fp)

def _initial_funds_address():
    """Get the address of initially created account having enough funds.

    Such an account is used to transfer initial funds for the accounts
    created in this tutorial.
    """
    return next(
        (
            account.get("address")
            for account in _indexer_client().accounts().get("accounts", [{}, {}])
            if account.get("created-at-round") == 0
            and account.get("status") == "Offline"  # "Online" for devMode
        ),
        None,
    )

def fund_account(address, initial_funds=1000000000):
    """Fund provided `address` with `initial_funds` amount of microAlgos."""
    initial_funds_address = _initial_funds_address()
    if initial_funds_address is None:
        raise Exception("Initial funds weren't transferred!")
    _add_transaction(
        initial_funds_address,
        address,
        _cli_passphrase_for_account(initial_funds_address),
        initial_funds,
        "Initial funds",
    )