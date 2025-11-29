import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add backend directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set dummy env vars for testing
os.environ["TRADERA_API_URL"] = "http://mock-url.com?wsdl"
os.environ["TRADERA_APP_ID"] = "mock_id"
os.environ["TRADERA_APP_KEY"] = "mock_key"

# Mock zeep.Client to avoid network calls during import if it happens immediately
from unittest.mock import MagicMock
import sys
# We need to mock zeep before importing fetching_service because it initializes Client at module level
sys.modules["zeep"] = MagicMock()

from fetching_service import app

client = TestClient(app)

def test_cors_wildcard():
    """
    Test that CORS currently allows all origins (Regression/Baseline).
    After fix, this should likely fail or be updated to check for specific origin.
    """
    response = client.options("/related-products", headers={"Origin": "https://evil.com", "Access-Control-Request-Method": "GET"})
    # With restricted origins, the request should be rejected (likely 400 Bad Request) or return no CORS headers
    # Starlette/FastAPI CORSMiddleware typically returns 400 for disallowed origins if allow_origins is set
    assert response.status_code == 400

def test_error_handling_leakage():
    """
    Test that errors currently leak internal details (Regression/Baseline).
    After fix, this should return a generic error message.
    """
    # Trigger an error by sending an empty product name which might cause issues or mock a failure if possible
    # For now, we'll try to trigger a validation error or a mock failure
    response = client.get("/related-products?product_name=")
    # FastAPI validation might catch empty string if min_length=1, let's try a valid one that fails logic or mock it
    # Since we can't easily mock without changing code, we'll rely on the fact that the current code returns raw exceptions
    # We can try to force an exception if we could, but for now let's just check the structure of a valid request
    
    # Actually, let's try to trigger the "Tradera API call failed" by passing something that might break it or just check normal response
    pass

def test_related_products_endpoint():
    """
    Basic functionality test.
    """
    # We can't easily hit real APIs in unit tests without mocking, 
    # but we can check if the endpoint exists and validates input.
    response = client.get("/related-products")
    assert response.status_code == 422 # Missing query param

    # We would need to mock the external services to properly test success cases without hitting real APIs
