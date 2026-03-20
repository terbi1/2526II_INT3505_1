# swagger_client.BooksApi

All URIs are relative to *http://127.0.0.1:5000*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_book**](BooksApi.md#create_book) | **POST** /v1/books | Create a new book
[**delete_book**](BooksApi.md#delete_book) | **DELETE** /v1/books/{book_id} | Delete a book
[**get_book**](BooksApi.md#get_book) | **GET** /v1/books/{book_id} | Get a book by ID
[**list_books**](BooksApi.md#list_books) | **GET** /v1/books | List all books
[**update_book**](BooksApi.md#update_book) | **PUT** /v1/books/{book_id} | Update a book

# **create_book**
> Book create_book(body)

Create a new book

Add a new book to the collection.

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.BooksApi()
body = swagger_client.BookInput() # BookInput | 

try:
    # Create a new book
    api_response = api_instance.create_book(body)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling BooksApi->create_book: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**BookInput**](BookInput.md)|  | 

### Return type

[**Book**](Book.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **delete_book**
> delete_book(book_id)

Delete a book

Remove a book from the collection by ID.

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.BooksApi()
book_id = 56 # int | The integer ID of the book

try:
    # Delete a book
    api_instance.delete_book(book_id)
except ApiException as e:
    print("Exception when calling BooksApi->delete_book: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **book_id** | **int**| The integer ID of the book | 

### Return type

void (empty response body)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **get_book**
> Book get_book(book_id)

Get a book by ID

Returns the full details of a single book.

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.BooksApi()
book_id = 56 # int | The integer ID of the book

try:
    # Get a book by ID
    api_response = api_instance.get_book(book_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling BooksApi->get_book: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **book_id** | **int**| The integer ID of the book | 

### Return type

[**Book**](Book.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_books**
> InlineResponse200 list_books(page=page, limit=limit, genre=genre, q=q)

List all books

Returns a paginated list of books with optional filtering by genre and keyword search.

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.BooksApi()
page = 1 # int | Page number (starts at 1) (optional) (default to 1)
limit = 20 # int | Number of books per page (max 100) (optional) (default to 20)
genre = 'genre_example' # str | Filter by genre (optional)
q = 'q_example' # str | Search by title or author (optional)

try:
    # List all books
    api_response = api_instance.list_books(page=page, limit=limit, genre=genre, q=q)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling BooksApi->list_books: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **page** | **int**| Page number (starts at 1) | [optional] [default to 1]
 **limit** | **int**| Number of books per page (max 100) | [optional] [default to 20]
 **genre** | **str**| Filter by genre | [optional] 
 **q** | **str**| Search by title or author | [optional] 

### Return type

[**InlineResponse200**](InlineResponse200.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_book**
> Book update_book(body, book_id)

Update a book

Fully replace the data of an existing book.

### Example
```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.BooksApi()
body = swagger_client.BookInput() # BookInput | 
book_id = 56 # int | The integer ID of the book

try:
    # Update a book
    api_response = api_instance.update_book(body, book_id)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling BooksApi->update_book: %s\n" % e)
```

### Parameters

Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **body** | [**BookInput**](BookInput.md)|  | 
 **book_id** | **int**| The integer ID of the book | 

### Return type

[**Book**](Book.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

