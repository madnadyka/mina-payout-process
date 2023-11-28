import json
import asyncpg
class Dao():
    __table__ = ''
    __fields__ = []

    def __init__(self, **kw):
        pass


    @classmethod
    async def _select(cls, conn, sql, args=None, json_load=True, **kwargs):
        stmt = await conn.prepare(sql)
        if args:
            models = await stmt.fetch(*args)
        else:
            models = await stmt.fetch()
        json_fields = [field.name for field in cls.__fields__ if field.column_type == "json"]
        for i, model in enumerate(models): models[i] = dict(model)
        if json_load and json_fields:
            for model in models:
                if json_load and json_fields:
                    json_load_fields(model,json_fields)
        return models

    @classmethod
    async def _select_one(cls, conn, sql, args=None, json_load=True, **kwargs):
        stmt = await conn.prepare(sql)
        if args:
            model = await stmt.fetchrow(*args)
        else:
            model = await stmt.fetchrow()
        if not model: return None
        json_fields = [field.name for field in cls.__fields__ if field.column_type=="json"]
        row = dict(model)
        if json_load and json_fields:
           json_load_fields(row, json_fields)
        return row

    @classmethod
    async def _insert(cls, conn, args, returning=None, json_dump=True, **kwargs):
        inserted_rows = cls.get_inserted_rows(args, json_dump)
        columns_list = [field.name for field in cls.__fields__]
        columns = ','.join(columns_list)
        placeholders_list = ["$"+str(i) for i in range(1,len(cls.__fields__)+1) ]
        placeholders = ','.join(placeholders_list)
        if len(inserted_rows)==1:
            if returning:
                stmt = await conn.prepare(f"INSERT INTO {cls.__table__} ({columns}) VALUES ({placeholders}) RETURNING {returning};")
                inserted_value = await stmt.fetchval(*inserted_rows[0])
                return inserted_value
            else:
                await conn.execute(f"INSERT INTO {cls.__table__} ({columns}) VALUES ({placeholders});", *inserted_rows[0])
        else:
            await conn.executemany(f"INSERT INTO {cls.__table__} ({columns}) VALUES ({placeholders});", inserted_rows)
        return True

    @classmethod
    async def _upsert(cls, conn, args, pk_columns_list, upsert_columns_list=None, json_dump=True, **kwargs):
        inserted_rows = cls.get_inserted_rows(args, json_dump)
        columns_list = [field.name for field in cls.__fields__]
        columns = ','.join(columns_list)
        placeholders_list = ["$"+str(i) for i in range(1,len(cls.__fields__)+1) ]
        placeholders = ','.join(placeholders_list)
        pk_columns = ','.join(pk_columns_list)
        if upsert_columns_list:
            upsert_columns= ','.join([column+"=$"+ str(columns_list.index(column)+1) for column in upsert_columns_list])
        else:
            upsert_columns = None
        if len(inserted_rows)==1:
            if upsert_columns_list:
                await conn.execute(f"INSERT INTO {cls.__table__} ({columns}) VALUES ({placeholders}) ON CONFLICT ({pk_columns}) DO UPDATE SET {upsert_columns};", *inserted_rows[0])
            else:
                await conn.execute(f"INSERT INTO {cls.__table__} ({columns}) VALUES ({placeholders}) ON CONFLICT ({pk_columns}) DO NOTHING;",*inserted_rows[0])
        else:
            if upsert_columns_list:
                await conn.executemany(f"INSERT INTO {cls.__table__} ({columns}) VALUES ({placeholders}) ON CONFLICT ({pk_columns}) DO UPDATE SET {upsert_columns};", inserted_rows)
            else:
                await conn.executemany(f"INSERT INTO {cls.__table__} ({columns}) VALUES ({placeholders}) ON CONFLICT ({pk_columns}) DO NOTHING;",inserted_rows)
        return True

    @classmethod
    def get_inserted_rows(cls, args, json_dump):
        inserted_rows=[]
        if isinstance(args, dict): args = [args]
        for v in args:
            inserted_row = []
            for field in cls.__fields__:
                val = v.get(field.name, field.default)
                if json_dump and field.column_type=="json":
                    val = json.dumps(val) if val else None
                inserted_row.append(val)
            inserted_rows.append(inserted_row)
        return inserted_rows

class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

class StringField(Field):
    def __init__(self, name, primary_key=False, default=None):
        super().__init__(name,'varchar', primary_key, default)

class BoolField(Field):
    def __init__(self, name, primary_key=False, default=None):
        super().__init__(name,'boolean', primary_key, default)

class IntegerField(Field):
    def __init__(self, name, primary_key=False, default=0):
        super().__init__(name, 'int', primary_key, default)

class BytesField(Field):
    def __init__(self, name, primary_key=False, default=None):
        super().__init__(name, 'bytea', primary_key, default)

class FloatField(Field):
    def __init__(self, name, primary_key=False, default=0.0):
        super().__init__(name,'numeric', primary_key, default)

class JsonField(Field):
    def __init__(self, name, default=None):
        super().__init__(name,'json', False, default)

def json_load_fields(model, json_fields):
    for field in json_fields:
        if field in model and model[field]:
            model[field] = json.loads(model[field])
