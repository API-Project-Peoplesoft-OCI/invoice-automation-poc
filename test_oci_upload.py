from pathlib import Path

import oci


BUCKET_NAME = "invoice-poc-input"
FILE_PATH = Path("uploads/31a90d8390574a3bb5d03d2810508f31.png")


def main() -> None:
    if not FILE_PATH.exists():
        raise FileNotFoundError(
            f"Could not find the test invoice at: {FILE_PATH.resolve()}"
        )

    config = oci.config.from_file(
        file_location="~/.oci/config",
        profile_name="DEFAULT",
    )

    object_storage_client = oci.object_storage.ObjectStorageClient(config)

    namespace = object_storage_client.get_namespace().data
    object_name = FILE_PATH.name

    with FILE_PATH.open("rb") as file_handle:
        object_storage_client.put_object(
            namespace_name=namespace,
            bucket_name=BUCKET_NAME,
            object_name=object_name,
            put_object_body=file_handle,
        )

    print("Upload successful")
    print(f"File: {object_name}")
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Namespace: {namespace}")


if __name__ == "__main__":
    main()