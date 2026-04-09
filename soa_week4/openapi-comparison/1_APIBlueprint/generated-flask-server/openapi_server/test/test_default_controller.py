import unittest

from flask import json

from openapi_server.models.cpnh_tsch200_response import CPNhTSCh200Response  # noqa: E501
from openapi_server.models.cpnh_tsch400_response import CPNhTSCh400Response  # noqa: E501
from openapi_server.models.cpnh_tsch_request import CPNhTSChRequest  # noqa: E501
from openapi_server.models.ly_danh_sch_sch200_response import LYDanhSChSCh200Response  # noqa: E501
from openapi_server.models.lyth_ng_tin_sch200_response import LYThNgTinSCh200Response  # noqa: E501
from openapi_server.models.lyth_ng_tin_sch404_response import LYThNgTinSCh404Response  # noqa: E501
from openapi_server.models.tosch_mi201_response import TOSChMI201Response  # noqa: E501
from openapi_server.models.tosch_mi_request import TOSChMIRequest  # noqa: E501
from openapi_server.test import BaseTestCase


class TestDefaultController(BaseTestCase):
    """DefaultController integration test stubs"""

    def test_cp_nht_sch(self):
        """Test case for cp_nht_sch

        Cập nhật sách
        """
        cpnh_tsch_request = openapi_server.CPNhTSChRequest()
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/v1/books/{book_id}'.format(book_id=1),
            method='PUT',
            headers=headers,
            data=json.dumps(cpnh_tsch_request),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_ly_danh_sch_sch(self):
        """Test case for ly_danh_sch_sch

        Lấy danh sách sách
        """
        query_string = [('page', 1),
                        ('limit', 20),
                        ('genre', 'sci-fi'),
                        ('q', 'q_example')]
        headers = { 
            'Accept': '*/*',
        }
        response = self.client.open(
            '/v1/books',
            method='GET',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_ly_thng_tin_sch(self):
        """Test case for ly_thng_tin_sch

        Lấy thông tin sách
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/v1/books/{book_id}'.format(book_id=1),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_to_sch_mi(self):
        """Test case for to_sch_mi

        Tạo sách mới
        """
        tosch_mi_request = openapi_server.TOSChMIRequest()
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/v1/books',
            method='POST',
            headers=headers,
            data=json.dumps(tosch_mi_request),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_xa_sch(self):
        """Test case for xa_sch

        Xóa sách
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/v1/books/{book_id}'.format(book_id=1),
            method='DELETE',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
