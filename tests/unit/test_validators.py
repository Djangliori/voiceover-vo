"""
Unit Tests for validators.py
Tests URL validation, video ID extraction, and input sanitization
"""

import pytest
from src.validators import (
    validate_youtube_url,
    extract_video_id,
    validate_video_id,
    sanitize_filename,
    ValidationError,
    MAX_URL_LENGTH
)


# ========================================
# Test validate_youtube_url()
# ========================================

class TestValidateYouTubeURL:
    """Tests for YouTube URL validation and ID extraction"""

    @pytest.mark.unit
    def test_standard_youtube_url(self, youtube_urls):
        """Test standard youtube.com/watch?v= URL"""
        video_id = validate_youtube_url(youtube_urls['standard'])
        assert video_id == 'dQw4w9WgXcQ'
        assert len(video_id) == 11

    @pytest.mark.unit
    def test_short_youtube_url(self, youtube_urls):
        """Test youtu.be short URL"""
        video_id = validate_youtube_url(youtube_urls['short'])
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_embed_youtube_url(self, youtube_urls):
        """Test youtube.com/embed/ URL"""
        video_id = validate_youtube_url(youtube_urls['embed'])
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_shorts_youtube_url(self, youtube_urls):
        """Test youtube.com/shorts/ URL"""
        video_id = validate_youtube_url(youtube_urls['shorts'])
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_geyoutube_url(self, youtube_urls):
        """Test geyoutube.com URL (custom domain)"""
        video_id = validate_youtube_url(youtube_urls['geyoutube'])
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_geyoutube_shorts_url(self, youtube_urls):
        """Test geyoutube.com/shorts/ URL"""
        video_id = validate_youtube_url(youtube_urls['geyoutube_shorts'])
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_url_with_extra_params(self):
        """Test URL with additional query parameters"""
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PLtest'
        video_id = validate_youtube_url(url)
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_url_with_whitespace(self):
        """Test URL with leading/trailing whitespace"""
        url = '  https://www.youtube.com/watch?v=dQw4w9WgXcQ  '
        video_id = validate_youtube_url(url)
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_url_without_https(self):
        """Test URL without https:// prefix"""
        url = 'youtube.com/watch?v=dQw4w9WgXcQ'
        video_id = validate_youtube_url(url)
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_url_with_www(self):
        """Test URL with www prefix"""
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        video_id = validate_youtube_url(url)
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_invalid_url_raises_error(self, youtube_urls):
        """Test that invalid URL raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            validate_youtube_url(youtube_urls['invalid'])
        assert 'Invalid YouTube URL' in str(exc_info.value)
        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_malformed_url_raises_error(self, youtube_urls):
        """Test that malformed URL raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            validate_youtube_url(youtube_urls['malformed'])
        assert 'Invalid YouTube URL' in str(exc_info.value)

    @pytest.mark.unit
    def test_empty_string_raises_error(self):
        """Test that empty string raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            validate_youtube_url('')
        assert 'must be a non-empty string' in str(exc_info.value)

    @pytest.mark.unit
    def test_none_raises_error(self):
        """Test that None raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            validate_youtube_url(None)
        assert 'must be a non-empty string' in str(exc_info.value)

    @pytest.mark.unit
    def test_non_string_raises_error(self):
        """Test that non-string input raises ValidationError"""
        with pytest.raises(ValidationError):
            validate_youtube_url(12345)

    @pytest.mark.unit
    def test_url_too_long_raises_error(self):
        """Test that extremely long URL raises ValidationError"""
        long_url = 'https://youtube.com/watch?v=dQw4w9WgXcQ&' + 'x' * MAX_URL_LENGTH
        with pytest.raises(ValidationError) as exc_info:
            validate_youtube_url(long_url)
        assert 'exceeds maximum length' in str(exc_info.value)

    @pytest.mark.unit
    def test_invalid_video_id_format(self):
        """Test URL with invalid video ID format (not 11 chars)"""
        with pytest.raises(ValidationError):
            validate_youtube_url('https://youtube.com/watch?v=invalid')


