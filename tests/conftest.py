"""
Test Configuration and Fixtures
================================

Shared fixtures and configuration for all tests.
"""

import pytest
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


@pytest.fixture
def sample_config():
    """Standard test configuration."""
    return {
        'pv_capacity_mw': 10.0,
        'bess_power_mw': 4.0,
        'bess_capacity_mwh': 16.0,
        'cost_per_wp': 0.8,
        'bess_cost_eur_kwh': 300.0,
        'project_lifetime_years': 25,
        'discount_rate': 0.08
    }


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment before each test."""
    # Clear any environment variables that might affect tests
    yield
    # Cleanup after test if needed
