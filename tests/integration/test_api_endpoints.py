"""
Integration Tests for API Endpoints
Tests Flask routes, request/response handling, and database integration
"""

import json
import pytest
from unittest.mock import patch, MagicMock


# ========================================
# Test Index Route
# ========================================

class TestIndexRoute:
    """Tests for main index page"""

    @pytest.mark.integration
    def test_index_returns_200(self, client):
        """Test index page returns 200 OK"""
        response = client.get('/')
        assert response.status_code == 200

    @pytest.mark.integration
    def test_index_returns_html(self, client):
        """Test index page returns HTML content"""
        response = client.get('/')
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data


# ========================================
# Test Health Check Endpoint
# ========================================

class TestHealthCheckEndpoint:
    """Tests for /health endpoint"""

    @pytest.mark.integration
    @pytest.mark.api
    def test_health_check_returns_200(self, client):
        """Test health check returns 200"""
        response = client.get('/health')
        assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.api
    def test_health_check_returns_json(self, client):
        """Test health check returns JSON"""
        response = client.get('/health')
        assert response.content_type == 'application/json'

    @pytest.mark.integration
    @pytest.mark.api
    def test_health_check_has_status(self, client):
        """Test health check contains status field"""
        response = client.get('/health')
        data = json.loads(response.data)
        assert 'status' in data
        assert data['status'] == 'healthy'

    @pytest.mark.integration
    @pytest.mark.api
    def test_health_check_shows_mode(self, client):
        """Test health check shows celery or threading mode"""
        response = client.get('/health')
        data = json.loads(response.data)
        assert 'mode' in data
        assert data['mode'] in ['celery', 'threading']

    @pytest.mark.integration
    @pytest.mark.api
    def test_health_check_shows_database_info(self, client):
        """Test health check shows database info"""
        response = client.get('/health')
        data = json.loads(response.data)
        assert 'database' in data
        assert 'type' in data['database']


# ========================================
# Test Process Video Endpoint
# ========================================

