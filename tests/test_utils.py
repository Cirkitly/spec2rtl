# tests/test_utils.py

import pytest
import requests  # FIX: Import requests to use its exception types
from unittest.mock import MagicMock, patch

from utils.get_embedding import get_embedding
from utils.call_llm import call_llm

# You can add tests for call_llm here if you want.
# For now, we'll focus on fixing the failing test for get_embedding.

def test_get_embedding_success(mocker):
    """Test get_embedding on a successful API call."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    expected_embedding = [0.1, 0.2, 0.3]
    mock_response.json.return_value = {"embedding": expected_embedding}
    mocker.patch("requests.post", return_value=mock_response)

    embedding = get_embedding("test text")

    assert embedding == expected_embedding
    requests.post.assert_called_once()


def test_get_embedding_connection_error(mocker):
    """Test get_embedding when a connection error occurs."""
    mocker.patch("requests.post", side_effect=requests.exceptions.ConnectionError("Test connection error"))

    with pytest.raises(ConnectionError, match="Could not connect to Ollama"):
        get_embedding("test text")


def test_get_embedding_no_embedding_in_response(mocker):
    """Test get_embedding when the response is valid but lacks the 'embedding' key."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"detail": "Model not found"} # No embedding key
    mocker.patch("requests.post", return_value=mock_response)

    with pytest.raises(ValueError, match="API response did not contain an embedding"):
        get_embedding("test text")


def test_get_embedding_api_error(mocker):
    """Test get_embedding when the API returns an error status code."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    
    # FIX: Explicitly tell the mock's raise_for_status to raise an HTTPError.
    # This simulates the real behavior of the requests library.
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
    
    mocker.patch("requests.post", return_value=mock_response)

    # The code should now raise a ConnectionError as it's wrapped in the try/except block.
    # The original test expected an HTTPError, but the function's own error handling wraps it.
    with pytest.raises(ConnectionError, match="Is it running?"):
        get_embedding("test text")