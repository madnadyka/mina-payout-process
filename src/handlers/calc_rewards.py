import asyncio
import GraphQL
from utils import *
from constants import *
from db_model.dao import ConnectorEpochs, ConnectorPayouts, ConnectorRewards, ConnectorBlocks
import time
import math
from tabulate import tabulate
import traceback


validator_fee = float(config["VALIDATOR"]["fee"])
foundation_delegations = config["VALIDATOR"]["foundation_delegations"].split(',')


async def calc_rewards (app):
    while True:
        try:
            async with app.db_pool.acquire() as conn:
                async with conn.transaction():
                    epochs_for_calculation = await get_uncalculated_epochs(conn)
                    if not epochs_for_calculation: continue
                    logger.info("epochs_for_calculation %s" %epochs_for_calculation)
                    for epoch in epochs_for_calculation:
                        await calculate_rewards(epoch, app.public_key, conn, read_only=False)
            await asyncio.sleep(86400)
        except Exception:
            logger.error("calc_rewards error")
            logger.error(traceback.format_exc())
            await asyncio.sleep(3600)

async def get_uncalculated_epochs(conn):
    epochs = []
    last_calculated_epoch = await ConnectorEpochs.get_last_row(conn)
    latest_block_data = GraphQL.getLatestHeight()
    latest_confirmed_slot = latest_block_data["data"]["blocks"][0]["protocolState"]["consensusState"]["slotSinceGenesis"] - 2*CONFIRMATIONS
    previous_epoch = int(latest_confirmed_slot/BLOCKS_IN_EPOCH)-1
    if not last_calculated_epoch:
        epochs.append(previous_epoch)
    else:
        for e in range(last_calculated_epoch+1, previous_epoch+1):
            epochs.append(e)
    return epochs

