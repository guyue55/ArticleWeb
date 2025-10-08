"""Pytest configuration and fixtures for OTA system tests."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest
from django.test import TestCase


# Remove the problematic django_db_setup fixture
# pytest-django will handle database setup automatically


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_minio_client():
    """Mock MinIO client for testing."""
    with patch('common.utils.MinIOClient') as mock_client:
        mock_instance = Mock()
        mock_instance.upload_file.return_value = True
        mock_instance.download_file.return_value = True
        mock_instance.delete_file.return_value = True
        mock_instance.list_files.return_value = []
        mock_instance.get_file_url.return_value = 'http://test-url.com/file'
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_docker_client():
    """Mock Docker client for testing."""
    with patch('common.utils.DockerClient') as mock_client:
        mock_instance = Mock()
        mock_instance.pull_image.return_value = True
        mock_instance.push_image.return_value = True
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_version_data():
    """Sample version data for testing."""
    return {
        'name': 'Test Version',
        'version': '1.0.0',
        'device_type': 0,
        'resource': [{'name': 'test.zip', 'size': 1024}],
        'description': 'Test version description',
        'vendor': '|test_vendor|',
        'is_active': True
    }


@pytest.fixture
def sample_history_data():
    """Sample history data for testing."""
    return {
        'version_uuid': 'test-uuid-123',
        'node_no': 'node-001',
        'status': 0,  # PENDING
        'device_type': 0,
        'vendor': 'test_vendor',
        'execution_log': 'Test log entry',
        'error_message': ''
    }


class BaseTestCase(TestCase):
    """Base test case with common utilities."""

    def setUp(self):
        """Set up test case."""
        super().setUp()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test case."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        super().tearDown()

    def create_test_file(self, filename, content='test content'):
        """Create a test file in temp directory."""
        file_path = os.path.join(self.temp_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path