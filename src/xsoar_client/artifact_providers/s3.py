from __future__ import annotations

import boto3
from botocore.exceptions import EndpointConnectionError, NoCredentialsError, PartialCredentialsError
from botocore.httpsession import ConnectTimeoutError
from packaging import version

from .base import BaseArtifactProvider


class S3ArtifactProvider(BaseArtifactProvider):
    """AWS S3 artifact storage provider."""

    def __init__(self, *, bucket_name: str, verify_ssl: str | bool = True) -> None:
        self.bucket_name = bucket_name
        self.verify_ssl = verify_ssl
        self.session = boto3.session.Session()
        self.s3 = self.session.resource("s3")

    def test_connection(self) -> bool:
        try:
            bucket = self.s3.Bucket(self.bucket_name)
            bucket.load()
        except NoCredentialsError as ex:
            raise RuntimeError("AWS credentials not found.") from ex
        except PartialCredentialsError as ex:
            raise RuntimeError("Incomplete AWS credentials.") from ex
        except EndpointConnectionError as ex:
            raise RuntimeError("Could not connect to the S3") from ex
        except ConnectTimeoutError as ex:
            raise RuntimeError("Connection timed out") from ex
        return True

    def is_available(self, *, pack_id: str, pack_version: str) -> bool:
        key_name = self.get_pack_path(pack_id, pack_version)
        try:
            self.s3.Object(self.bucket_name, key_name).load()
            return True
        except Exception:
            return False

    def download(self, *, pack_id: str, pack_version: str) -> bytes:
        key_name = self.get_pack_path(pack_id, pack_version)
        obj = self.s3.Object(bucket_name=self.bucket_name, key=key_name)
        response = obj.get()
        return response["Body"].read()

    def get_latest_version(self, pack_id: str) -> str:
        client = boto3.client("s3", verify=self.verify_ssl)
        result = client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=f"content/packs/{pack_id}/",
            Delimiter="/",
        )
        version_list = [x["Prefix"].split("/")[3] for x in result.get("CommonPrefixes", [])]
        return str(max(version_list, key=version.parse))
