import pytest
import uuid
from unittest.mock import Mock, patch
from PIL import Image
import requests

# Import the module to test
from lf_toolkit.evaluation.image_upload import (
    generate_file_name,
    get_s3_bucket_uri,
    resolve_upload_backend,
    upload_image,
    ImageUploadError,
    InvalidMimeTypeError,
    MissingEnvironmentVariableError,
)


def fake_getenv(mapping):
    """Build an os.getenv replacement backed by ``mapping`` (respects default)."""
    def _getenv(key, default=None):
        return mapping.get(key, default)
    return _getenv


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


class TestResolveUploadBackend:
    """Test suite for resolve_upload_backend function"""

    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    def test_defaults_to_s3(self, mock_getenv):
        mock_getenv.side_effect = fake_getenv({})
        assert resolve_upload_backend() == 's3'

    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    def test_gcs_bucket_selects_gcs(self, mock_getenv):
        mock_getenv.side_effect = fake_getenv({'GCS_BUCKET': 'my-bucket'})
        assert resolve_upload_backend() == 'gcs'

    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    def test_explicit_backend_wins_over_autodetect(self, mock_getenv):
        mock_getenv.side_effect = fake_getenv({
            'IMAGE_UPLOAD_BACKEND': 'S3',
            'GCS_BUCKET': 'my-bucket',
        })
        assert resolve_upload_backend() == 's3'

    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    def test_unknown_backend_value_falls_back_to_autodetect(self, mock_getenv):
        mock_getenv.side_effect = fake_getenv({
            'IMAGE_UPLOAD_BACKEND': 'azure',
            'S3_BUCKET_URI': 'https://s3.amazonaws.com/bucket',
        })
        assert resolve_upload_backend() == 's3'


