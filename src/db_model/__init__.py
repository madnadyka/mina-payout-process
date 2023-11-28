

async def create_db_model(app):
    async with app.db_pool.acquire() as conn:
        level = await conn.fetchval("SHOW TRANSACTION ISOLATION LEVEL;")

        if level != "repeatable read":
           raise Exception("Postgres repeatable read isolation "
                           "level required! current isolation level is %s" % level)

        await conn.execute(open("./db_model/sql/schema.sql", "r", encoding='utf-8').read().replace("\n", " "))

