from db_model.dao.dao import *
class ConnectorEpochs(Dao):
    __fields__ = [
        IntegerField(name="epoch"),
        StringField(name="ledger_hash"),
        IntegerField(name="staking_balance"),
        IntegerField(name="staking_balance_foundation"),
        IntegerField(name="rewards_amount"),
        IntegerField(name="fee_amount"),
        IntegerField(name="blocks_count"),
    ]
    __table__ = 'epochs'

    @classmethod
    async def get_data(cls, conn, order_by = None, limit = None):
        _order_by = "ORDER BY " + order_by if order_by else ""
        _limit = "LIMIT " + str(limit) if limit else ""
        return await cls._select(conn, f"SELECT * FROM {cls.__table__} {_order_by} {_limit};")

    @classmethod
    async def get_last_row(cls, conn):
        row = await cls._select_one(conn, f"SELECT * FROM {cls.__table__} ORDER BY epoch DESC LIMIT 1;")
        return row["epoch"] if row else None

    @classmethod
    async def insert(cls, conn, data, returning=None):
        return await cls._insert(conn, data, returning=returning)

    @classmethod
    async def delete_by_epoch(cls, conn, epoch):
        await conn.execute(f"DELETE FROM {cls.__table__}  WHERE epoch = $1;", epoch)