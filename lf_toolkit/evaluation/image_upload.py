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


def upload_image(img: Image.Image, folder_name: str) -> str:
    """Upload PIL image with comprehensive MIME type validation

    Args:
        folder_name: name of folder to save image
        img: PIL Image object to upload

    Returns:
        JSON response from the server as a dictionary

    Raises:
        InvalidMimeTypeError: If MIME type validation fails
        MissingEnvironmentVariableError: If S3_BUCKET_URI is not set
        ImageUploadError: If upload fails for any reason
    """
    try:
        # Get URL from environment variable
        base_url: str = get_s3_bucket_uri()

        filename: str = generate_file_name(img)

        full_url = os.path.join(base_url, folder_name, filename)

        if img.format is None:
            img.format = 'PNG'

        mime_type = FORMAT_TO_MIME[img.format.upper()]

        buffer: BytesIO = BytesIO()
        img_format: str = img.format if img.format else 'PNG'
        img.save(buffer, format=img_format)
        buffer.seek(0)

        aws_request = get_aws_signed_request(full_url, buffer, mime_type).prepare()

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

    except (InvalidMimeTypeError, MissingEnvironmentVariableError):
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