# ========================================
# Test extract_video_id()
# ========================================

class TestExtractVideoID:
    """Tests for video ID extraction from various formats"""

    @pytest.mark.unit
    def test_extract_from_standard_url(self):
        """Extract from standard YouTube URL"""
        video_id = extract_video_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_extract_from_short_url(self):
        """Extract from youtu.be URL"""
        video_id = extract_video_id('https://youtu.be/dQw4w9WgXcQ')
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_extract_from_bare_id(self):
        """Test that bare video ID is returned as-is"""
        video_id = extract_video_id('dQw4w9WgXcQ')
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_extract_returns_none_for_invalid(self):
        """Test that invalid input returns None"""
        assert extract_video_id('https://example.com/invalid') is None
        assert extract_video_id('not-a-url') is None
        assert extract_video_id('') is None
        assert extract_video_id(None) is None

    @pytest.mark.unit
    def test_extract_with_whitespace(self):
        """Test extraction with whitespace"""
        video_id = extract_video_id('  dQw4w9WgXcQ  ')
        assert video_id == 'dQw4w9WgXcQ'


# ========================================
# Test validate_video_id()
# ========================================

class TestValidateVideoID:
    """Tests for video ID format validation"""

    @pytest.mark.unit
    def test_valid_video_id(self):
        """Test valid 11-character video ID"""
        video_id = validate_video_id('dQw4w9WgXcQ')
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_video_id_with_numbers(self):
        """Test video ID with numbers"""
        video_id = validate_video_id('abc12345678')
        assert video_id == 'abc12345678'

    @pytest.mark.unit
    def test_video_id_with_underscore(self):
        """Test video ID with underscore"""
        video_id = validate_video_id('abc_1234567')
        assert video_id == 'abc_1234567'

    @pytest.mark.unit
    def test_video_id_with_hyphen(self):
        """Test video ID with hyphen"""
        video_id = validate_video_id('abc-1234567')
        assert video_id == 'abc-1234567'

    @pytest.mark.unit
    def test_video_id_with_whitespace(self):
        """Test video ID with whitespace (should be stripped)"""
        video_id = validate_video_id('  dQw4w9WgXcQ  ')
        assert video_id == 'dQw4w9WgXcQ'

    @pytest.mark.unit
    def test_empty_string_raises_error(self):
        """Test empty string raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            validate_video_id('')
        assert 'must be a non-empty string' in str(exc_info.value)

    @pytest.mark.unit
    def test_none_raises_error(self):
        """Test None raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            validate_video_id(None)
        assert 'must be a non-empty string' in str(exc_info.value)

    @pytest.mark.unit
    def test_too_short_raises_error(self):
        """Test video ID too short raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            validate_video_id('short')
        assert 'Invalid video ID format' in str(exc_info.value)

    @pytest.mark.unit
    def test_too_long_raises_error(self):
        """Test video ID too long raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            validate_video_id('toolongvideoid123')
        assert 'Invalid video ID format' in str(exc_info.value)

    @pytest.mark.unit
    def test_invalid_characters_raises_error(self):
        """Test video ID with invalid characters raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            validate_video_id('invalid$%^&')
        assert 'Invalid video ID format' in str(exc_info.value)

    @pytest.mark.unit
    def test_spaces_raises_error(self):
        """Test video ID with spaces raises ValidationError"""
        with pytest.raises(ValidationError):
            validate_video_id('has spaces!')


# ========================================
# Test sanitize_filename()
# ========================================

class TestSanitizeFilename:
    """Tests for filename sanitization"""

    @pytest.mark.unit
    def test_valid_filename(self):
        """Test valid filename passes through"""
        filename = sanitize_filename('video_123-test.mp4')
        assert filename == 'video_123-test.mp4'

    @pytest.mark.unit
    def test_filename_with_dots(self):
        """Test filename with multiple dots"""
        filename = sanitize_filename('video.test.mp4')
        assert filename == 'video.test.mp4'

    @pytest.mark.unit
    def test_removes_directory_path(self):
        """Test that directory paths are removed"""
        filename = sanitize_filename('/path/to/file.mp4')
        assert filename == 'file.mp4'

        filename = sanitize_filename('path/to/file.mp4')
        assert filename == 'file.mp4'

    @pytest.mark.unit
    def test_removes_windows_path(self):
        """Test that Windows paths are removed"""
        filename = sanitize_filename('C:\\Users\\test\\file.mp4')
        assert filename == 'file.mp4'

    @pytest.mark.unit
    def test_path_traversal_raises_error(self):
        """Test that path traversal attempts raise error"""
        with pytest.raises(ValidationError) as exc_info:
            sanitize_filename('../../../etc/passwd')
        assert 'path traversal not allowed' in str(exc_info.value)

    @pytest.mark.unit
    def test_hidden_file_raises_error(self):
        """Test that hidden files (starting with dot) raise error"""
        with pytest.raises(ValidationError) as exc_info:
            sanitize_filename('.hidden')
        assert 'path traversal not allowed' in str(exc_info.value)

    @pytest.mark.unit
    def test_invalid_characters_raise_error(self):
        """Test that invalid characters raise error"""
        invalid_filenames = [
            'file name with spaces.mp4',
            'file@name.mp4',
            'file$name.mp4',
            'file%name.mp4',
            'file&name.mp4',
        ]
        for filename in invalid_filenames:
            with pytest.raises(ValidationError) as exc_info:
                sanitize_filename(filename)
            assert 'only alphanumeric characters' in str(exc_info.value)

    @pytest.mark.unit
    def test_empty_string_raises_error(self):
        """Test empty string raises error"""
        with pytest.raises(ValidationError) as exc_info:
            sanitize_filename('')
        assert 'must be a non-empty string' in str(exc_info.value)

    @pytest.mark.unit
    def test_none_raises_error(self):
        """Test None raises error"""
        with pytest.raises(ValidationError) as exc_info:
            sanitize_filename(None)
        assert 'must be a non-empty string' in str(exc_info.value)

    @pytest.mark.unit
    def test_too_long_filename_raises_error(self):
        """Test filename exceeding 255 chars raises error"""
        long_filename = 'a' * 256 + '.mp4'
        with pytest.raises(ValidationError) as exc_info:
            sanitize_filename(long_filename)
        assert 'exceeds maximum length' in str(exc_info.value)

    @pytest.mark.unit
    def test_valid_extensions(self):
        """Test various valid file extensions"""
        valid_files = [
            'video.mp4',
            'video.avi',
            'video.mov',
            'video.mkv',
            'audio.mp3',
            'audio.wav',
            'subtitle.srt',
        ]
        for filename in valid_files:
            result = sanitize_filename(filename)
            assert result == filename


# ========================================
# Test ValidationError Exception
# ========================================

class TestValidationError:
    """Tests for ValidationError custom exception"""

    @pytest.mark.unit
    def test_default_status_code(self):
        """Test default status code is 400"""
        error = ValidationError('Test error')
        assert error.status_code == 400
        assert error.message == 'Test error'

    @pytest.mark.unit
    def test_custom_status_code(self):
        """Test custom status code"""
        error = ValidationError('Forbidden', status_code=403)
        assert error.status_code == 403
        assert error.message == 'Forbidden'

    @pytest.mark.unit
    def test_exception_inherits_from_exception(self):
        """Test ValidationError inherits from Exception"""
        assert issubclass(ValidationError, Exception)

    @pytest.mark.unit
    def test_can_be_raised_and_caught(self):
        """Test ValidationError can be raised and caught"""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError('Test error', status_code=422)
        assert exc_info.value.message == 'Test error'
        assert exc_info.value.status_code == 422
