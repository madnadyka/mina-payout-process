import signal
import sys
import uvloop
import db_model
import traceback
import asyncio
import asyncpg
import handlers
from utils import *
uvloop.install()

class App:
    def __init__(self, loop):
        self.loop = loop
        self.db_pool = False
        self.dsn = config["POSTGRESQL"]["dsn"]
        self.public_key = config["VALIDATOR"]["address"]
        self.background_tasks = []
        logger.info("Mina Payout service started ...")
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)
        asyncio.ensure_future(self.start(), loop=self.loop)


    async def start(self):
        # init_app database
        try:
            logger.info("Init db pool ")
            self.db_pool = await asyncpg.create_pool(dsn=self.dsn,
                                                     loop=self.loop)
            await db_model.create_db_model(self)
            self.background_tasks.append(self.loop.create_task(handlers.calc_rewards(self)))
            self.background_tasks.append(self.loop.create_task(handlers.send_payout(self)))
            self.background_tasks.append(self.loop.create_task(handlers.check_payout(self)))
        except Exception as err:
            logger.error("Start failed")
            logger.error(str(traceback.format_exc()))
            self.terminate(None, None)

    def _exc(self, a, b, c):
        return

    def terminate(self, a, b):
        self.loop.create_task(self.terminate_coroutine())

    async def terminate_coroutine(self):
        sys.excepthook = self._exc
        logger.error('Stop request received')
        [task.cancel() for task in self.background_tasks]
        if self.background_tasks: await asyncio.wait(self.background_tasks)
        if self.db_pool:
            await self.db_pool.close()
        logger.info("Server stopped")
        self.loop.stop()
        await asyncio.sleep(1)
        self.loop.close()



if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    app = App(loop)
    loop.run_forever()
    pending = asyncio.all_tasks()
    loop.run_until_complete(asyncio.gather(*pending))
    loop.close()

