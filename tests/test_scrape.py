import pytest
import requests
import os
from unittest.mock import patch, Mock
from scripts.scrape import get_routes  # Importing from the correct path: 'scripts.scrape'

@patch('scripts.scrape.requests.post')  # Corrected the module path
def test_get_routes_success(mock_post):
    # Mock a successful API response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = '{"data": [{"routeid": "1", "routeno": "101"}]}'
    mock_post.return_value = mock_response

    # Call the function and assert
    response = get_routes()
    assert response.status_code == 200
    assert response.text == '{"data": [{"routeid": "1", "routeno": "101"}]}'

    # Verify that the function attempts to write to the correct file
    with open('routes.json', 'r') as f:
        content = f.read()
    assert content == '{"data": [{"routeid": "1", "routeno": "101"}]}'

@patch('scripts.scrape.requests.post')  # Corrected the module path
def test_get_routes_failure(mock_post):
    # Mock a failed API response
    mock_response = Mock()
    mock_response.status_code = 500
    mock_post.return_value = mock_response

    # Call the function and assert
    response = get_routes()
    assert response.status_code == 500

    # Ensure no file was written when the response failed
    assert not os.path.exists('routes.json')

@patch('scripts.scrape.requests.post')  # Corrected the module path
def test_get_routes_no_data(mock_post):
    # Mock a response with no data
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = '{}'
    mock_post.return_value = mock_response

    # Call the function and assert
    response = get_routes()
    assert response.status_code == 200
    assert response.text == '{}'

    # Verify that the function attempts to write to the correct file
    with open('routes.json', 'r') as f:
        content = f.read()
    assert content == '{}'
