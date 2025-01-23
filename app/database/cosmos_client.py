from azure.cosmos import CosmosClient, PartitionKey
from datetime import datetime, timedelta

class CosmosClientWrapper:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, 
                 cosmosdb_uri: str, 
                 cosmosdb_key: str, 
                 database_name: str, 
                 ph_cmz: str, 
                 ph_mlp: str,
                 ph_ant: str):
        # Ensure we only run init code once
        if hasattr(self, 'initialized'):
            return
        
        self.initialized = True
        # Initialize Cosmos client
        self.cosmos_client = CosmosClient(cosmosdb_uri, credential=cosmosdb_key, connection_verify=True)
        self.database = self.cosmos_client.create_database_if_not_exists(id=database_name)

        # Create containers if not exist
        self.ph_cmz = self._create_container(ph_cmz)
        self.ph_mlp = self._create_container(ph_mlp)
        self.ph_ant = self._create_container(ph_ant)

        self.containers = {
            'PH_CMZ': self.ph_cmz,
            'PH_MLP': self.ph_mlp,
            'PH_ANT': self.ph_ant,
        }

    @classmethod
    def get_instance(cls,
                     cosmosdb_uri: str, 
                     cosmosdb_key: str, 
                     database_name: str, 
                     ph_cmz: str, 
                     ph_mlp: str,
                     ph_ant: str):
        if not cls._instance:
            cls._instance = CosmosClientWrapper(
                cosmosdb_uri, 
                cosmosdb_key, 
                database_name, 
                ph_cmz, 
                ph_mlp,
                ph_ant,
            )
        return cls._instance

    def _create_container(self, container_id: str):
        return self.database.create_container_if_not_exists(
            id=container_id,
            partition_key=PartitionKey(path='/id'),
            offer_throughput=400
        )

    def get_items_from_container(self, container_name: str, table: str, start_date: str = None, end_date: str = None):
        # If no date range is provided, default to the last 31 days
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=31)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.utcnow().strftime('%Y-%m-%d')

        query = (
            f"SELECT * FROM c "
            f"WHERE c.tabla = '{table}' "
            f"AND c.fecha >= '{start_date}' "
            f"AND c.fecha <= '{end_date}'"
        )

        container = self.containers[container_name]
        items = list(container.query_items(query=query, enable_cross_partition_query=True))

        # Format date fields if necessary
        for item in items:
            if 'fecha' in item:
                try:
                    item['fecha'] = datetime.strptime(item['fecha'], '%Y-%m-%d').strftime('%Y-%m-%d')
                except ValueError:
                    # Handle invalid date format
                    item['fecha'] = '0'

        return items if items else []