
import pandas as pd
from azure.cosmos import CosmosClient

from app.utils.utils import PATH_ENV
from app.utils.utils import get_env
from app.utils.api.connectors.utils import ThreadWithReturnValue

try:
    from etl.azure.cosmosdb.api import CosmosDB as _CosmosDB

    _url = get_env('COSMOSDB_WORKSPACE', path_env=PATH_ENV)
    _credential = get_env('COSMOSDB_SECRET', path_env=PATH_ENV)


    class CosmosDB(_CosmosDB):
        def __init__(
                self,
                url=_url,
                credential=_credential
        ):
            self.client = CosmosClient(
                url=url,
                credential=credential
            )

        # TODO: migrate to MLP_ETL
        def get_tags(
                self,
                cosmos_database_name: str,
                cosmos_table_name: str,
                start_time: str,
                end_time: str,
                fmt_input: str,
                tags: list,
                parallel=False,
                n_tag_batches=1
        ):
            fmt_out = '%Y-%m-%d %H:%M:%S'
            start_time = pd.to_datetime(start_time, format=fmt_input).strftime(fmt_out)
            end_time = pd.to_datetime(end_time, format=fmt_input).strftime(fmt_out)
            if isinstance(tags, str):
                where_condition = f'i.id_tag = "{tags}"'
            elif isinstance(tags, list) and len(tags) == 1:
                where_condition = f'i.id_tag = "{tags[0]}"'
            elif isinstance(tags, list) and len(tags) > 1:
                tags_str = '(' + ','.join([f'"{t}"' for t in tags]) + ')'
                where_condition = f"i.id_tag in {tags_str}"
            else:
                raise Exception('tags should be str or list with string elements')

            q = f"""
            SELECT 
            c.timestamp,
            ARRAY(SELECT i.id_tag, i.valor  FROM i IN c.items where {where_condition}) as item
            FROM c WHERE c.timestamp between "{start_time}" and "{end_time}"
            """
            database = self.client.get_database_client(cosmos_database_name)
            container = database.get_container_client(cosmos_table_name)
            data_list = []
            for j, data in enumerate(container.query_items(q, enable_cross_partition_query=True)):
                print(f"{j+1:04d}")
                df_item = pd.DataFrame(data['item'])
                df_item['timestamp'] = data['timestamp']
                data_list.append(df_item)
            df = pd.concat(data_list)[['timestamp', 'id_tag', 'valor']]
            df = df.reset_index(drop=True)
            return df


except Exception as e:
    print(e)


    class CosmosDB(object):
        def __init__(self):
            self.client = CosmosClient(
                url=get_env('COSMOSDB_WORKSPACE', path_env=PATH_ENV),
                credential=get_env('COSMOSDB_SECRET', path_env=PATH_ENV)
            )

        def execute(self):
            pass

        def check_connection(self, timeout=5):
            def list_dbs():
                dbs = list(self.client.list_databases())
                return dbs

            thread = ThreadWithReturnValue(target=list_dbs, args=())
            thread.start()
            _r = thread.join(timeout=timeout)
            return _r is not None

if __name__ == '__main__':
    api = CosmosDB()
    r = api.check_connection()
    d = api.get_tags(
        cosmos_database_name='ams-dataplatform-cosmosdb-mlp-notpii',
        cosmos_table_name='pi_system_data_interpolated',
        start_time="2023-02-10 00:00:00",
        end_time="2023-02-10 00:10:00",
        fmt_input='%Y-%m-%d %H:%M:%S',
        tags=["SINUSOID", "000:CANT_AAP_D"]
    )
    print('OK')
