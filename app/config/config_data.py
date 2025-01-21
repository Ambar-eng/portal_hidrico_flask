from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pytz
from itertools import product
from ..database.cosmos_client import CosmosClientWrapper

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

class ConfigData:
    _instance = None

    def __new__(cls, *args, **kwargs):
        cls._instance = super().__new__(cls)
        return cls._instance
    
    @staticmethod
    def get_instance(json_app_data, cosmos_credentials):
        if not ConfigData._instance:
            ConfigData._instance = ConfigData(json_app_data, cosmos_credentials)
        return ConfigData._instance


    def __init__(self, json_app_data, cosmos_credentials):

        self.cosmos_client = CosmosClientWrapper.get_instance(
            cosmos_credentials["COSMOSDB_URI"],
            cosmos_credentials["COSMOSDB_KEY"],
            cosmos_credentials["DATABASE_NAME"],
            cosmos_credentials["PH_CMZ"],
            cosmos_credentials["PH_MLP"],
            cosmos_credentials["PH_ANT"],
            cosmos_credentials["TIME_INTERVAL"]
        )

        self.current_time = pd.to_datetime(datetime.now(tz=pytz.timezone('America/Santiago')).strftime("%Y-%m-%d %H:%M:%S")).floor("30min")

    def format_day_part(self, value):
        parts = value.split('-')
        day_part = parts[0]
        if len(day_part) == 1 and day_part.isdigit():
            day_part = f'0{day_part}'
        return f'{day_part}-{parts[1]}'
    
    def pull_data_flot(self, cosmos_container):
        # Retrieve data
        items = list(cosmos_container.query_items(query="SELECT * FROM c", enable_cross_partition_query=True))

        data_read = pd.DataFrame(items)

        return data_read