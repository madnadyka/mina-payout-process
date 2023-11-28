import CodaClient
import time
from utils import *
from constants import *
import asyncio
import traceback
from db_model.dao import ConnectorPayouts


GRAPHQL_HOST = config["NODE"]["graphql_host"]
GRAPHQL_PORT = config["NODE"]["graphql_port"]
DEFAULT_FEE = int(config["NODE"]["default_tx_fee"])


WALLET_PASSWORD =  config["VALIDATOR"]["password"]
VALIDATOR_NAME = config["VALIDATOR"]["name"]
SEND_FROM = config["VALIDATOR"]["address"]

graphql = CodaClient.Client(graphql_host=GRAPHQL_HOST, graphql_port=GRAPHQL_PORT)



async def send_payout(app):
    await asyncio.sleep(60)
    while True:
        try:
            async with app.db_pool.acquire() as conn:
                async with conn.transaction():
                    payouts = await ConnectorPayouts.get_data_by_status(conn, TX_CREATED)
                    if not payouts: continue
                    try:
                        graphql.unlock_wallet(SEND_FROM, WALLET_PASSWORD)
                        for payout in payouts:
                            if payout["public_key"] == SEND_FROM: continue #do not handle own rewards
                            await handle_payout(conn, payout)
                    except:
                        raise
                    finally:
                        graphql.lock_wallet(SEND_FROM)
            await asyncio.sleep(3600)
        except Exception:
            logger.error("send_payout error")
            logger.error(traceback.format_exc())
            await asyncio.sleep(600)

async def check_payout(app):
    await asyncio.sleep(60)
    while True:
        try:
            async with app.db_pool.acquire() as conn:
                async with conn.transaction():
                    payouts = await ConnectorPayouts.get_data_by_status(conn, TX_PENDING)
                    if not payouts: continue
                    for payout in payouts:
                        status = TX_PENDING
                        payment_id = payout["payment_id"]
                        tx_data = graphql.get_transaction_status(payment_id)
                        if "error" in str(tx_data):
                            logger.error(f'Can\'t get TX status {tx_data}')
                            continue
                        elif "pending" in str(tx_data) or "PENDING" in str(tx_data):
                            logger.warning(f'Tx has pending status: https://minaexplorer.com/payment/{payment_id}')
                        elif "INCLUDED" in str(tx_data) or "included" in str(tx_data):
                            logger.warning(f'Transaction sent successfully: https://minaexplorer.com/payment/{payment_id}')
                            status = TX_CONFIRMED
                        if status == TX_PENDING  and (int(time.time()) - payout["timestamp"])>3600:
                            status = TX_ERROR
                        if payout["status"]!= status:
                            payout["status"] = status
                            await ConnectorPayouts.upsert(conn, payout, ["public_key", "epoch"], ["status"])
            await asyncio.sleep(300)
        except Exception:
            logger.error("check_payout error")
            logger.error(traceback.format_exc())
            await asyncio.sleep(600)

async def handle_payout(conn, payout):
    delegator_addr = payout["public_key"]
    payout_in_nanomina = int(payout["payout_amount"])
    epoch = payout["epoch"]
    if payout_in_nanomina>0:
        MEMO = f'payout_from_{VALIDATOR_NAME}_Epoch_{epoch}'
        # PAYOUTS STARTS HERE
        result = send_transaction(
            to_address=delegator_addr,
            amount_nanomina=payout_in_nanomina,
            from_address = SEND_FROM,
            fee_nanomina = DEFAULT_FEE,
            memo = MEMO)
        logger.info("payout for epoch %s is sent from %s to %s, amount [%s]" %(epoch, SEND_FROM, delegator_addr, payout_in_nanomina))
        if result:
            payout["payment_id"] = result["sendPayment"]["payment"]["id"]
            payout["status"] = 1
            payout["timestamp"] = int(time.time())
            await ConnectorPayouts.upsert(conn,payout, ["public_key", "epoch"], ["payment_id", "status", "timestamp"])
    else:
        payout["status"] = TX_NOT_HANDLE
        await ConnectorPayouts.upsert(conn, payout, ["public_key", "epoch"], ["status"])




def send_transaction(to_address, amount_nanomina, from_address, fee_nanomina, memo):
    if fee_nanomina > 1e9:
        exit(f"Tx fee is too high {fee_nanomina}")

    trans_res = graphql.send_payment(to_pk=to_address,
                                     from_pk=from_address,
                                     amount=amount_nanomina,
                                     fee=fee_nanomina,
                                     memo=memo)
    return trans_res
