import requests
import uuid
import os
from io import BytesIO
from typing import Dict, List, Optional
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

MIME_TO_FORMAT: Dict[str, List[str]] = {
    'image/jpeg': ['JPEG', 'JPG'],
    'image/png': ['PNG'],
    'image/gif': ['GIF'],
    'image/bmp': ['BMP'],
    'image/webp': ['WEBP'],
    'image/tiff': ['TIFF', 'TIF'],
    'image/x-icon': ['ICO'],
}

FORMAT_TO_EXTENSION: Dict[str, List[str]] = {
    'JPEG': ['.jpg', '.jpeg', '.jpe'],
    'PNG': ['.png'],
    'GIF': ['.gif'],
    'BMP': ['.bmp'],
    'WEBP': ['.webp'],
    'TIFF': ['.tiff', '.tif'],
    'ICO': ['.ico'],
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


def validate_mime_type(mime_type: str, img: Image.Image, filename: str) -> bool:
    """Validate MIME type against image format and filename

    Args:
        mime_type: MIME type string to validate
        img: PIL Image object
        filename: Name of the file

    Returns:
        True if validation passes

    Raises:
        InvalidMimeTypeError: If MIME type is invalid or doesn't match image
    """
    if mime_type not in MIME_TO_FORMAT:
        raise InvalidMimeTypeError(
            f"Invalid MIME type '{mime_type}'. "
            f"Supported types: {', '.join(MIME_TO_FORMAT.keys())}"
        )

    img_format: Optional[str] = img.format.upper() if img.format else None

    if img_format:
        allowed_formats: List[str] = MIME_TO_FORMAT[mime_type]
        if img_format not in allowed_formats:
            raise InvalidMimeTypeError(
                f"MIME type '{mime_type}' does not match image format '{img_format}'. "
                f"Expected formats for {mime_type}: {', '.join(allowed_formats)}"
            )

    file_ext: str = filename[filename.rfind('.'):].lower()

    if img_format and img_format in FORMAT_TO_EXTENSION:
        valid_extensions: List[str] = FORMAT_TO_EXTENSION[img_format]
        if file_ext not in valid_extensions:
            raise InvalidMimeTypeError(
                f"File extension '{file_ext}' does not match format '{img_format}'. "
                f"Expected extensions: {', '.join(valid_extensions)}"
            )

    return True


def get_s3_bucket_uri() -> str:
    """Get S3 bucket URI from environment variable"""
    s3_uri: Optional[str] = os.getenv('S3_BUCKET_URI')

    if not s3_uri:
        raise MissingEnvironmentVariableError(
            "S3_BUCKET_URI environment variable is not set"
        )

    return s3_uri


def upload_image(img: Image.Image, mime_type: str) -> Dict:
    """Upload PIL image with comprehensive MIME type validation

    Args:
        img: PIL Image object to upload
        mime_type: MIME type for the upload

    Returns:
        JSON response from the server as a dictionary

    Raises:
        InvalidMimeTypeError: If MIME type validation fails
        MissingEnvironmentVariableError: If S3_BUCKET_URI is not set
        ImageUploadError: If upload fails for any reason
    """
    try:
        # Get URL from environment variable
        url: str = get_s3_bucket_uri()

        filename: str = generate_file_name(img)

        validate_mime_type(mime_type, img, filename)

        buffer: BytesIO = BytesIO()
        img_format: str = img.format if img.format else 'PNG'
        img.save(buffer, format=img_format)
        buffer.seek(0)

        files: Dict[str, tuple] = {'file': (filename, buffer, mime_type)}
        response: requests.Response = requests.post(url, files=files, timeout=30)

        if response.status_code != 200:
            raise ImageUploadError(
                f"Upload failed with status code {response.status_code}: {response.text}"
            )

        return response.json()['url']

    except (InvalidMimeTypeError, MissingEnvironmentVariableError):
        raise
    except requests.exceptions.RequestException as e:
        raise ImageUploadError(f"Network error: {str(e)}")
    except Exception as e:
        raise ImageUploadError(f"Unexpected error: {str(e)}")

