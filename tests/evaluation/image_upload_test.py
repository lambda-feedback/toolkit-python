import pytest
import uuid
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import requests

# Import the module to test
from lf_toolkit.evaluation.image_upload import (
    generate_file_name,
    validate_mime_type,
    get_s3_bucket_uri,
    upload_image,
    ImageUploadError,
    InvalidMimeTypeError,
    MissingEnvironmentVariableError,
    MIME_TO_FORMAT,
    FORMAT_TO_EXTENSION
)


class TestGenerateFileName:
    """Test suite for generate_file_name function"""

    def test_generate_file_name_with_jpeg_format(self):
        """Test filename generation for JPEG image"""
        img = Mock(spec=Image.Image)
        img.format = 'JPEG'

        with patch('lf_toolkit.evaluation.image_upload.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
            filename = generate_file_name(img)

        assert filename == '12345678-1234-5678-1234-567812345678.jpeg'

    def test_generate_file_name_with_png_format(self):
        """Test filename generation for PNG image"""
        img = Mock(spec=Image.Image)
        img.format = 'PNG'

        with patch('lf_toolkit.evaluation.image_upload.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = uuid.UUID('abcdef12-3456-7890-abcd-ef1234567890')
            filename = generate_file_name(img)

        assert filename == 'abcdef12-3456-7890-abcd-ef1234567890.png'

    def test_generate_file_name_with_no_format(self):
        """Test filename generation when image has no format (defaults to png)"""
        img = Mock(spec=Image.Image)
        img.format = None

        with patch('lf_toolkit.evaluation.image_upload.uuid.uuid4') as mock_uuid:
            mock_uuid.return_value = uuid.UUID('00000000-0000-0000-0000-000000000000')
            filename = generate_file_name(img)

        assert filename == '00000000-0000-0000-0000-000000000000.png'

    def test_generate_file_name_unique(self):
        """Test that generated filenames are unique"""
        img = Mock(spec=Image.Image)
        img.format = 'PNG'

        filename1 = generate_file_name(img)
        filename2 = generate_file_name(img)

        assert filename1 != filename2


class TestValidateMimeType:
    """Test suite for validate_mime_type function"""

    def test_valid_jpeg_mime_type(self):
        """Test validation with valid JPEG MIME type"""
        img = Mock(spec=Image.Image)
        img.format = 'JPEG'

        result = validate_mime_type('image/jpeg', img, 'test.jpg')
        assert result is True

    def test_valid_png_mime_type(self):
        """Test validation with valid PNG MIME type"""
        img = Mock(spec=Image.Image)
        img.format = 'PNG'

        result = validate_mime_type('image/png', img, 'test.png')
        assert result is True

    def test_invalid_mime_type(self):
        """Test validation with unsupported MIME type"""
        img = Mock(spec=Image.Image)
        img.format = 'PNG'

        with pytest.raises(InvalidMimeTypeError) as exc_info:
            validate_mime_type('image/invalid', img, 'test.png')

        assert "Invalid MIME type 'image/invalid'" in str(exc_info.value)

    def test_mime_type_format_mismatch(self):
        """Test validation when MIME type doesn't match image format"""
        img = Mock(spec=Image.Image)
        img.format = 'PNG'

        with pytest.raises(InvalidMimeTypeError) as exc_info:
            validate_mime_type('image/jpeg', img, 'test.png')

        assert "does not match image format 'PNG'" in str(exc_info.value)

    def test_extension_format_mismatch(self):
        """Test validation when file extension doesn't match format"""
        img = Mock(spec=Image.Image)
        img.format = 'JPEG'

        with pytest.raises(InvalidMimeTypeError) as exc_info:
            validate_mime_type('image/jpeg', img, 'test.png')

        assert "File extension '.png' does not match format 'JPEG'" in str(exc_info.value)

    def test_valid_with_no_image_format(self):
        """Test validation when image has no format attribute"""
        img = Mock(spec=Image.Image)
        img.format = None

        # Should not raise when format is None
        result = validate_mime_type('image/png', img, 'test.png')
        assert result is True

    def test_valid_webp_mime_type(self):
        """Test validation with valid WEBP MIME type"""
        img = Mock(spec=Image.Image)
        img.format = 'WEBP'

        result = validate_mime_type('image/webp', img, 'test.webp')
        assert result is True

    def test_jpeg_with_jpg_extension(self):
        """Test JPEG image with .jpg extension"""
        img = Mock(spec=Image.Image)
        img.format = 'JPEG'

        result = validate_mime_type('image/jpeg', img, 'photo.jpg')
        assert result is True

    def test_jpeg_with_jpeg_extension(self):
        """Test JPEG image with .jpeg extension"""
        img = Mock(spec=Image.Image)
        img.format = 'JPEG'

        result = validate_mime_type('image/jpeg', img, 'photo.jpeg')
        assert result is True


class TestGetS3BucketUri:
    """Test suite for get_s3_bucket_uri function"""

    def test_get_s3_bucket_uri_success(self):
        """Test successful retrieval of S3 bucket URI"""
        with patch('lf_toolkit.evaluation.image_upload.os.getenv') as mock_getenv:
            mock_getenv.return_value = 'https://s3.amazonaws.com/my-bucket'

            uri = get_s3_bucket_uri()

            assert uri == 'https://s3.amazonaws.com/my-bucket'
            mock_getenv.assert_called_once_with('S3_BUCKET_URI')

    def test_get_s3_bucket_uri_missing(self):
        """Test error when S3_BUCKET_URI is not set"""
        with patch('lf_toolkit.evaluation.image_upload.os.getenv') as mock_getenv:
            mock_getenv.return_value = None

            with pytest.raises(MissingEnvironmentVariableError) as exc_info:
                get_s3_bucket_uri()

            assert "S3_BUCKET_URI environment variable is not set" in str(exc_info.value)

    def test_get_s3_bucket_uri_empty_string(self):
        """Test error when S3_BUCKET_URI is empty string"""
        with patch('lf_toolkit.evaluation.image_upload.os.getenv') as mock_getenv:
            mock_getenv.return_value = ''

            with pytest.raises(MissingEnvironmentVariableError):
                get_s3_bucket_uri()


class TestUploadImage:
    """Test suite for upload_image function"""

    @patch('lf_toolkit.evaluation.image_upload.requests.put')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_successful_upload(self, mock_uuid, mock_getenv, mock_put):
        """Test successful image upload with UUID-based filename"""
        # Setup mocks
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.return_value = 'https://s3.amazonaws.com/my-bucket'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'url': f'https://s3.amazonaws.com/uploaded-image.jpg'}
        mock_put.return_value = mock_response

        # Create a real PIL image for testing
        img = Image.new('RGB', (100, 100), color='red')
        img.format = 'JPEG'

        # Execute
        result = upload_image(img, 'image/jpeg')

        # Verify response
        assert result == 'https://s3.amazonaws.com/uploaded-image.jpg'
        assert mock_put.called
        assert mock_put.call_args[1]['timeout'] == 30

        # Verify UUID-based filename is used
        call_args = mock_put.call_args
        filename, file_obj, mime_type = call_args[1]['files']['file']
        assert filename == '12345678-1234-5678-1234-567812345678.jpeg'
        assert mime_type == 'image/jpeg'

    @patch('lf_toolkit.evaluation.image_upload.requests.put')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_upload_with_png_image(self, mock_uuid, mock_getenv, mock_put):
        """Test uploading PNG image with UUID-based filename"""
        mock_uuid.return_value = uuid.UUID('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee')
        mock_getenv.return_value = 'https://storage.example.com'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'url': 'https://storage.example.com/image.png'}
        mock_put.return_value = mock_response

        img = Image.new('RGBA', (50, 50), color=(0, 255, 0, 128))
        img.format = 'PNG'

        result = upload_image(img, 'image/png')

        assert result == 'https://storage.example.com/image.png'

        # Verify UUID-based filename is used
        call_args = mock_put.call_args
        filename, file_obj, mime_type = call_args[1]['files']['file']
        assert filename == 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.png'
        assert mime_type == 'image/png'

    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    def test_upload_missing_s3_uri(self, mock_getenv):
        """Test upload fails when S3_BUCKET_URI is missing"""
        mock_getenv.return_value = None

        img = Image.new('RGB', (100, 100))
        img.format = 'JPEG'

        with pytest.raises(MissingEnvironmentVariableError):
            upload_image(img, 'image/jpeg')

    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    def test_upload_invalid_mime_type(self, mock_getenv):
        """Test upload fails with invalid MIME type"""
        mock_getenv.return_value = 'https://s3.amazonaws.com/bucket'

        img = Image.new('RGB', (100, 100))
        img.format = 'JPEG'

        with pytest.raises(InvalidMimeTypeError):
            upload_image(img, 'image/invalid')

    @patch('lf_toolkit.evaluation.image_upload.requests.put')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_upload_server_error(self, mock_uuid, mock_getenv, mock_put):
        """Test upload fails when server returns error"""
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.return_value = 'https://s3.amazonaws.com/bucket'

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_put.return_value = mock_response

        img = Image.new('RGB', (100, 100))
        img.format = 'JPEG'

        with pytest.raises(ImageUploadError) as exc_info:
            upload_image(img, 'image/jpeg')

        assert "Upload failed with status code 500" in str(exc_info.value)

    @patch('lf_toolkit.evaluation.image_upload.requests.put')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_upload_network_error(self, mock_uuid, mock_getenv, mock_put):
        """Test upload fails on network error"""
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.return_value = 'https://s3.amazonaws.com/bucket'

        mock_put.side_effect = requests.exceptions.ConnectionError('Connection failed')

        img = Image.new('RGB', (100, 100))
        img.format = 'JPEG'

        with pytest.raises(ImageUploadError) as exc_info:
            upload_image(img, 'image/jpeg')

        assert "Network error" in str(exc_info.value)

    @patch('lf_toolkit.evaluation.image_upload.requests.put')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_upload_timeout_error(self, mock_uuid, mock_getenv, mock_put):
        """Test upload fails on timeout"""
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.return_value = 'https://s3.amazonaws.com/bucket'

        mock_put.side_effect = requests.exceptions.Timeout('Request timed out')

        img = Image.new('RGB', (100, 100))
        img.format = 'JPEG'

        with pytest.raises(ImageUploadError) as exc_info:
            upload_image(img, 'image/jpeg')

        assert "Network error" in str(exc_info.value)

    @patch('lf_toolkit.evaluation.image_upload.requests.put')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_upload_mime_type_mismatch(self, mock_uuid, mock_getenv, mock_put):
        """Test upload fails when MIME type doesn't match image format"""
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.return_value = 'https://s3.amazonaws.com/bucket'

        img = Image.new('RGB', (100, 100))
        img.format = 'PNG'

        with pytest.raises(InvalidMimeTypeError):
            upload_image(img, 'image/jpeg')

    @patch('lf_toolkit.evaluation.image_upload.requests.put')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_upload_image_no_format(self, mock_uuid, mock_getenv, mock_put):
        """Test upload with image that has no format (defaults to PNG) uses UUID filename"""
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.return_value = 'https://s3.amazonaws.com/bucket'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'url': 'https://s3.amazonaws.com/image.png'}
        mock_put.return_value = mock_response

        img = Image.new('RGB', (100, 100))
        img.format = None

        result = upload_image(img, 'image/png')

        assert result == 'https://s3.amazonaws.com/image.png'

        # Verify UUID-based filename with default .png extension
        call_args = mock_put.call_args
        filename, file_obj, mime_type = call_args[1]['files']['file']
        assert filename == '12345678-1234-5678-1234-567812345678.png'
        assert mime_type == 'image/png'

    @patch('lf_toolkit.evaluation.image_upload.requests.put')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_upload_uses_different_uuid_each_time(self, mock_uuid, mock_getenv, mock_put):
        """Test that each upload generates a unique UUID-based filename"""
        mock_getenv.return_value = 'https://s3.amazonaws.com/bucket'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'url': 'https://s3.amazonaws.com/uploaded.jpg'}
        mock_put.return_value = mock_response

        # First upload with first UUID
        uuid1 = uuid.UUID('11111111-1111-1111-1111-111111111111')
        mock_uuid.return_value = uuid1

        img1 = Image.new('RGB', (100, 100))
        img1.format = 'JPEG'
        upload_image(img1, 'image/jpeg')

        filename1 = mock_put.call_args[1]['files']['file'][0]

        # Second upload with different UUID
        uuid2 = uuid.UUID('22222222-2222-2222-2222-222222222222')
        mock_uuid.return_value = uuid2

        img2 = Image.new('RGB', (100, 100))
        img2.format = 'JPEG'
        upload_image(img2, 'image/jpeg')

        filename2 = mock_put.call_args[1]['files']['file'][0]

        # Verify different UUIDs result in different filenames
        assert filename1 == '11111111-1111-1111-1111-111111111111.jpeg'
        assert filename2 == '22222222-2222-2222-2222-222222222222.jpeg'
        assert filename1 != filename2

    @patch('lf_toolkit.evaluation.image_upload.requests.put')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_upload_verifies_correct_file_uploaded(self, mock_uuid, mock_getenv, mock_put):
        """Test that the correct file data is sent in upload request"""
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.return_value = 'https://s3.amazonaws.com/bucket'

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'url': 'https://s3.amazonaws.com/image.jpg'}
        mock_put.return_value = mock_response

        img = Image.new('RGB', (100, 100), color='blue')
        img.format = 'JPEG'

        upload_image(img, 'image/jpeg')

        # Verify the put was called with correct arguments
        call_args = mock_put.call_args
        assert call_args[0][0] == 'https://s3.amazonaws.com/bucket'
        assert 'files' in call_args[1]
        assert 'file' in call_args[1]['files']

        filename, file_obj, mime_type = call_args[1]['files']['file']
        assert filename == '12345678-1234-5678-1234-567812345678.jpeg'
        assert mime_type == 'image/jpeg'


