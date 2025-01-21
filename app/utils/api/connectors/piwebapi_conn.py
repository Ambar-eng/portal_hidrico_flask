from app.utils.api.connectors.utils import is_open

from app.utils.utils import PATH_ENV
from app.utils.utils import get_env
from app.utils.api.connectors.utils import ThreadWithReturnValue


class PIWebAPI(object):
    def __init__(self):
        pass

    @staticmethod
    def check_connection():
        timeout = 5
        thread = ThreadWithReturnValue(
            target=is_open,
            args=(
                get_env('PIWEBAPI_IP', path_env=PATH_ENV),
                get_env('PIWEBAPI_PORT', path_env=PATH_ENV)
            )
        )
        thread.start()
        r = thread.join(timeout=timeout)
        return r is not None