class TestUploadImageS3:
    """Test suite for upload_image function (S3 backend)"""

    @patch('lf_toolkit.evaluation.image_upload.requests.request')
    @patch('lf_toolkit.evaluation.image_upload.get_aws_signed_request')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_successful_upload(self, mock_uuid, mock_getenv, mock_get_aws_signed_request, mock_request):
        """Test successful image upload with UUID-based filename"""
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.side_effect = fake_getenv({'S3_BUCKET_URI': 'https://s3.amazonaws.com/eduvision'})

        mock_prepared_request = Mock()
        mock_prepared_request.method = 'PUT'
        mock_prepared_request.url = 'https://s3.amazonaws.com/eduvision/eduvision/12345678-1234-5678-1234-567812345678.jpeg'
        mock_prepared_request.body = b'mock_body'
        mock_prepared_request.headers = {'Content-Type': 'image/jpeg'}

        mock_aws_request = Mock()
        mock_aws_request.prepare.return_value = mock_prepared_request
        mock_get_aws_signed_request.return_value = mock_aws_request

        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        img = Image.new('RGB', (100, 100), color='red')
        img.format = 'JPEG'

        result = upload_image(img, "eduvision")

        assert result == 'https://s3.amazonaws.com/eduvision/eduvision/12345678-1234-5678-1234-567812345678.jpeg'
        assert mock_request.called
        assert mock_request.call_args[1]['timeout'] == 30

    @patch('lf_toolkit.evaluation.image_upload.requests.request')
    @patch('lf_toolkit.evaluation.image_upload.get_aws_signed_request')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_upload_with_png(self, mock_uuid, mock_getenv, mock_get_aws_signed_request, mock_request):
        """Test uploading PNG image with UUID-based filename"""
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.side_effect = fake_getenv({'S3_BUCKET_URI': 'https://s3.amazonaws.com/eduvision'})

        mock_prepared_request = Mock()
        mock_prepared_request.method = 'PUT'
        mock_prepared_request.url = 'https://s3.amazonaws.com/eduvision/eduvision/12345678-1234-5678-1234-567812345678.png'
        mock_prepared_request.body = b'mock_body'
        mock_prepared_request.headers = {'Content-Type': 'image/jpeg'}

        mock_aws_request = Mock()
        mock_aws_request.prepare.return_value = mock_prepared_request
        mock_get_aws_signed_request.return_value = mock_aws_request

        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        img = Image.new('RGBA', (50, 50), color=(0, 255, 0, 128))
        img.format = 'PNG'

        result = upload_image(img, "eduvision")

        assert result == 'https://s3.amazonaws.com/eduvision/eduvision/12345678-1234-5678-1234-567812345678.png'

    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    def test_upload_missing_s3_uri(self, mock_getenv):
        """Test upload fails when S3_BUCKET_URI is missing"""
        mock_getenv.side_effect = fake_getenv({})

        img = Image.new('RGB', (100, 100))
        img.format = 'JPEG'

        with pytest.raises(MissingEnvironmentVariableError):
            upload_image(img, "eduvision")

    @patch('lf_toolkit.evaluation.image_upload.requests.request')
    @patch('lf_toolkit.evaluation.image_upload.get_aws_signed_request')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_upload_server_error(self, mock_uuid, mock_getenv, mock_get_aws_signed_request, mock_request):
        """Test upload fails when server returns error"""
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.side_effect = fake_getenv({'S3_BUCKET_URI': 'https://s3.amazonaws.com/bucket'})

        mock_prepared_request = Mock()
        mock_prepared_request.method = 'PUT'
        mock_prepared_request.url = 'https://s3.amazonaws.com/bucket/eduvision/12345678-1234-5678-1234-567812345678.jpeg'
        mock_prepared_request.body = b'mock_body'
        mock_prepared_request.headers = {'Content-Type': 'image/jpeg'}

        mock_aws_request = Mock()
        mock_aws_request.prepare.return_value = mock_prepared_request
        mock_get_aws_signed_request.return_value = mock_aws_request

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_request.return_value = mock_response

        img = Image.new('RGB', (100, 100))
        img.format = 'JPEG'

        with pytest.raises(ImageUploadError) as exc_info:
            upload_image(img, "eduvision")

        assert "Upload failed with status code 500" in str(exc_info.value)

    @patch('lf_toolkit.evaluation.image_upload.requests.request')
    @patch('lf_toolkit.evaluation.image_upload.get_aws_signed_request')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_upload_network_error(self, mock_uuid, mock_getenv, mock_get_aws_signed_request, mock_request):
        """Test upload fails on network error"""
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.side_effect = fake_getenv({'S3_BUCKET_URI': 'https://s3.amazonaws.com/bucket'})

        mock_prepared_request = Mock()
        mock_prepared_request.method = 'PUT'
        mock_prepared_request.url = 'https://s3.amazonaws.com/bucket/eduvision/12345678-1234-5678-1234-567812345678.jpeg'
        mock_prepared_request.body = b'mock_body'
        mock_prepared_request.headers = {'Content-Type': 'image/jpeg'}

        mock_aws_request = Mock()
        mock_aws_request.prepare.return_value = mock_prepared_request
        mock_get_aws_signed_request.return_value = mock_aws_request

        mock_request.side_effect = requests.exceptions.ConnectionError('Connection failed')

        img = Image.new('RGB', (100, 100))
        img.format = 'JPEG'

        with pytest.raises(ImageUploadError) as exc_info:
            upload_image(img, "eduvision")

        assert "Network error" in str(exc_info.value)

    @patch('lf_toolkit.evaluation.image_upload.requests.request')
    @patch('lf_toolkit.evaluation.image_upload.get_aws_signed_request')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_upload_timeout_error(self, mock_uuid, mock_getenv, mock_get_aws_signed_request, mock_request):
        """Test upload fails on timeout"""
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.side_effect = fake_getenv({'S3_BUCKET_URI': 'https://s3.amazonaws.com/bucket'})

        mock_prepared_request = Mock()
        mock_prepared_request.method = 'PUT'
        mock_prepared_request.url = 'https://s3.amazonaws.com/bucket/eduvision/12345678-1234-5678-1234-567812345678.jpeg'
        mock_prepared_request.body = b'mock_body'
        mock_prepared_request.headers = {'Content-Type': 'image/jpeg'}

        mock_aws_request = Mock()
        mock_aws_request.prepare.return_value = mock_prepared_request
        mock_get_aws_signed_request.return_value = mock_aws_request

        mock_request.side_effect = requests.exceptions.Timeout('Request timed out')

        img = Image.new('RGB', (100, 100))
        img.format = 'JPEG'

        with pytest.raises(ImageUploadError) as exc_info:
            upload_image(img, "eduvision")

        assert "Network error" in str(exc_info.value)

    @patch('lf_toolkit.evaluation.image_upload.requests.request')
    @patch('lf_toolkit.evaluation.image_upload.get_aws_signed_request')
    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_upload_image_no_format(self, mock_uuid, mock_getenv, mock_get_aws_signed_request, mock_request):
        """Test upload with image that has no format (defaults to PNG) uses UUID filename"""
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.side_effect = fake_getenv({'S3_BUCKET_URI': 'https://s3.amazonaws.com/bucket/'})

        mock_prepared_request = Mock()
        mock_prepared_request.method = 'PUT'
        mock_prepared_request.url = 'https://s3.amazonaws.com/bucket/eduvision/12345678-1234-5678-1234-567812345678.png'
        mock_prepared_request.body = b'mock_body'
        mock_prepared_request.headers = {'Content-Type': 'image/png'}

        mock_aws_request = Mock()
        mock_aws_request.prepare.return_value = mock_prepared_request
        mock_get_aws_signed_request.return_value = mock_aws_request

        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        img = Image.new('RGB', (100, 100))
        img.format = None

        result = upload_image(img, "eduvision")

        assert result == 'https://s3.amazonaws.com/bucket/eduvision/12345678-1234-5678-1234-567812345678.png'


