import os
import fnmatch
import pandas as pd
from io import BytesIO
from azure.storage.filedatalake import DataLakeServiceClient

from app.utils.utils import get_env


def get_all_files(root, pattern='*', extension='.csv', lowerize=False):
    """

    Get all the tree path from a root path filtering by a pattern an a extension

    :param root:
    :param pattern:
    :param extension:
    :param lowerize:
    :return:
    """
    path_files = []
    root = os.path.normpath(root)
    pattern = pattern.lower() if lowerize else pattern
    for root, dirs, files in os.walk(root):
        for f in files:
            full_path_file = os.path.join(root, f)
            full_path_file_ = full_path_file.lower() if lowerize else full_path_file
            if fnmatch.fnmatch(full_path_file_, pattern) and extension in full_path_file:
                path_files.append(full_path_file)
    return path_files


class DataLakeAPIClient(object):
    """
    This API is generated with the purpose of making the DataLake management easy.
    It is based on the DataLakeServiceClient with extra functionalities.
    """

    def __init__(
            self,
            file_system: str
    ):
        """
        :param file_system:
        """
        self.service_client = DataLakeServiceClient(
            account_url=get_env('ADP_DL_ACCOUNT_URL'))

        self.file_system_client = None
        self.set_file_system(file_system)

    def set_file_system(self, file_system):
        try:
            if file_system is not None:
                self.file_system_client = self.service_client.get_file_system_client(file_system=file_system)
        except Exception as e:
            print(e)

    def get_data(self, path: str, func_loader: any = lambda x: x):
        if self.file_system_client.get_file_client(path).exists():
            dl_file = self.file_system_client.get_file_client(path)
            dw = dl_file.download_file()
            data = dw.readall()
            return func_loader(BytesIO(data))
        else:
            return None

    def download_dir_and_files(
            self,
            remote_base_path: str,
            local_base_path: str,
            filter_='',
            overwrite=True
    ):
        """
        :param remote_base_path: DataLake path
        :param local_base_path: Local path
        :param filter_: path filtering. "if filter_ in _remote_path"
        :param overwrite:
        :return:
        """
        remote_paths = self.file_system_client.get_paths(path=remote_base_path, recursive=True)
        for remote_path in remote_paths:
            _remote_path = remote_path.name
            _relative_remote_path = _remote_path[_remote_path.find(remote_base_path) + len(remote_base_path):]
            local_path = f'{local_base_path}/{_relative_remote_path}'
            if remote_path.is_directory:
                if not os.path.exists(local_path):
                    os.makedirs(local_path)
            else:
                if not os.path.exists(os.path.dirname(local_path)):
                    os.makedirs(os.path.dirname(local_path))

                file_client = self.file_system_client.get_file_client(remote_path.name)

                if filter_ in _remote_path:
                    if overwrite or not os.path.exists(local_path):
                        with open(local_path, 'wb') as local_file:
                            print(remote_path.name)
                            download = file_client.download_file()
                            downloaded_bytes = download.readall()
                            local_file.write(downloaded_bytes)

    def get_paths(
            self,
            path=None,
            recursive=True,
            max_results=None,
            **kwargs
    ):
        """

        :param path: from DL
        :param recursive:
        :param max_results:
        :param kwargs:
        :return:
        """
        return self.file_system_client.get_paths(path=path, recursive=recursive, max_results=max_results, **kwargs)

    def get_path_by_month(
            self,
            path_,
            recursive=True,
            **kwargs):

        self.file_system_client.get_paths(path=path_, recursive=recursive, **kwargs)

    def upload_dataframe(self, df: pd.DataFrame,
                         file_name: str,
                         remote_path: str,
                         overwrite=True,
                         verbose=True):
        if verbose:
            print('upload_file')
            print(f'\tfilename: {file_name}')
            print(f'\tremote_path: {remote_path}')
        directory_client = self.file_system_client.create_directory(directory=remote_path)
        file_client = directory_client.get_file_client(file_name)
        if not file_client.exists() or overwrite:
            if verbose:
                print('\tUploading File')
                file_client.upload_data(df, overwrite=True)
        else:
            if verbose:
                print('\tFile already exist')

    def upload_file(
            self,
            file_name: str,
            local_path: str,
            remote_path: str,
            overwrite=True,
            verbose=False
    ):
        """

        :param file_name: "file.extension"
        :param local_path:
        :param remote_path: path/from/datalake
        :param overwrite:
        :param verbose:
        :return:
        """
        if verbose:
            print('upload_file')
            print(f'\tfilename: {file_name}')
            print(f'\tlocal_path: {local_path}')
            print(f'\tremote_path: {remote_path}')
        directory_client = self.file_system_client.create_directory(directory=remote_path)
        local_file_path = f'{local_path}/{file_name}'
        file_client = directory_client.get_file_client(file_name)
        if not file_client.exists() or overwrite:
            if verbose:
                print('\tUploading File')
            with open(local_file_path, 'rb') as local_file:
                file_client.upload_data(local_file, overwrite=True)
        else:
            if verbose:
                print('\tFile already exist')

    def upload_dir_and_files(
            self,
            local_base_path,
            remote_path,
            overwrite=True,
            verbose=0
    ):
        """

        :param local_base_path: path/to/local/system
        :param remote_path: path/to/datalake
        :param overwrite:
        :param verbose:
        :return:
        """
        local_path_files = get_all_files(local_base_path, pattern='*', extension='')
        for local_path_file in local_path_files:
            _file_name = os.path.basename(local_path_file)
            _local_path = os.path.dirname(local_path_file)
            _relative_local_path = _local_path[_local_path.find(local_base_path) + len(local_base_path) + 1:]
            _remote_path = f'{remote_path}/{_relative_local_path}'

            if verbose > 0:
                print(f'{_relative_local_path}/{_file_name}->{_remote_path}/{_file_name}')

            self.upload_file(
                file_name=_file_name,
                local_path=_local_path,
                remote_path=_remote_path,
                overwrite=overwrite,
                verbose=verbose > 1
            )

    def delete_files(
            self,
            remote_paths: list,
    ):
        """

        :param remote_paths: list of datalake paths
        :return:
        """
        check_bool = True
        for file_to_delete in remote_paths:
            file_client = self.file_system_client.get_file_client(file_to_delete)
            if file_client.exists():
                file_client.delete_file()
            check_bool = check_bool and not file_client.exists()
        return check_bool

    def delete_directories(
            self,
            remote_dirs: list,
    ):
        """

        :param remote_dirs: list of datalake directories
        :return:
        """
        check_bool = True
        for d in remote_dirs:
            directory_client = self.file_system_client.get_directory_client(d)
            if directory_client.exists():
                directory_client.delete_directory()
            check_bool = check_bool and not directory_client.exists()
        return check_bool