class TestExceptionHierarchy:
    """Test suite for custom exception classes"""

    def test_image_upload_error_is_exception(self):
        """Test that ImageUploadError inherits from Exception"""
        assert issubclass(ImageUploadError, Exception)

    def test_invalid_mime_type_error_is_image_upload_error(self):
        """Test that InvalidMimeTypeError inherits from ImageUploadError"""
        assert issubclass(InvalidMimeTypeError, ImageUploadError)
        assert issubclass(InvalidMimeTypeError, Exception)

    def test_missing_environment_variable_error_is_image_upload_error(self):
        """Test that MissingEnvironmentVariableError inherits from ImageUploadError"""
        assert issubclass(MissingEnvironmentVariableError, ImageUploadError)
        assert issubclass(MissingEnvironmentVariableError, Exception)

    def test_can_raise_and_catch_image_upload_error(self):
        """Test that custom exceptions can be raised and caught"""
        with pytest.raises(ImageUploadError):
            raise ImageUploadError("Test error")

    def test_invalid_mime_type_error_caught_as_image_upload_error(self):
        """Test that InvalidMimeTypeError can be caught as ImageUploadError"""
        with pytest.raises(ImageUploadError):
            raise InvalidMimeTypeError("Invalid MIME")


class TestConstants:
    """Test suite for module constants"""

    def test_mime_to_format_has_expected_types(self):
        """Test that MIME_TO_FORMAT contains expected image types"""
        assert 'image/jpeg' in MIME_TO_FORMAT
        assert 'image/png' in MIME_TO_FORMAT
        assert 'image/gif' in MIME_TO_FORMAT
        assert 'image/webp' in MIME_TO_FORMAT

    def test_format_to_extension_has_expected_formats(self):
        """Test that FORMAT_TO_EXTENSION contains expected formats"""
        assert 'JPEG' in FORMAT_TO_EXTENSION
        assert 'PNG' in FORMAT_TO_EXTENSION
        assert 'GIF' in FORMAT_TO_EXTENSION
        assert 'WEBP' in FORMAT_TO_EXTENSION

    def test_jpeg_has_multiple_extensions(self):
        """Test that JPEG format has multiple valid extensions"""
        assert '.jpg' in FORMAT_TO_EXTENSION['JPEG']
        assert '.jpeg' in FORMAT_TO_EXTENSION['JPEG']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
