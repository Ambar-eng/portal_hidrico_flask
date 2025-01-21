import pandas as pd
from typing import Union
import databricks.sql as sql

from app.utils.utils import PATH_ENV
from app.utils.utils import get_env
from app.utils.api.connectors.utils import ThreadWithReturnValue

DEFAULT_CONFIG = {
    'table': 'mlp_raw.pi_system_data',
    'col_tag': 'id_tag',
    'col_time': 'timestamp',
    'col_value': 'valor',
    'fmt': '%Y-%m-%dT%H:%M:%S.000+0000'
}


class Databricks(object):
    def __init__(
            self,
            server_hostname: str,
            http_path: str,
            access_token: str,
            config: dict = None

    ):
        self.server_hostname = server_hostname
        self.http_path = http_path
        self.access_token = access_token
        self.config = DEFAULT_CONFIG if config is None else config

    def _get_conn_scope(self):
        return sql.connect(
            server_hostname=self.server_hostname,
            http_path=self.http_path,
            access_token=self.access_token)

    def _execute(self, query: str):
        with self._get_conn_scope() as _connection:
            with _connection.cursor() as _cursor:
                _cursor.execute(query)
                return _cursor.fetchall()

    def execute(self, query: str, as_dataframe=True):
        _r_list = self._execute(query=query)
        r_list = [el.asDict() for el in _r_list]
        if as_dataframe:
            _df = pd.DataFrame(r_list)
            return _df
        return r_list

    def check_connection(self, timeout=10):
        def __execute():
            return self.execute("SHOW SCHEMAS", as_dataframe=True)

        thread = ThreadWithReturnValue(target=__execute)
        thread.start()
        r = thread.join(timeout=timeout)
        return r is not None

    def query__get_tags(
            self,
            tag: Union[str, list],
            start_time: str,
            end_time: str,
            input_fmt: str,
    ):
        """

        :param tag:
        :param start_time:
        :param end_time:
        :param input_fmt:
        :return:
        """
        if isinstance(tag, str):
            tag_string = f"{self.config['col_tag']} in ('{tag}')"
        elif isinstance(tag, list):
            _t = ",".join([f"'{t}'" for t in tag])
            tag_string = f"{self.config['col_tag']} in ({_t})"
        else:
            raise Exception('tag instance should be str or list')

        start_time = pd.to_datetime(start_time, format=input_fmt).strftime(self.config['fmt'])
        end_time = pd.to_datetime(end_time, format=input_fmt).strftime(self.config['fmt'])

        query = \
            f"""
             SELECT {self.config['col_time']}, {self.config['col_value']}, {self.config['col_tag']}
             FROM {self.config['table']}
             WHERE 
                 {tag_string} AND
                 {self.config['col_time']} >= '{start_time}' AND 
                 {self.config['col_time']} <= '{end_time}'
             """

        return query

    def query__list_tags(
            self,
            tags_like: Union[str, None],
            start_time: str,
            end_time: str,
            input_fmt: str,
    ):
        """

        :param tags_like:
        :param start_time:
        :param end_time:
        :param input_fmt:
        :return:
        """
        start_time = pd.to_datetime(start_time, format=input_fmt).strftime(self.config['fmt'])
        end_time = pd.to_datetime(end_time, format=input_fmt).strftime(self.config['fmt'])

        string_like = f"AND {self.config['col_tag']} LIKE '{tags_like}' " if tags_like is not None else ''

        query = \
            f"""
                    SELECT DISTINCT({self.config['col_tag']}) 
                    FROM {self.config['table']}
                    WHERE 
                        {self.config['col_time']} >= '{start_time}' AND 
                        {self.config['col_time']} <= '{end_time}'
                        {string_like}
                    ORDER BY {self.config['col_tag']} ASC
                    """
        return query


if __name__ == '__main__':
    client = Databricks(
        server_hostname=get_env("DATABRICKS_SERVER_HOSTNAME", path_env=PATH_ENV),
        http_path=get_env("DATABRICKS_HTTP_PATH", path_env=PATH_ENV),
        access_token=get_env("DATABRICKS_TOKEN", path_env=PATH_ENV),
    )
    _r = client.check_connection()
    