import connexion
from typing import Dict
from typing import Tuple
from typing import Union

from openapi_server.models.cpnh_tsch200_response import CPNhTSCh200Response  # noqa: E501
from openapi_server.models.cpnh_tsch400_response import CPNhTSCh400Response  # noqa: E501
from openapi_server.models.cpnh_tsch_request import CPNhTSChRequest  # noqa: E501
from openapi_server.models.ly_danh_sch_sch200_response import LYDanhSChSCh200Response  # noqa: E501
from openapi_server.models.lyth_ng_tin_sch200_response import LYThNgTinSCh200Response  # noqa: E501
from openapi_server.models.lyth_ng_tin_sch404_response import LYThNgTinSCh404Response  # noqa: E501
from openapi_server.models.tosch_mi201_response import TOSChMI201Response  # noqa: E501
from openapi_server.models.tosch_mi_request import TOSChMIRequest  # noqa: E501
from openapi_server import util


def cp_nht_sch(book_id, body=None):  # noqa: E501
    """Cập nhật sách

    Thay thế toàn bộ dữ liệu sách. Các field optional (&#x60;isbn&#x60;, &#x60;publishedYear&#x60;, &#x60;price&#x60;) sẽ giữ nguyên giá trị cũ nếu không được truyền trong body.  &#x60;title&#x60;, &#x60;author&#x60;, &#x60;genre&#x60; là bắt buộc — thiếu sẽ raise &#x60;KeyError&#x60; → 500. # noqa: E501

    :param book_id: ID của sách (integer)
    :type book_id: 
    :param cpnh_tsch_request: 
    :type cpnh_tsch_request: dict | bytes

    :rtype: Union[CPNhTSCh200Response, Tuple[CPNhTSCh200Response, int], Tuple[CPNhTSCh200Response, int, Dict[str, str]]
    """
    cpnh_tsch_request = body
    if connexion.request.is_json:
        cpnh_tsch_request = CPNhTSChRequest.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def ly_danh_sch_sch(page=None, limit=None, genre=None, q=None):  # noqa: E501
    """Lấy danh sách sách

    Trả về danh sách sách có hỗ trợ phân trang, lọc theo thể loại và tìm kiếm full-text (không phân biệt hoa thường) trên &#x60;title&#x60; và &#x60;author&#x60;.  Thứ tự filter: genre trước → q sau → paginate. # noqa: E501

    :param page: Số trang, tối thiểu 1. Default: 1
    :type page: 
    :param limit: Số bản ghi/trang, clamp vào [1, 100]. Default: 20
    :type limit: 
    :param genre: Lọc theo thể loại chính xác
    :type genre: str
    :param q: Tìm kiếm trong &#x60;title&#x60; hoặc &#x60;author&#x60; (case-insensitive, substring match)
    :type q: str

    :rtype: Union[LYDanhSChSCh200Response, Tuple[LYDanhSChSCh200Response, int], Tuple[LYDanhSChSCh200Response, int, Dict[str, str]]
    """
    return 'do some magic!'


def ly_thng_tin_sch(book_id):  # noqa: E501
    """Lấy thông tin sách

     # noqa: E501

    :param book_id: ID của sách (integer)
    :type book_id: 

    :rtype: Union[LYThNgTinSCh200Response, Tuple[LYThNgTinSCh200Response, int], Tuple[LYThNgTinSCh200Response, int, Dict[str, str]]
    """
    return 'do some magic!'


def to_sch_mi(body=None):  # noqa: E501
    """Tạo sách mới

    Tạo một cuốn sách mới. &#x60;id&#x60; được server tự gán bằng &#x60;len(BOOKS) + 1&#x60;.  **Lưu ý:** Nếu &#x60;title&#x60;, &#x60;author&#x60;, hoặc &#x60;genre&#x60; vắng mặt trong body, server sẽ raise &#x60;KeyError&#x60; và trả về 500 (thiếu validation ở tầng app). # noqa: E501

    :param tosch_mi_request: 
    :type tosch_mi_request: dict | bytes

    :rtype: Union[None, Tuple[None, int], Tuple[None, int, Dict[str, str]]
    """
    tosch_mi_request = body
    if connexion.request.is_json:
        tosch_mi_request = TOSChMIRequest.from_dict(connexion.request.get_json())  # noqa: E501
    return 'do some magic!'


def xa_sch(book_id):  # noqa: E501
    """Xóa sách

     # noqa: E501

    :param book_id: ID của sách (integer)
    :type book_id: 

    :rtype: Union[None, Tuple[None, int], Tuple[None, int, Dict[str, str]]
    """
    return 'do some magic!'
