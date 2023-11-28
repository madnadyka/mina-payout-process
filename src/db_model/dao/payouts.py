from db_model.dao.dao import *

class ConnectorPayouts(Dao):
    __fields__ = [
        StringField(name="public_key"),
        IntegerField(name="epoch"),
        IntegerField(name="payout_amount"),
        IntegerField(name="staking_balance"),
        IntegerField(name="timed_weighting"),
        IntegerField(name="foundation"),
        IntegerField(name="timestamp"),
        StringField(name="payment_id"),
        IntegerField(name="status"),
    ]
    __table__ = 'payouts'


    @classmethod
    async def get_data(cls, conn, order_by = None, limit = None):
        _order_by = "ORDER BY " + order_by if order_by else ""
        _limit = "LIMIT " + str(limit) if limit else ""
        return await cls._select(conn, f"SELECT * FROM {cls.__table__} {_order_by} {_limit};")


    @classmethod
    async def get_data_by_status(cls, conn, status):
        return await cls._select(conn, f"SELECT * FROM {cls.__table__} WHERE status = $1;", (status,))

    @classmethod
    async def upsert(cls, conn, data, pk_columns_list, upsert_columns_list):
        await cls._upsert(conn, data, pk_columns_list, upsert_columns_list=upsert_columns_list)

    @classmethod
    async def insert(cls, conn, data, returning=None):
        return await cls._insert(conn, data, returning=returning)

    @classmethod
    async def delete_by_epoch(cls, conn, epoch):
        await conn.execute(f"DELETE FROM {cls.__table__}  WHERE epoch = $1;", epoch)