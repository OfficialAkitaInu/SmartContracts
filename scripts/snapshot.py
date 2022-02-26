from akita_inu_asa_utils import *
import pandas as pd
import numpy as np
import time

OUTPUT_COLUMNS = ["ADDRESS", "ASSET_ID", "WEIGHT", "DISQUALIFIED_TXN"]

#returns a tuple of format [weight, disqualified_txn]
def validate_stake(indexer, address, asset_id, eligible_csv, stake_begin_unix_ts, stake_end_unix_ts):
    # if the NFT has weight then its eligible
    if weight := eligible_csv[eligible_csv["asset_id"] == asset_id]["weight"]:
        
        query = indexer.search_transactions_by_address(address, asset_id)
        next_token = query['next-token']
        transactions = query['transactions']
        last_received = None
        last_sent = None
        closest_eligible_receive = None

        while len(transactions):
            base_txns = pd.DataFrame(indexer.search_transactions_by_address(account, asset_id=asset_id)['transactions'])
            asset_txns = pd.DataFrame.from_records(base_txns['asset-transfer-transaction'])
            base_txns = base_txns[np.logical_xor(asset_txns['close-amount'] > 0, asset_txns['amount'] > 0)]
            asset_txns = pd.DataFrame.from_records(base_txns['asset-transfer-transaction']).join(base_txns[['sender', 'round-time', 'id']])
            
            current_closest_receive = asset_txns[np.logical_and(asset_txns['receiver'] == account, asset_txns['round-time'] <= stake_begin_unix_ts)].tail(1)
            if current_closest_receive.shape[0] and current_closest_receive['round-time'] > closest_eligible_receive['round-time']:
                closest_eligible_receive = current_closest_receive
            
            soonest_over_receive = asset_txns[np.logical_and(asset_txns['receiver'] == account, asset_txns['round-time'] > stake_begin_unix_ts)].head(1)
            if soonest_over_receive.shape[0] and soonest_over_receive['round-time'] < stake_end_unix_ts:
                return (0, soonest_over_receive['id'].iloc[0])
            
            soonest_over_sent = asset_txns[np.logical_and(asset_txns['sender'] == account, asset_txns['round-time'] > stake_begin_unix_ts)].head(1)
            if soonest_over_sent.shape[0] and soonest_over_sent['round-time'] < stake_end_unix_ts:
                return (0, soonest_over_sent['id'].iloc[0])

            query = indexer.search_transactions_by_address(address, asset_id, next_page=next_token)
            if 'next-token' in query.keys():
                next_token = query['next-token']
                transactions = query['transactions']
            else:
                break

        return (weight, "")
    else:
        return (0, "")

def build_registered_asset_map(indexer, registration_csv_path, eligible_csv_path, staking_start_time, staking_end_time):
    registrations = pd.read_csv(registration_csv_path)
    eligible_nfts = pd.read_csv(eligible_csv_path)

    unique_addresses = list(pd.unique(registrations["address"]))
    output = pd.DataFrame(columns=OUTPUT_COLUMNS)
    for address in unique_addresses:
        assets_registered = list(registrations[registrations["address"] == address]["asset_ids"])

        for asset in assets_registered:
            weight, disqualified_txn = validate_stake(indexer, address, asset, staking_start_time, staking_end_time)
            output.loc[len(output.index)] = {"ADDRESS": address, "ASSET_ID": asset, "WEIGHT": weight, "DISQUALIFIED_TXN": disqualified_txn}
    output.to_csv(output_path, columns=OUTPUT_COLUMNS)


indexer = get_remote_indexer()
registeration_csv = "" # each row contains address, asset_id, discord_username
eligible_nft_csv = ""  # each row contains columns [asset_id, weight]
output_path = ""  # where output is written
staking_start_time = 123
staking_end_time = 123