class TestUploadImageGCS:
    """Test suite for upload_image function (GCS backend)"""

    def _mock_storage(self):
        mock_blob = Mock()
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = Mock()
        mock_client.bucket.return_value = mock_bucket
        mock_storage = Mock()
        mock_storage.Client.return_value = mock_client
        return mock_storage, mock_client, mock_bucket, mock_blob

    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_successful_gcs_upload(self, mock_uuid, mock_getenv):
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.side_effect = fake_getenv({'GCS_BUCKET': 'plots-bucket'})
        mock_storage, mock_client, mock_bucket, mock_blob = self._mock_storage()

        img = Image.new('RGB', (100, 100), color='blue')
        img.format = 'PNG'

        with patch('lf_toolkit.evaluation.image_upload._gcs_storage', mock_storage):
            result = upload_image(img, "evaluatePython")

        assert result == (
            'https://storage.googleapis.com/plots-bucket/evaluatePython/'
            '12345678-1234-5678-1234-567812345678.png'
        )
        mock_client.bucket.assert_called_once_with('plots-bucket')
        mock_bucket.blob.assert_called_once_with(
            'evaluatePython/12345678-1234-5678-1234-567812345678.png'
        )
        _, kwargs = mock_blob.upload_from_string.call_args
        assert kwargs['content_type'] == 'image/png'

    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_gcs_public_base_url_override(self, mock_uuid, mock_getenv):
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.side_effect = fake_getenv({
            'IMAGE_UPLOAD_BACKEND': 'gcs',
            'GCS_BUCKET': 'plots-bucket',
            'GCS_PUBLIC_BASE_URL': 'https://cdn.example.com/',
        })
        mock_storage, *_ = self._mock_storage()

        img = Image.new('RGB', (10, 10))
        img.format = 'PNG'

        with patch('lf_toolkit.evaluation.image_upload._gcs_storage', mock_storage):
            result = upload_image(img, "evaluatePython")

        assert result == (
            'https://cdn.example.com/plots-bucket/evaluatePython/'
            '12345678-1234-5678-1234-567812345678.png'
        )

    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    def test_gcs_missing_bucket(self, mock_getenv):
        mock_getenv.side_effect = fake_getenv({'IMAGE_UPLOAD_BACKEND': 'gcs'})
        mock_storage, *_ = self._mock_storage()

        img = Image.new('RGB', (10, 10))
        img.format = 'PNG'

        with patch('lf_toolkit.evaluation.image_upload._gcs_storage', mock_storage):
            with pytest.raises(MissingEnvironmentVariableError):
                upload_image(img, "evaluatePython")

    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    def test_gcs_backend_without_dependency(self, mock_getenv):
        mock_getenv.side_effect = fake_getenv({
            'IMAGE_UPLOAD_BACKEND': 'gcs',
            'GCS_BUCKET': 'plots-bucket',
        })

        img = Image.new('RGB', (10, 10))
        img.format = 'PNG'

        with patch('lf_toolkit.evaluation.image_upload._gcs_storage', None):
            with pytest.raises(ImageUploadError) as exc_info:
                upload_image(img, "evaluatePython")

        assert "google-cloud-storage is not installed" in str(exc_info.value)

    @patch('lf_toolkit.evaluation.image_upload.os.getenv')
    @patch('lf_toolkit.evaluation.image_upload.uuid.uuid4')
    def test_gcs_upload_error_wrapped(self, mock_uuid, mock_getenv):
        mock_uuid.return_value = uuid.UUID('12345678-1234-5678-1234-567812345678')
        mock_getenv.side_effect = fake_getenv({'GCS_BUCKET': 'plots-bucket'})
        mock_storage, _, _, mock_blob = self._mock_storage()
        mock_blob.upload_from_string.side_effect = RuntimeError('boom')

        img = Image.new('RGB', (10, 10))
        img.format = 'PNG'

        with patch('lf_toolkit.evaluation.image_upload._gcs_storage', mock_storage):
            with pytest.raises(ImageUploadError) as exc_info:
                upload_image(img, "evaluatePython")

        assert "boom" in str(exc_info.value)


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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