async def calculate_rewards(epoch, public_key, conn, read_only = True):
    calculation_ts = int(time.time())
    ledger_hash = GraphQL.getLedgerHash(epoch=epoch)
    ledger_hash = ledger_hash["data"]["blocks"][0]["protocolState"]["consensusState"]["stakingEpochData"]["ledger"]["hash"]

    # Initialize some stuff
    epoch_staking_balance = 0
    epoch_staking_balance_foundation = 0
    epoch_rewards = 0
    epoch_fees = 0
    epoch_blocks = 0

    blocks_table =[]
    rewards_table = []
    payouts_table = []

    staking_ledger = GraphQL.getStakingLedger({
        "delegate": public_key,
        "ledgerHash": ledger_hash,
    })
    if not staking_ledger["data"]["stakes"]:
        logger.warning("We have no stakers")
    for s in staking_ledger["data"]["stakes"]:
        # skip delegates with staking balance == 0
        if s["balance"] == 0:
            continue
        # Clean up timed weighting if no timing info as then they are untimed
        if not s["timing"]:
            timed_weighting = 1
        else:
            timed_weighting = s["timing"]["timed_weighting"]

        # Is this a Foundation address
        if s["public_key"] in foundation_delegations:
            foundation_delegation = True
            epoch_staking_balance_foundation += int(s["balance"]*10**9)
        else:
            foundation_delegation = False

        payouts_table.append({
            "public_key":             s["public_key"],
            "epoch":   epoch,
            "payout_amount":          0,
            "staking_balance":       int(s["balance"]*10**9),
            "timed_weighting":       timed_weighting,
            "foundation_delegation": foundation_delegation,
            "timestamp": calculation_ts,
            "status": TX_CREATED if s["public_key"].lower()!=config["VALIDATOR"]["address"].lower() else TX_NOT_HANDLE
        })
        # Sum the total of the pool
        epoch_staking_balance += int(s["balance"]*10**9)
    assert (epoch_staking_balance_foundation <= epoch_staking_balance)

    blocks = GraphQL.getBlocks({
        "creator":        public_key,
        "epoch":          epoch
    })
    if not blocks["data"]["blocks"]:
        logger.warning("Nothing to payout as we didn't win anything")

    for b in blocks["data"]["blocks"]:
        foundation_payouts = 0
        other_payouts = 0

        if not b["transactions"]["coinbase"]:
            logger.warning(f"{b['blockHeight']} didn't have a coinbase so won it but no rewards.")
            continue

        coinbase_receiver = b["transactions"]["coinbaseReceiverAccount"]["publicKey"]

        ####################################
        # FEE TRANSFERS
        ####################################
        fee_transfers_list = list(filter(lambda d: d['type'] == "Fee_transfer", b["transactions"]["feeTransfer"]))
        fee_transfers = sum(int(item['fee']) for item in fee_transfers_list)

        fee_transfers_coinbase_list = list(filter(lambda d: d['type'] == "Fee_transfer_via_coinbase", b["transactions"]["feeTransfer"]))
        fee_transfer_coinbase = sum( int(item['fee']) for item in fee_transfers_coinbase_list)

        # Sum all the fee transfers to this account with type of fee_transfer - these are the tx fees
        fee_transfers_creator_list = list(filter(lambda d: d['recipient'] == coinbase_receiver, fee_transfers_list))
        fee_transfers_creator = sum(int(item['fee']) for item in fee_transfers_creator_list)

        # Sum all the fee transfers not to this account with type of fee_transfer - this is snark work for the included tx
        fee_transfers_snarkers = fee_transfers - fee_transfers_creator

        # Determine the supercharged weighting for the block
        # New way uses fee transfers so we share the resulting profitability of the tx and take into account the coinbase snark
        supercharged_weighting = 1 + (1 / (1 + int(fee_transfers_creator) / (int(b["transactions"]["coinbase"]) - int(fee_transfer_coinbase))))

        # What are the rewards for the block - this is how we used to calculate it
        # this serves as a sense check currently to check logic
        total_rewards_prev_method = int(b["transactions"]["coinbase"]) + int( b["txFees"]) - int(b["snarkFees"])

        # Can also define this via fee transfers
        total_rewards = int(b["transactions"]["coinbase"]) + fee_transfers_creator - fee_transfer_coinbase

        # We calculate rewards multiple ways to sense check
        assert (total_rewards == total_rewards_prev_method)

        total_fees = int(validator_fee * total_rewards)

        epoch_rewards += total_rewards
        epoch_fees += total_fees
        epoch_blocks +=1


        blocks_table.append(
            {"epoch":epoch,
             "block_height":b['blockHeight'],
            "supercharged_weighting": supercharged_weighting,
            "coinbase": int(b["transactions"]["coinbase"]),
            "fee_transfers_creator": fee_transfers_creator,
            "fee_transfers_snarkers": fee_transfers_snarkers,
            "fee_transfer_coinbase":fee_transfer_coinbase,
            "timestamp":time_to_timestamp(b["dateTime"])})
        #handle foundation rewards firstly
        for p in payouts_table:
            if p["foundation_delegation"]:
                # Only pay foundation a % of the normal coinbase
                # Round down to the nearest nanomina
                foundation_block_reward = math.floor((p["staking_balance"] / epoch_staking_balance) * COINBASE *(1 - validator_fee))
                rewards_table.append({
                    "public_key": p["public_key"],
                    "block_height": b["blockHeight"],
                    "epoch": epoch,
                    "reward_amount": foundation_block_reward,
                    "foundation": True,
                    "timestamp": calculation_ts
                })
                foundation_payouts += foundation_block_reward
                p["payout_amount"] += foundation_block_reward
                assert (foundation_payouts <= total_rewards)

        # What are the remaining rewards we can share? This should always be higher than if we don't share.
        block_pool_share = total_rewards - (foundation_payouts / (1 - validator_fee))

        # handle non-foundation rewards
        sum_effective_pool_stakes = 0
        effective_pool_stakes = {}
        for p in payouts_table:
            if not p["foundation_delegation"]:
                supercharged_contribution = ((supercharged_weighting - 1) * p["timed_weighting"]) + 1
                effective_stake = p["staking_balance"] * supercharged_contribution
                # This the effective percentage of the pool disregarding the Foundation element
                effective_pool_stakes[p["public_key"]] = effective_stake
                sum_effective_pool_stakes += effective_stake

        for p in payouts_table:
            if not p["foundation_delegation"]:
                effective_pool_weighting = effective_pool_stakes[p["public_key"]] / sum_effective_pool_stakes
                # This must be less than 1 or we have a major issue
                assert effective_pool_weighting <= 1
                block_reward = math.floor(block_pool_share * effective_pool_weighting * (1 - validator_fee))
                rewards_table.append({
                    "public_key": p["public_key"],
                    "block_height": b["blockHeight"],
                    "epoch": epoch,
                    "reward_amount": block_reward,
                    "foundation":False,
                    "timestamp": calculation_ts
                })

                p["payout_amount"] += block_reward
                other_payouts += block_reward

        # Final check
        # These are essentially the same but we allow for a tiny bit of nanomina rounding and worst case we never pay more
        assert (foundation_payouts + other_payouts + total_fees <= total_rewards)

    epochs_table = [{"epoch": epoch,
                     "ledger_hash": ledger_hash,
                     "staking_balance": epoch_staking_balance,
                     "staking_balance_foundation": epoch_staking_balance_foundation,
                     "rewards_amount": epoch_rewards,
                     "fee_amount": epoch_fees,
                     "blocks_count": epoch_blocks}]
    if not read_only:
        await ConnectorEpochs.insert(conn, epochs_table)
        await ConnectorBlocks.insert(conn, blocks_table)
        await ConnectorRewards.insert(conn, rewards_table)
        await ConnectorPayouts.insert(conn, payouts_table)

    for table in [epochs_table,blocks_table,rewards_table,payouts_table]:
        if table:
            logger.info(
            tabulate([row.values() for row in table],
                     headers=list(table[0].keys()),
                     tablefmt="pretty"))