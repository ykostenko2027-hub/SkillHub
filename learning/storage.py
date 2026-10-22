import os
import uuid
from django.conf import settings
from .exceptions import InvalidFileUploadException


class LocalCoverImageStorage:
    ALLOWED_TYPES = {
        "image/jpeg": [".jpg", ".jpeg"],
        "image/png": [".png"],
    }
    MAX_FILE_SIZE = 5 * 1024 * 1024

    @classmethod
    def get_upload_dir(cls):
        upload_dir = getattr(settings, "MEDIA_ROOT", settings.BASE_DIR / "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        return str(upload_dir)

    @classmethod
    def validate_file(cls, file):
        if not file or getattr(file, "size", 0) == 0:
            raise InvalidFileUploadException("Select a non-empty JPEG or PNG file.")
        if file.size > cls.MAX_FILE_SIZE:
            raise InvalidFileUploadException("The cover image must not exceed 5 MB.")
        content_type = getattr(file, "content_type", "")
        if content_type not in cls.ALLOWED_TYPES:
            raise InvalidFileUploadException("Only JPEG and PNG cover images are supported.")
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in cls.ALLOWED_TYPES[content_type]:
            raise InvalidFileUploadException("The file extension does not match the declared image type.")
        return ext

    @classmethod
    def save(cls, file):
        ext = cls.validate_file(file)
        file_name = f"{uuid.uuid4().hex}{ext}"
        destination = os.path.join(cls.get_upload_dir(), file_name)
        with open(destination, "wb+") as destination_file:
            for chunk in file.chunks():
                destination_file.write(chunk)
        return file_name

    @classmethod
    def get_path(cls, file_name):
        if not file_name or os.path.basename(file_name) != file_name:
            return None
        path = os.path.join(cls.get_upload_dir(), file_name)
        if os.path.exists(path):
            return path
        return None

    @classmethod
    def delete(cls, file_name):
        path = cls.get_path(file_name)
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
