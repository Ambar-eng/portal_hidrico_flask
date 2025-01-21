from app.utils.api.connectors.utils import ThreadWithReturnValue
from app.utils.api.dl_api import DataLakeAPIClient


class Datalake(DataLakeAPIClient):
    def check_connection(self, timeout=5):
        dir_client = None
        try:
            dir_client = self.service_client.get_directory_client(file_system='repos', directory='/')
        except Exception as ex:
            print(ex)
        assert dir_client is not None

        # EXECUTE dir_client.exists AND WAIT UNTIL "timeout" SECONDS

        thread = ThreadWithReturnValue(target=dir_client.exists, args=())
        thread.start()
        r = thread.join(timeout=timeout)
        return r


if __name__ == '__main__':
    api = Datalake(file_system='repos')
    r = api.check_connection()

    print()
