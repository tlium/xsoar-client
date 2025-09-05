from __future__ import annotations

import boto3
from botocore.exceptions import EndpointConnectionError, NoCredentialsError, PartialCredentialsError
from botocore.httpsession import ConnectTimeoutError
from packaging import version

SUPPORTED_STORES = ["S3"]


class ArtifactProvider:
    def __init__(self, *, location: str = "S3", s3_bucket_name: str | None = None, verify_ssl: str | bool = True) -> None:
        if not location:
            self.artifacts_repo = None
            return
        if location not in SUPPORTED_STORES:
            msg = f"Artifact store {location} is not yet implemented."
            raise NotImplementedError(msg)
        self.artifacts_repo = location
        self.s3_bucket_name = s3_bucket_name
        self.verify_ssl = verify_ssl
        self.boto3_session = boto3.session.Session()  # pyright: ignore  # noqa: PGH003
        self.s3 = self.boto3_session.resource("s3")

    def test_connection(self) -> bool:
        if self.artifacts_repo == "S3":
            return self._test_connection_aws()
        return False

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

    def is_available(self, *, pack_id: str, pack_version: str) -> bool:
        if self.artifacts_repo == "S3":
            return self._is_available_s3(pack_id=pack_id, pack_version=pack_version)
        raise NotImplementedError

    def _download_s3(self, *, pack_id: str, pack_version: str) -> bytes:
        """Downloads a custom content pack from AWS S3."""
        key_name = f"content/packs/{pack_id}/{pack_version}/{pack_id}.zip"
        obj = self.s3.Object(bucket_name=self.s3_bucket_name, key=key_name)
        response = obj.get()
        return response["Body"].read()

    def download(self, *, pack_id: str, pack_version: str) -> bytes:
        if self.artifacts_repo == "S3":
            return self._download_s3(pack_id=pack_id, pack_version=pack_version)
        raise NotImplementedError

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
        raise NotImplementedError
