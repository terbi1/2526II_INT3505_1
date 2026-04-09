import unittest

from flask import json

from openapi_server.models.api_error import ApiError  # noqa: E501
from openapi_server.models.book import Book  # noqa: E501
from openapi_server.models.book_list_response import BookListResponse  # noqa: E501
from openapi_server.models.create_book_request import CreateBookRequest  # noqa: E501
from openapi_server.models.genre import Genre  # noqa: E501
from openapi_server.models.update_book_request import UpdateBookRequest  # noqa: E501
from openapi_server.test import BaseTestCase


class TestBooksController(BaseTestCase):
    """BooksController integration test stubs"""

    def test_books_create(self):
        """Test case for books_create

        
        """
        create_book_request = {"author":"author","price":6.027456183070403,"isbn":"isbn","genre":"fiction","publishedYear":0,"title":"title"}
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/v1/books',
            method='POST',
            headers=headers,
            data=json.dumps(create_book_request),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_books_list(self):
        """Test case for books_list

        
        """
        query_string = [('page', 1),
                        ('limit', 20),
                        ('genre', openapi_server.Genre()),
                        ('q', 'q_example')]
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/v1/books',
            method='GET',
            headers=headers,
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_by_id_delete(self):
        """Test case for by_id_delete

        
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/v1/books/{book_id}'.format(book_id='book_id_example'),
            method='DELETE',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_by_id_get(self):
        """Test case for by_id_get

        
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/v1/books/{book_id}'.format(book_id='book_id_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_by_id_update(self):
        """Test case for by_id_update

        
        """
        update_book_request = {"author":"author","price":6.027456183070403,"isbn":"isbn","genre":"fiction","publishedYear":0,"title":"title"}
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/v1/books/{book_id}'.format(book_id='book_id_example'),
            method='PUT',
            headers=headers,
            data=json.dumps(update_book_request),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
