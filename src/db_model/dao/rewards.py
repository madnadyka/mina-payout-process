from db_model.dao.dao import *

class ConnectorRewards(Dao):
    __fields__ = [
        StringField(name="public_key"),
        IntegerField(name="epoch"),
        IntegerField(name="block_height"),
        IntegerField(name="reward_amount"),
        IntegerField(name="foundation"),
        IntegerField(name="timestamp")
    ]
    __table__ = 'rewards'

    @classmethod
    async def get_data(cls, conn, order_by = None, limit = None):
        _order_by = "ORDER BY " + order_by if order_by else ""
        _limit = "LIMIT " + str(limit) if limit else ""
        return await cls._select(conn, f"SELECT * FROM {cls.__table__} {_order_by} {_limit};")

    @classmethod
    async def insert(cls, conn, data, returning=None):
        return await cls._insert(conn, data, returning=returning)

    @classmethod
    async def delete_by_epoch(cls, conn, epoch):
        await conn.execute(f"DELETE FROM {cls.__table__}  WHERE epoch = $1;", epoch)