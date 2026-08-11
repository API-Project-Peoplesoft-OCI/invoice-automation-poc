from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import settings
import json
from pathlib import Path
from typing import Any


from app.config import settings


def save_normalized_invoice(
    document_id: str,
    data: dict[str, Any],
) -> Path:
    destination = (
        settings.output_dir
        / f"{document_id}.json"
    )

    destination.write_text(
        json.dumps(
            data,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    return destination


def load_normalized_invoice(
    document_id: str,
) -> dict[str, Any]:
    path = settings.output_dir / f"{document_id}.json"

    if not path.exists():
        raise FileNotFoundError(
            f"Invoice {document_id} was not found."
        )

    return json.loads(
        path.read_text(encoding="utf-8")
    )


ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}


def validate_file_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(
            f"Unsupported file type. Allowed types: {allowed}"
        )

    return extension


async def save_uploaded_invoice(
    upload_file: UploadFile,
) -> tuple[str, Path]:
    original_filename = upload_file.filename or "invoice"
    extension = validate_file_extension(original_filename)

    document_id = uuid4().hex
    saved_filename = f"{document_id}{extension}"
    destination = settings.upload_dir / saved_filename

    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    total_size = 0

    try:
        with destination.open("wb") as output_file:
            while chunk := await upload_file.read(1024 * 1024):
                total_size += len(chunk)

                if total_size > max_size_bytes:
                    output_file.close()
                    destination.unlink(missing_ok=True)

                    raise ValueError(
                        "Uploaded file exceeds the maximum size of "
                        f"{settings.max_upload_size_mb} MB."
                    )

                output_file.write(chunk)
    finally:
        await upload_file.close()

    return document_id, destination