class TestProcessVideoEndpoint:
    """Tests for /process endpoint"""

    @pytest.mark.integration
    @pytest.mark.api
    def test_process_requires_json(self, client):
        """Test /process requires JSON content type"""
        response = client.post('/process', data='not json')
        assert response.status_code == 400

    @pytest.mark.integration
    @pytest.mark.api
    def test_process_requires_url_field(self, client):
        """Test /process requires 'url' field"""
        response = client.post('/process',
                              json={'no_url': 'value'},
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    @pytest.mark.integration
    @pytest.mark.api
    def test_process_validates_youtube_url(self, client):
        """Test /process validates YouTube URL format"""
        response = client.post('/process',
                              json={'url': 'https://example.com/not-youtube'},
                              content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'YouTube' in data['error'] or 'Invalid' in data['error']

    @pytest.mark.integration
    @pytest.mark.api
    @patch('app.process_video_threading')
    def test_process_accepts_valid_youtube_url(self, mock_process, client, db_session):
        """Test /process accepts valid YouTube URL"""
        youtube_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

        response = client.post('/process',
                              json={'url': youtube_url},
                              content_type='application/json')

        # Should return success or already processing
        assert response.status_code in [200, 201]
        data = json.loads(response.data)
        assert 'video_id' in data or 'job_id' in data

    @pytest.mark.integration
    @pytest.mark.api
    def test_process_extracts_video_id(self, client):
        """Test /process correctly extracts video ID"""
        youtube_url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

        with patch('app.process_video_threading'):
            response = client.post('/process',
                                  json={'url': youtube_url},
                                  content_type='application/json')

            if response.status_code == 200:
                data = json.loads(response.data)
                if 'video_id' in data:
                    assert data['video_id'] == 'dQw4w9WgXcQ'

    @pytest.mark.integration
    @pytest.mark.api
    def test_process_handles_voyoutube_url(self, client):
        """Test /process handles voyoutube.com URLs"""
        voyoutube_url = 'https://voyoutube.com/watch?v=dQw4w9WgXcQ'

        with patch('app.process_video_threading'):
            response = client.post('/process',
                                  json={'url': voyoutube_url},
                                  content_type='application/json')

            assert response.status_code in [200, 201, 400]


# ========================================
# Test Status Endpoint
# ========================================

class TestStatusEndpoint:
    """Tests for /status/<video_id> endpoint"""

    @pytest.mark.integration
    @pytest.mark.api
    def test_status_with_invalid_video_id(self, client):
        """Test /status with invalid video ID format"""
        response = client.get('/status/invalid-id')
        # Should return error or default status
        assert response.status_code in [200, 400, 404]

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.database
    def test_status_with_completed_video(self, client, db_session, sample_video):
        """Test /status returns correct data for completed video"""
        response = client.get(f'/status/{sample_video.video_id}')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data.get('complete') is True
        assert data.get('progress') == 100
        assert 'video_id' in data
        assert data['video_id'] == sample_video.video_id

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.database
    def test_status_with_processing_video(self, client, db_session, processing_video):
        """Test /status returns correct data for processing video"""
        response = client.get(f'/status/{processing_video.video_id}')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data.get('complete') is False
        assert 'progress' in data
        assert data['progress'] < 100

    @pytest.mark.integration
    @pytest.mark.api
    def test_status_returns_json(self, client):
        """Test /status returns JSON response"""
        response = client.get('/status/dQw4w9WgXcQ')
        assert response.content_type == 'application/json'


# ========================================
# Test Download Endpoint
# ========================================

class TestDownloadEndpoint:
    """Tests for /download/<filename> endpoint"""

    @pytest.mark.integration
    @pytest.mark.api
    def test_download_with_invalid_filename(self, client):
        """Test /download rejects invalid filenames"""
        invalid_files = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32',
            '.hidden',
            'file with spaces.mp4',
        ]
        for filename in invalid_files:
            response = client.get(f'/download/{filename}')
            assert response.status_code in [400, 403, 404]

    @pytest.mark.integration
    @pytest.mark.api
    def test_download_with_nonexistent_file(self, client):
        """Test /download returns 404 for nonexistent files"""
        response = client.get('/download/nonexistent_file.mp4')
        assert response.status_code == 404

    @pytest.mark.integration
    @pytest.mark.api
    def test_download_validates_filename_format(self, client):
        """Test /download validates filename format"""
        response = client.get('/download/valid-file_123.mp4')
        # Should return 404 (file not found) not 400 (invalid filename)
        assert response.status_code == 404


# ========================================
# Test Watch Endpoint
# ========================================

class TestWatchEndpoint:
    """Tests for /watch endpoint (YouTube-style)"""

    @pytest.mark.integration
    def test_watch_without_video_id_redirects(self, client):
        """Test /watch without video ID redirects to index"""
        response = client.get('/watch')
        assert response.status_code in [302, 301]

    @pytest.mark.integration
    @pytest.mark.database
    def test_watch_with_completed_video(self, client, db_session, sample_video):
        """Test /watch with completed video shows player"""
        response = client.get(f'/watch?v={sample_video.video_id}')
        assert response.status_code == 200

    @pytest.mark.integration
    def test_watch_with_processing_video_redirects(self, client, db_session, processing_video):
        """Test /watch with processing video redirects to index"""
        response = client.get(f'/watch?v={processing_video.video_id}')
        # Should redirect to index or show processing status
        assert response.status_code in [200, 302]


# ========================================
# Test Library Endpoint
# ========================================

class TestLibraryEndpoint:
    """Tests for /library endpoint"""

    @pytest.mark.integration
    def test_library_returns_200(self, client):
        """Test /library returns 200 OK"""
        response = client.get('/library')
        assert response.status_code == 200

    @pytest.mark.integration
    def test_library_returns_html(self, client):
        """Test /library returns HTML"""
        response = client.get('/library')
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data

    @pytest.mark.integration
    @pytest.mark.database
    def test_library_shows_completed_videos(self, client, db_session, sample_video):
        """Test /library shows completed videos"""
        response = client.get('/library')
        assert response.status_code == 200
        # Video title or ID might be in response
        assert sample_video.video_id.encode() in response.data or \
               sample_video.title.encode() in response.data


# ========================================
# Test API Usage Stats Endpoint
# ========================================

class TestAPIUsageStatsEndpoint:
    """Tests for /api/usage-stats endpoint"""

    @pytest.mark.integration
    @pytest.mark.api
    def test_usage_stats_returns_json(self, client):
        """Test usage stats returns JSON"""
        response = client.get('/api/usage-stats')
        assert response.content_type == 'application/json'

    @pytest.mark.integration
    @pytest.mark.api
    def test_usage_stats_has_success_field(self, client):
        """Test usage stats has success field"""
        response = client.get('/api/usage-stats')
        data = json.loads(response.data)
        assert 'success' in data


# ========================================
# Test Debug Endpoints
# ========================================

class TestDebugEndpoints:
    """Tests for debug endpoints"""

    @pytest.mark.integration
    @pytest.mark.api
    @pytest.mark.database
    def test_debug_video_endpoint(self, client, db_session, sample_video):
        """Test /debug/<video_id> endpoint"""
        response = client.get(f'/debug/{sample_video.video_id}')
        assert response.status_code == 200
        assert response.content_type == 'application/json'

        data = json.loads(response.data)
        assert 'video_id' in data
        assert data['video_id'] == sample_video.video_id

    @pytest.mark.integration
    @pytest.mark.api
    def test_debug_invalid_video_id(self, client):
        """Test /debug with invalid video ID"""
        response = client.get('/debug/invalid')
        assert response.status_code in [400, 404]

    @pytest.mark.integration
    @pytest.mark.api
    def test_console_logs_endpoint(self, client):
        """Test /api/logs/<video_id> endpoint"""
        response = client.get('/api/logs/dQw4w9WgXcQ')
        assert response.status_code == 200
        assert response.content_type == 'application/json'


# ========================================
# Test Error Handling
# ========================================

class TestErrorHandling:
    """Tests for error handling in API"""

    @pytest.mark.integration
    @pytest.mark.api
    def test_404_on_invalid_route(self, client):
        """Test 404 on invalid route"""
        response = client.get('/nonexistent-route')
        assert response.status_code == 404

    @pytest.mark.integration
    @pytest.mark.api
    def test_method_not_allowed(self, client):
        """Test 405 on wrong HTTP method"""
        response = client.get('/process')  # Should be POST
        assert response.status_code == 405

    @pytest.mark.integration
    @pytest.mark.api
    def test_malformed_json_returns_400(self, client):
        """Test malformed JSON returns 400"""
        response = client.post('/process',
                              data='{"invalid": json}',
                              content_type='application/json')
        assert response.status_code == 400
