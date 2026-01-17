from __future__ import annotations

import io
import os

import boto3
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContainerClient
from botocore.exceptions import EndpointConnectionError, NoCredentialsError, PartialCredentialsError
from botocore.httpsession import ConnectTimeoutError
from packaging import version

SUPPORTED_STORES = ["S3", "Azure"]


class ArtifactProvider:
    def __init__(
        self,
        *,
        location: str = "S3",
        s3_bucket_name: str | None = None,
        azure_storage_account_url: str = "",
        azure_container_name: str = "",
        verify_ssl: str | bool = True,
        service: BlobServiceClient | None = None,
        container_client: ContainerClient | None = None,
    ) -> None:
        if not location:
            self.artifacts_repo = None
            return
        if location not in SUPPORTED_STORES:
            msg = f"Artifact store {location} is not yet implemented."
            raise NotImplementedError(msg)
        if location == "S3":
            self.artifacts_repo = location
            self.s3_bucket_name = s3_bucket_name
            self.verify_ssl = verify_ssl
            self.boto3_session = boto3.session.Session()  # pyright: ignore  # noqa: PGH003
            self.s3 = self.boto3_session.resource("s3")
        if location == "Azure":
            self.artifacts_repo = location
            try:
                credential = os.environ["SAS_TOKEN"]
            except KeyError:
                msg = "Required environment variable SAS_TOKEN is not set."
                raise RuntimeError(msg)
            self.service = BlobServiceClient(account_url=azure_storage_account_url, credential=credential)
            self.container_client = self.service.get_container_client(azure_container_name)

    def test_connection(self) -> bool:
        if self.artifacts_repo == "S3":
            return self._test_connection_aws()
        if self.artifacts_repo == "Azure":
            return self._test_connection_azure()
        return False

    def _test_connection_azure(self) -> bool:
        # Maybe we should try/except a few errors here...
        self.container_client.get_container_properties()
        return True

    def _test_connection_aws(self) -> bool:
        try:
            bucket = self.s3.Bucket(self.s3_bucket_name)  # lager en bucketresource object for bucket_name
            bucket.load()

        except NoCredentialsError as ex:
            msg = "AWS credentials not found."
            raise RuntimeError(msg) from ex
        except PartialCredentialsError as ex:
            msg = "Incomplete AWS credentials."
            raise RuntimeError(msg) from ex
        except EndpointConnectionError as ex:
            msg = "Could not connect to the S3"
            raise RuntimeError(msg) from ex
        except ConnectTimeoutError as ex:
            msg = "Connection timed out"
            raise RuntimeError(msg) from ex
        except Exception as ex:  # noqa: BLE001
            print(f"An error occurred: {ex}")
        return True

    def _is_available_s3(self, *, pack_id: str, pack_version: str) -> bool:
        """Returns True if pack is available, False otherwise"""
        key_name = f"content/packs/{pack_id}/{pack_version}/{pack_id}.zip"
        try:
            self.s3.Object(self.s3_bucket_name, key_name).load()
        except Exception:  # noqa: BLE001
            return False
        return True

    def _is_available_azure(self, *, pack_id: str, pack_version: str) -> bool:
        key_name = f"content/packs/{pack_id}/{pack_version}/{pack_id}.zip"
        blob_client = self.container_client.get_blob_client(blob=key_name)
        try:
            blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False

    def is_available(self, *, pack_id: str, pack_version: str) -> bool:
        if self.artifacts_repo == "S3":
            return self._is_available_s3(pack_id=pack_id, pack_version=pack_version)
        if self.artifacts_repo == "Azure":
            return self._is_available_azure(pack_id=pack_id, pack_version=pack_version)
        raise NotImplementedError

    def _download_azure(self, *, pack_id: str, pack_version: str) -> bytes:
        key_name = f"content/packs/{pack_id}/{pack_version}/{pack_id}.zip"
        stream = io.BytesIO()
        download_stream = self.container_client.download_blob(blob=key_name)
        return download_stream.readall()

    def _download_s3(self, *, pack_id: str, pack_version: str) -> bytes:
        """Downloads a custom content pack from AWS S3."""
        key_name = f"content/packs/{pack_id}/{pack_version}/{pack_id}.zip"
        obj = self.s3.Object(bucket_name=self.s3_bucket_name, key=key_name)
        response = obj.get()
        return response["Body"].read()

    def download(self, *, pack_id: str, pack_version: str) -> bytes:
        if self.artifacts_repo == "S3":
            return self._download_s3(pack_id=pack_id, pack_version=pack_version)
        if self.artifacts_repo == "Azure":
            return self._download_azure(pack_id=pack_id, pack_version=pack_version)
        raise NotImplementedError

    def _get_latest_version_azure(self, pack_id: str) -> str:
        prefix = f"content/packs/{pack_id}/"
        iter_names = self.container_client.list_blob_names(name_starts_with=prefix)
        version_list = [x.split("/")[3] for x in list(iter_names)]
        return str(max(version_list, key=version.parse))

    def _get_latest_version_s3(self, pack_id: str) -> str:
        b3_client = boto3.client("s3", verify=self.verify_ssl)
        result = b3_client.list_objects_v2(
            Bucket=self.s3_bucket_name,
            Prefix=f"content/packs/{pack_id}/",
            Delimiter="/",
        )
        version_list = [x["Prefix"].split("/")[3] for x in result.get("CommonPrefixes")]
        return str(max(version_list, key=version.parse))

    def get_latest_version(self, pack_id: str) -> str:
        if self.artifacts_repo == "S3":
            return self._get_latest_version_s3(pack_id=pack_id)
        if self.artifacts_repo == "Azure":
            return self._get_latest_version_azure(pack_id=pack_id)
        raise NotImplementedError
