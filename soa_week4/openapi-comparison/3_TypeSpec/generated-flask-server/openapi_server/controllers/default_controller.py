import connexion
from typing import Dict
from typing import Tuple
from typing import Union

from openapi_server.models.root_ping200_response import RootPing200Response  # noqa: E501
from openapi_server import util


def root_ping():  # noqa: E501
    """root_ping

    Ping endpoint. Trả về chuỗi cố định. Không liên quan đến base path /v1. # noqa: E501


    :rtype: Union[RootPing200Response, Tuple[RootPing200Response, int], Tuple[RootPing200Response, int, Dict[str, str]]
    """
    return 'do some magic!'
