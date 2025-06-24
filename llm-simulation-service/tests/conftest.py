"""
Pytest configuration and fixtures
"""
import pytest
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.config import Config

@pytest.fixture
def sample_variables():
    """Sample variables for testing prompt formatting"""
    return {
        'name': 'Test Company LLC',
        'locations': 'Moscow, Saint Petersburg',
        'delivery_days': 'Monday, Wednesday, Friday', 
        'current_date': '2024-12-24',
        'purchase_history': 'Previously ordered chicken, beef'
    }

@pytest.fixture
def incomplete_variables():
    """Incomplete variables to test error handling"""
    return {
        'name': 'Test Company LLC',
        # Missing: locations, delivery_days, current_date, purchase_history
    }

@pytest.fixture
def skip_if_no_api_key():
    """Skip test if OpenAI API key is not available"""
    if not Config.OPENAI_API_KEY:
        pytest.skip("OpenAI API key not available")
    return Config.OPENAI_API_KEY