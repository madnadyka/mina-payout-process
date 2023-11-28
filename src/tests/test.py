import asyncio
import unittest
import handlers
from utils import *
import asyncpg
import db_model
from db_model.dao import ConnectorEpochs, ConnectorPayouts, ConnectorRewards, ConnectorBlocks

class AppTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.loop = asyncio.get_event_loop()
        self.dsn = config["POSTGRESQL"]["dsn"]
        self.db_pool = self.run_coroutine(asyncpg.create_pool(dsn=self.dsn,loop=self.loop))
        self.run_coroutine(db_model.create_db_model(self))


    def run_coroutine(self, co):
        return self.loop.run_until_complete(co)


    def test_get_epoch_for_calculation(self):
        async def test(self):
            test_epoch = 64
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    try:
                        last_calculated_epoch = await ConnectorEpochs.get_last_row(conn)
                        if not last_calculated_epoch: await ConnectorEpochs.insert(conn, {"epoch": test_epoch-1})
                        epochs_for_calculation = await handlers.get_uncalculated_epochs(conn)
                        self.assertTrue(test_epoch in epochs_for_calculation)
                        self.assertGreater(len(epochs_for_calculation),1)
                    except:
                        raise
                    finally:
                        await ConnectorEpochs.delete_by_epoch(conn, test_epoch - 1)
        self.run_coroutine(test(self))

    def test_calculate_rewards(self):
        async def test(self):
            test_epoch = 64
            public_key = "B62qq1xGN57tke8jJ3EuJMgFmgWQRoip6kKoBsTuLxsGXVqQXMN5oVj"
            async with self.db_pool.acquire() as conn:
                async with conn.transaction():
                    try:
                        await handlers.calculate_rewards(test_epoch, public_key, conn, read_only=False)
                        epochs = await ConnectorEpochs.get_data(conn)
                        epoch_exists = False
                        for epoch in epochs:
                            if epoch["epoch"] == test_epoch:
                                epoch_exists = True
                                self.assertEqual(epoch["ledger_hash"],"jx4MPGB51t9MjrUh7NSsU6dLaouAb9bE2xu8b79kzmkEtKezwfw")
                                self.assertEqual(epoch["staking_balance"],508913277477306)
                                self.assertEqual(epoch["rewards_amount"], 2880866200234)
                                self.assertEqual(epoch["fee_amount"],144043310011)
                                self.assertEqual(epoch["blocks_count"],2)
                        self.assertTrue(epoch_exists)
                        blocks = await ConnectorBlocks.get_data(conn)
                        block_count = 0
                        for block in blocks:
                            if epoch["epoch"] == test_epoch:
                                if block['block_height'] == 302260:
                                    block_count += 1
                                    self.assertEqual(block["epoch"], test_epoch)
                                    self.assertEqual(float(block["supercharged_weighting"]),1.999721535735473)
                                    self.assertEqual(block["coinbase"], 1440000000000)
                                    self.assertEqual(block["fee_transfers_creator"], 401100233)
                                    self.assertEqual(block["fee_transfers_snarkers"], 20899770)
                                    self.assertEqual(block["fee_transfer_coinbase"], 0)
                                if block['block_height'] == 303338:
                                    block_count += 1
                                    self.assertEqual(block["epoch"], test_epoch)
                                    self.assertEqual(float(block["supercharged_weighting"]),1.9996771181745399)
                                    self.assertEqual(block["coinbase"], 1440000000000)
                                    self.assertEqual(block["fee_transfers_creator"], 465100001)
                                    self.assertEqual(block["fee_transfers_snarkers"], 0)
                                    self.assertEqual(block["fee_transfer_coinbase"], 0)
                        self.assertEqual(block_count,2)

                        rewards = await ConnectorRewards.get_data(conn)
                        reward_by_public_key = {}
                        for reward in rewards:
                            if epoch["epoch"] == test_epoch:
                                try:
                                    reward_by_public_key[reward['public_key']]
                                except:
                                    reward_by_public_key[reward['public_key']] = 0
                                reward_by_public_key[reward['public_key']] += reward['reward_amount']
                        self.assertEqual(reward_by_public_key["B62qnruc8A4QWJJhESXN3AcQVQgYWCMNnkdf1vmujR3eyEuiuqhCxGf"], 2153604902584)
                        self.assertEqual(reward_by_public_key["B62qo85u3qL5J3oivYyMRkk21DMCkw5ijRq2qJwMzDZr25BMUNEU7Qx"], 490401968630)
                        self.assertEqual(reward_by_public_key["B62qq1xGN57tke8jJ3EuJMgFmgWQRoip6kKoBsTuLxsGXVqQXMN5oVj"], 92816019005)
                        payouts = await ConnectorPayouts.get_data(conn)
                        stakers_count = 0
                        for payout in payouts:
                            if epoch["epoch"] == test_epoch:
                                if payout['public_key'] == "B62qnruc8A4QWJJhESXN3AcQVQgYWCMNnkdf1vmujR3eyEuiuqhCxGf":
                                    self.assertEqual(payout['payout_amount'],2153604902584)
                                    self.assertEqual(payout['staking_balance'],387331731688753)
                                    self.assertEqual(payout["timed_weighting"],1)
                                    self.assertEqual(payout["foundation"], 0)
                                    stakers_count +=1
                                if payout['public_key'] == "B62qo85u3qL5J3oivYyMRkk21DMCkw5ijRq2qJwMzDZr25BMUNEU7Qx":
                                    self.assertEqual(payout['payout_amount'],490401968630)
                                    self.assertEqual(payout['staking_balance'],88200135273472)
                                    self.assertEqual(payout["timed_weighting"],1)
                                    self.assertEqual(payout["foundation"], 0)
                                    stakers_count += 1
                                if payout['public_key'] == "B62qq1xGN57tke8jJ3EuJMgFmgWQRoip6kKoBsTuLxsGXVqQXMN5oVj":
                                    self.assertEqual(payout['payout_amount'],92816019005)
                                    self.assertEqual(payout['staking_balance'],33381410515081)
                                    self.assertEqual(payout["timed_weighting"],0)
                                    self.assertEqual(payout["foundation"], 0)
                                    stakers_count += 1
                        self.assertEqual(stakers_count, 3)
                    except:
                        raise
                    finally:
                        await ConnectorEpochs.delete_by_epoch(conn, test_epoch)
                        await ConnectorBlocks.delete_by_epoch(conn, test_epoch)
                        await ConnectorRewards.delete_by_epoch(conn, test_epoch)
                        await ConnectorPayouts.delete_by_epoch(conn, test_epoch)
        self.run_coroutine(test(self))


    def tearDown(self) -> None:
        if self.loop:
            self.loop.run_until_complete(self.db_pool.close())


if __name__ == '__main__':
    unittest.main()