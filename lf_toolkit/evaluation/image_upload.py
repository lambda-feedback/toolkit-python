import hashlib

import requests
import uuid
import os
from io import BytesIO
from typing import Dict, List, Optional
from PIL import Image
from dotenv import load_dotenv

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

try:
    from google.cloud import storage as _gcs_storage
except ImportError:  # pragma: no cover - optional dependency, install the "gcs" extra
    _gcs_storage = None

load_dotenv()

MIME_TO_FORMAT: Dict[str, List[str]] = {
    'image/jpeg': ['JPEG', 'JPG'],
    'image/png': ['PNG'],
    'image/gif': ['GIF'],
    'image/bmp': ['BMP'],
}

FORMAT_TO_MIME: Dict[str, str] = {
    'JPEG': 'image/jpeg',
    'JPG': 'image/jpeg',
    'PNG': 'image/png',
    'GIF': 'image/gif',
    "BMP": 'image/bmp'
}

class ImageUploadError(Exception):
    """Custom exception for image upload failures"""
    pass


class InvalidMimeTypeError(ImageUploadError):
    """Exception for invalid MIME type"""
    pass


class MissingEnvironmentVariableError(ImageUploadError):
    """Exception for missing environment variables"""
    pass


def generate_file_name(img: Image.Image) -> str:
    """Generate filename for the image

    Args:
        img: PIL Image object

    Returns:
        Generated filename string
    """
    unique_id: str = str(uuid.uuid4())
    format_ext: str = img.format.lower() if img.format else 'png'
    return f"{unique_id}.{format_ext}"

def get_s3_bucket_uri() -> str:
    """Get S3 bucket URI from environment variable"""
    s3_uri: Optional[str] = os.getenv('S3_BUCKET_URI')

    if not s3_uri:
        raise MissingEnvironmentVariableError(
            "S3_BUCKET_URI environment variable is not set"
        )

    return s3_uri


def resolve_upload_backend() -> str:
    """Decide which storage backend upload_image() should use.

    ``IMAGE_UPLOAD_BACKEND`` ("s3" or "gcs") wins when set to a known value.
    Otherwise the presence of ``GCS_BUCKET`` selects GCS, and S3 is the default
    so existing deployments keep working unchanged.
    """
    backend = (os.getenv('IMAGE_UPLOAD_BACKEND') or '').strip().lower()
    if backend in ('s3', 'gcs'):
        return backend
    return 'gcs' if os.getenv('GCS_BUCKET') else 's3'


def get_aws_signed_request(full_url, buffer, mime_type):
    credentials = Credentials(
        access_key=os.environ['AWS_ACCESS_KEY_ID'],
        secret_key=os.environ['AWS_SECRET_ACCESS_KEY'],
        token=os.environ.get('AWS_SESSION_TOKEN', None)
    )

    if hasattr(buffer, 'read'):
        # It's a file-like object (BytesIO, etc.)
        current_pos = buffer.tell()  # Save current position
        buffer.seek(0)  # Go to start
        data = buffer.read()  # Read all data
        buffer.seek(current_pos)  # Restore position
    else:
        # It's already bytes
        data = buffer

        # Calculate content hash and length
    content_hash = hashlib.sha256(data).hexdigest()
    content_length = len(data)

    # Create the request for signing with required headers
    headers = {
        'Content-Type': mime_type,
        'Content-Length': str(content_length),
        'x-amz-content-sha256': content_hash
    }

    # Create the request for signing
    aws_request = AWSRequest(
        method='PUT',
        url=full_url,
        data=data,
        headers=headers
    )

    region = os.environ.get('AWS_REGION', 'eu-west-2')

    # Sign the request
    SigV4Auth(credentials, 's3', region).add_auth(aws_request)

    return aws_request


def _upload_s3(folder_name: str, filename: str, data: bytes, mime_type: str) -> str:
    """Upload bytes to S3 with a SigV4-signed PUT and return the object URL."""
    base_url: str = get_s3_bucket_uri()
    full_url = os.path.join(base_url, folder_name, filename)

    aws_request = get_aws_signed_request(full_url, data, mime_type).prepare()

    response: requests.Response = requests.request(
        method=aws_request.method,
        url=aws_request.url,
        data=aws_request.body,
        headers=aws_request.headers,
        timeout=30
    )

    if response.status_code != 200:
        raise ImageUploadError(
            f"Upload failed with status code {response.status_code}: {response.text}"
        )

    return full_url


def _upload_gcs(folder_name: str, filename: str, data: bytes, mime_type: str) -> str:
    """Upload bytes to Google Cloud Storage and return the object URL.

    Authenticates with Application Default Credentials (the runtime service
    account on Cloud Run / GKE / GCE) -- no static keys. Set ``GCS_BUCKET`` to
    the target bucket and, optionally, ``GCS_PUBLIC_BASE_URL`` to override the
    returned URL's host (e.g. a CDN or custom domain).
    """
    if _gcs_storage is None:
        raise ImageUploadError(
            "google-cloud-storage is not installed; install lf_toolkit with the "
            "'gcs' extra to use IMAGE_UPLOAD_BACKEND=gcs"
        )

    bucket_name: Optional[str] = os.getenv('GCS_BUCKET')
    if not bucket_name:
        raise MissingEnvironmentVariableError(
            "GCS_BUCKET environment variable is not set"
        )

    blob_name = f"{folder_name}/{filename}"
    client = _gcs_storage.Client()
    blob = client.bucket(bucket_name).blob(blob_name)
    blob.upload_from_string(data, content_type=mime_type)

    base_url = os.getenv('GCS_PUBLIC_BASE_URL', 'https://storage.googleapis.com').rstrip('/')
    return f"{base_url}/{bucket_name}/{blob_name}"


def upload_image(img: Image.Image, folder_name: str) -> str:
    """Upload a PIL image to the configured storage backend.

    The backend is chosen by :func:`resolve_upload_backend` (env var
    ``IMAGE_UPLOAD_BACKEND=s3|gcs``, else auto-detected from ``GCS_BUCKET`` /
    ``S3_BUCKET_URI``, defaulting to S3).

    Args:
        img: PIL Image object to upload
        folder_name: name of the folder/prefix to store the image under

    Returns:
        The public URL of the uploaded object

    Raises:
        InvalidMimeTypeError: If MIME type validation fails
        MissingEnvironmentVariableError: If required env vars are not set
        ImageUploadError: If upload fails for any reason
    """
    try:
        filename: str = generate_file_name(img)

        if img.format is None:
            img.format = 'PNG'

        mime_type = FORMAT_TO_MIME[img.format.upper()]

        buffer: BytesIO = BytesIO()
        img.save(buffer, format=img.format)
        data: bytes = buffer.getvalue()

        backend = resolve_upload_backend()
        if backend == 'gcs':
            return _upload_gcs(folder_name, filename, data, mime_type)
        return _upload_s3(folder_name, filename, data, mime_type)

    except ImageUploadError:
        # InvalidMimeTypeError / MissingEnvironmentVariableError / backend errors
        # already carry a useful message -- propagate as-is.
        raise
    except requests.exceptions.RequestException as e:
        raise ImageUploadError(f"Network error: {str(e)}")
    except Exception as e:
        raise ImageUploadError(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    img = Image.new('RGB', (100, 100), color='red')
    img.format = 'JPEG'

    # Execute
    result = upload_image(img, "eduvision")
    print(result)
