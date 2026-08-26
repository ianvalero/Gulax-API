from __future__ import annotations
from typing import TYPE_CHECKING
import logging
import uuid
import aiofiles
from pathlib import Path

from app.config.settings import settings
from app.exceptions import FileValidationError

if TYPE_CHECKING:
    from fastapi import UploadFile


class StorageGateway:
    def __init__(self):
        self.logger = logging.getLogger(f"app.{__name__}")
        self._base_path = Path(settings.files_storage_path).resolve()
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._max_file_size = settings.max_file_size
        self._allowed_file_types = settings.allowed_file_types
        self.logger.info("Storage Gateway initialized")

    async def save(self, file: UploadFile) -> Path:
        self._validate(file)

        file_path = Path(file.filename)
        filename = file_path.stem.replace(" ", "_")
        save_path = self._base_path / f"{str(uuid.uuid4())}_{filename}{file_path.suffix}"

        bytes_written = 0
        async with aiofiles.open(save_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                bytes_written += len(chunk)
                if bytes_written > self._max_file_size:
                    await buffer.close()
                    save_path.unlink(missing_ok=True)
                    raise FileValidationError(f"File size exceeds the maximum limit of {self._max_file_size} bytes")
                await buffer.write(chunk)

        self.logger.info(f"Document file {file.filename} saved to {save_path}")
        return self.resolve_path(save_path)

    def delete(self, file_path: str | Path) -> bool:
        try:
            path = self.resolve_path(file_path)
        except FileValidationError:
            self.logger.warning(f"Invalid storage path: {file_path}")
            return False

        if not path.exists():
            self.logger.warning(f"Local file not found: {path}")
            return False

        try:
            path.unlink()
            self.logger.info(f"Local file deleted: {path}")
            return True
        except Exception:
            self.logger.exception(f"Error deleting local file {path}")
            return False

    def resolve_path(self, file_path: str | Path) -> Path:
        full_path = Path(file_path).resolve()
        if not full_path.is_relative_to(self._base_path):
            raise FileValidationError(f"Invalid storage path: {file_path}")

        return full_path

    def _validate(self, file: UploadFile) -> None:
        extension = Path(file.filename).suffix.lower()
        if extension not in self._allowed_file_types:
            raise FileValidationError(f"Invalid file type: {extension}")

        if file.size is not None and file.size > self._max_file_size:
            raise FileValidationError(f"File size exceeds the maximum limit of {self._max_file_size} bytes")