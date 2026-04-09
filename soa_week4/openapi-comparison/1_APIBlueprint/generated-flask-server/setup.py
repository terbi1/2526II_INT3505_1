import sys
from setuptools import setup, find_packages

NAME = "openapi_server"
VERSION = "1.0.0"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = [
    "connexion>=2.0.2",
    "swagger-ui-bundle>=0.0.2",
    "python_dateutil>=2.6.0"
]

setup(
    name=NAME,
    version=VERSION,
    description="Book Management API",
    author_email="",
    url="",
    keywords=["OpenAPI", "Book Management API"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={'': ['openapi/openapi.yaml']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['openapi_server=openapi_server.__main__:main']},
    long_description="""\
    API quản lý sách đơn giản viết bằng Flask. Hỗ trợ tìm kiếm, lọc theo thể loại, phân trang, và các thao tác CRUD cơ bản.  **Base path:** &#x60;/v1&#x60;  ## Lưu ý về kiểu dữ liệu  - &#x60;book_id&#x60; trong URL là **integer** (vd: &#x60;1&#x60;, &#x60;2&#x60;), không phải string.  - &#x60;GET /v1/books/&lt;book_id&gt;&#x60; và &#x60;PUT&#x60;, &#x60;DELETE&#x60; tương tự — Flask nhận string từ URL   nhưng BOOKS store dùng integer key.  - Các field &#x60;isbn&#x60;, &#x60;publishedYear&#x60;, &#x60;price&#x60; là **optional** khi tạo/cập nhật sách.  ---  ## Mã lỗi  | Code | HTTP | Mô tả | |---|---|---| | &#x60;INVALID_PARAM&#x60; | 400 | Query param sai kiểu hoặc giá trị không hợp lệ | | &#x60;BAD_REQUEST&#x60; | 400 | Request body không phải JSON hợp lệ | | &#x60;BOOK_NOT_FOUND&#x60; | 404 | Không tìm thấy sách với ID đã cho | | &#x60;NOT_FOUND&#x60; | 404 | Route không tồn tại | | &#x60;METHOD_NOT_ALLOWED&#x60; | 405 | HTTP method không được hỗ trợ | | &#x60;INTERNAL_ERROR&#x60; | 500 | Lỗi server nội bộ |  ---
    """
)

