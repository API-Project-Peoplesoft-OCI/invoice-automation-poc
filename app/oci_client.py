import json
from pathlib import Path
from typing import Any

import oci

from app.config import settings
from app.invoice_mapper import normalize_invoice


class OCIInvoiceClient:
    def __init__(self) -> None:
        config = oci.config.from_file(
            file_location="~/.oci/config",
            profile_name=settings.oci_config_profile,
        )

        self.object_storage = (
            oci.object_storage.ObjectStorageClient(config)
        )
        self.document_client = (
            oci.ai_document.AIServiceDocumentClient(config)
        )

        self.namespace = self.object_storage.get_namespace().data

    def upload_invoice(
        self,
        file_path: Path,
        object_name: str | None = None,
    ) -> str:
        if not file_path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        object_name = object_name or file_path.name

        with file_path.open("rb") as file_handle:
            self.object_storage.put_object(
                namespace_name=self.namespace,
                bucket_name=settings.input_bucket,
                object_name=object_name,
                put_object_body=file_handle,
            )

        return object_name

    def analyze_invoice(
        self,
        object_name: str,
    ) -> tuple[str, dict[str, Any]]:
        if not settings.oci_compartment_id:
            raise ValueError(
                "OCI_COMPARTMENT_ID is missing."
            )

        document = (
            oci.ai_document.models.ObjectStorageDocumentDetails(
                source="OBJECT_STORAGE",
                namespace_name=self.namespace,
                bucket_name=settings.input_bucket,
                object_name=object_name,
            )
        )

        key_value_feature = (
            oci.ai_document.models.DocumentKeyValueExtractionFeature(
                feature_type="KEY_VALUE_EXTRACTION"
            )
        )

        table_feature = (
            oci.ai_document.models.DocumentTableExtractionFeature(
                feature_type="TABLE_EXTRACTION"
            )
        )

        analyze_details = (
            oci.ai_document.models.AnalyzeDocumentDetails(
                compartment_id=settings.oci_compartment_id,
                document=document,
                features=[
                    key_value_feature,
                    table_feature,
                ],
                document_type="INVOICE",
            )
        )

        response = self.document_client.analyze_document(
            analyze_document_details=analyze_details
        )

        raw_result = oci.util.to_dict(response.data)

        normalized_invoice, review = normalize_invoice(
            raw_result
        )

        document_id = Path(object_name).stem

        processing_status = (
            "REVIEW_REQUIRED"
            if review["requires_review"]
            else "READY"
        )

        final_document = {
            "document_id": document_id,
            "processing_status": processing_status,
            "source": {
                "bucket": settings.input_bucket,
                "object_name": object_name,
            },
            "invoice": normalized_invoice,
            "validation": {
                "warnings": review["warnings"],
                "field_metadata": review["field_metadata"],
            },
        }

        output_name = f"normalized/{document_id}.json"

        output_bytes = json.dumps(
            final_document,
            indent=2,
            default=str,
        ).encode("utf-8")

        self.object_storage.put_object(
            namespace_name=self.namespace,
            bucket_name=settings.output_bucket,
            object_name=output_name,
            put_object_body=output_bytes,
            content_type="application/json",
        )

        return output_name, final_document