import connexion
from typing import Dict
from typing import Tuple
from typing import Union

from openapi_server.models.ping200_response import Ping200Response  # noqa: E501
from openapi_server import util


def ping():  # noqa: E501
    """Ping

    Endpoint kiểm tra server còn sống. Không thuộc prefix &#x60;/v1&#x60;. # noqa: E501


    :rtype: Union[Ping200Response, Tuple[Ping200Response, int], Tuple[Ping200Response, int, Dict[str, str]]
    """
    return 'do some magic!'
