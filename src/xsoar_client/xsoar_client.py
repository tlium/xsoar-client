from __future__ import annotations

import os
import tarfile
import tempfile
from io import BytesIO, StringIO
from typing import TYPE_CHECKING, TypeAlias

import demisto_client
import demisto_client.demisto_api
import requests
from demisto_client.demisto_api.rest import ApiException
from packaging import version

from .artifact_provider import ArtifactProvider

if TYPE_CHECKING:
    from requests.models import Response

JSONType: TypeAlias = dict | list | None

XSOAR_OLD_VERSION = 6
HTTP_CALL_TIMEOUT = 10

requests.packages.urllib3.disable_warnings()


class Client:
    def __init__(
        self,
        *,
        verify_ssl: bool | str = False,
        api_token: str = "",
        server_url: str = "",
        xsiam_auth_id: str = "",
        custom_pack_authors: list[str],
        server_version: int,
        artifacts_location: str = "S3",
        s3_bucket_name: str = "",
    ) -> None:
        self.api_token = None
        self.server_url = None
        self.xsiam_auth_id = None
        self.server_version = server_version
        self.installed_packs = None
        self.custom_pack_authors = custom_pack_authors
        self.installed_expired = None
        self._set_credentials(api_token, server_url, xsiam_auth_id)
        self.http_timeout = HTTP_CALL_TIMEOUT
        self.verify_ssl = verify_ssl
        self.artifact_provider = ArtifactProvider(location=artifacts_location, s3_bucket_name=s3_bucket_name)
        if self.server_version > XSOAR_OLD_VERSION:
            self.demisto_py_instance = demisto_client.configure(
                base_url=self.server_url,
                api_key=self.api_token,
                auth_id=self.xsiam_auth_id,
                verify_ssl=self.verify_ssl,
            )
        else:
            self.demisto_py_instance = demisto_client.configure(
                base_url=self.server_url,
                api_key=self.api_token,
                verify_ssl=self.verify_ssl,
            )

    def _set_credentials(
        self,
        api_token: str,
        server_url: str,
        xsiam_auth_id: str,
    ) -> None:
        if api_token and server_url:
            self.api_token = api_token
            self.server_url = server_url
            self.xsiam_auth_id = str(xsiam_auth_id)

            """
            This should be moved somewhere else
            # We only use xsiam_auth_id for XSOAR 8. Assuming XSOAR 8 server if this variable contains any value
            if int(self.server_version) > XSOAR_OLD_VERSION:
                self.server_url = f"{server_url}/xsoar/public/v1"
            """

            return
        if (api_token and not server_url) or (server_url and not api_token):
            msg = "If api_token is specified in constructor, then server_url must also be specified (or vice versa)."
            raise RuntimeError(msg)
        try:
            self.api_token = os.environ["DEMISTO_API_KEY"]
            self.server_url = os.environ["DEMISTO_BASE_URL"]
            self.xsiam_auth_id = os.environ.get("XSIAM_AUTH_ID", None)
        except KeyError as ex:
            msg = "Cannot find all required environment varaibles. Please refer to the docs for required environment variables."
            raise ValueError(msg) from ex

    def _make_request(
        self,
        *,
        endpoint: str,
        method: str,
        json: JSONType = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        data: dict | None = None,
    ) -> Response:
        """Wrapper for Requests. Sets the appropriate headers and authentication token."""
        url = f"{self.server_url}{endpoint}"
        headers = {
            "Accept": "application/json",
            "Authorization": self.api_token,
            "Content-Type": "application/json",
        }
        if self.xsiam_auth_id:
            headers["x-xdr-auth-id"] = self.xsiam_auth_id
        return requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json,
            files=files,
            data=data,
            verify=self.verify_ssl,
            timeout=self.http_timeout,
        )

    def _get_custom_content_bundle(self) -> dict[str, StringIO]:
        endpoint = "/content/bundle"
        response = self._make_request(endpoint=endpoint, method="GET")
        loaded_files: dict[str, StringIO] = {}

        with tarfile.open(fileobj=BytesIO(response.content), mode="r") as tar:
            tar_members = tar.getmembers()

            for file in tar_members:
                file_name = file.name.lstrip("/")

                if extracted_file := tar.extractfile(file):
                    file_data = StringIO(extracted_file.read().decode("utf-8"))
                    loaded_files[file_name] = file_data
        return loaded_files

    def download_item(self, item_type: str, item_id: str) -> bytes:
        if item_type == "playbook":
            endpoint = f"/{item_type}/{item_id}/yaml"
            response = self._make_request(endpoint=endpoint, method="GET")
        else:
            msg = 'Uknown item_type selected for download. Must be one of ["playbook"]'
            raise ValueError(msg)
        response.raise_for_status()
        return response.content

    def is_pack_available(self, *, pack_id: str, version: str, custom: bool) -> bool:
        if custom:
            return self.artifact_provider.is_available(pack_id=pack_id, pack_version=version)
        baseurl = "https://marketplace.xsoar.paloaltonetworks.com/content/packs"
        path = f"/{pack_id}/{version}/{pack_id}.zip"
        url = baseurl + path
        response = requests.head(url, timeout=self.http_timeout)
        if int(response.status_code) != 200:  # noqa: PLR2004, SIM103
            return False
        return True

    def attach_item(self, item_type: str, item_id: str) -> None:
        if item_type == "playbook":
            endpoint = f"/{item_type}/attach/{item_id}"
            response = self._make_request(endpoint=endpoint, method="POST")
        else:
            msg = 'Uknown item_type selected. Must be one of ["playbook"]'
            raise ValueError(msg)
        response.raise_for_status()

    def detach_item(self, item_type: str, item_id: str) -> None:
        if item_type == "playbook":
            endpoint = f"/{item_type}/detach/{item_id}"
            response = self._make_request(endpoint=endpoint, method="POST")
        else:
            msg = 'Uknown item_type selected. Must be one of ["playbook"]'
            raise ValueError(msg)
        response.raise_for_status()

    def test_connectivity(self) -> bool:
        if self.server_version > XSOAR_OLD_VERSION:  # noqa: SIM108
            endpoint = "/xsoar/health"
        else:
            endpoint = "/health"
        try:
            response = self._make_request(endpoint=endpoint, method="GET")
            response.raise_for_status()
        except Exception as ex:
            msg = "Failed to connect to XSOAR server."
            raise ConnectionError(msg) from ex
        return True

    def get_installed_packs(self) -> list[dict]:
        """Fetches a JSON blob containing a complete list of installed packages."""
        if self.server_version > XSOAR_OLD_VERSION:
            endpoint = "/xsoar/public/v1/contentpacks/metadata/installed"
        else:
            endpoint = "/contentpacks/metadata/installed"

        if self.installed_packs is None:
            response = self._make_request(
                endpoint=endpoint,
                method="GET",
            )
            response.raise_for_status()
            self.installed_packs = response.json()
        return self.installed_packs

    def get_installed_expired_packs(self) -> list[dict]:
        """Fetches a JSON blob containing a complete list of installed expired packages."""
        if self.server_version > XSOAR_OLD_VERSION:  # noqa: SIM108
            endpoint = "/xsoar/contentpacks/installed-expired"
        else:
            endpoint = "/contentpacks/installed-expired"

        if self.installed_expired is None:
            response = self._make_request(
                endpoint=endpoint,
                method="GET",
            )
            response.raise_for_status()
            self.installed_expired = response.json()
        return self.installed_expired

    def get_case(self, case_id: int) -> dict:
        endpoint = "/incidents/search"
        payload = {
            "filter": {
                "query": f"id:{case_id}",
            },
        }
        response = self._make_request(endpoint=endpoint, json=payload, method="POST")
        response.raise_for_status()
        return response.json()

    def create_case(self, data: dict) -> dict:
        if self.server_version > XSOAR_OLD_VERSION:  # noqa: SIM108
            endpoint = "/xsoar/public/v1/incident"
        else:
            endpoint = "/incident"
        response = self._make_request(endpoint=endpoint, json=data, method="POST")
        response.raise_for_status()
        return response.json()

    def is_installed(self, *, pack_id: str = "", pack_version: str = "") -> bool:
        installed_packs = self.get_installed_packs()
        if not pack_version:
            return any(item for item in installed_packs if item["id"] == pack_id)
        return any(item for item in installed_packs if item["id"] == pack_id and item["currentVersion"] == pack_version)

    def download_pack(self, pack_id: str, pack_version: str, custom: bool) -> bytes:  # noqa: FBT001
        if custom:
            return self.artifact_provider.download(pack_id=pack_id, pack_version=pack_version)
        """Downloads a upstream content pack from the official XSOAR marketplace."""
        baseurl = "https://marketplace.xsoar.paloaltonetworks.com/content/packs"
        path = f"/{pack_id}/{pack_version}/{pack_id}.zip"
        url = baseurl + path
        response = requests.get(url, timeout=HTTP_CALL_TIMEOUT)
        response.raise_for_status()
        return response.content

    def delete(self, *, pack_id: str = "") -> bool:
        raise NotImplementedError

    def deploy_zip(self, *, filepath: str = "", skip_validation: bool = False, skip_verify: bool = False) -> bool:
        params = {
            "skip_validation": "true" if skip_validation else "false",
            "skip_verify": "true" if skip_verify else "false",
        }
        self.demisto_py_instance.upload_content_packs(filepath, **params)
        return True

    def deploy_pack(self, *, pack_id: str, pack_version: str, custom: bool) -> bool:
        """Downloads a content pack from upstream or artifacts repository (depending on `custom` bool argument)."""
        params = {}
        filedata = self.download_pack(pack_id=pack_id, pack_version=pack_version, custom=custom)
        if custom:
            params["skip_validation"] = "true"
            params["skip_verify"] = "true"
        else:
            params["skip_validation"] = "false"
            params["skip_verify"] = "false"

        tmp = tempfile.NamedTemporaryFile()  # noqa: SIM115
        with open(tmp.name, "wb") as f:  # noqa: PTH123
            f.write(filedata)

        try:
            self.demisto_py_instance.upload_content_packs(tmp.name, **params)
        except ApiException as ex:
            print(f"Exception when calling DefaulApi->upload_content_packs: {ex!s}\n")
            raise RuntimeError from ex
        return True

    def get_outdated_packs(self) -> list[dict]:
        expired_packs = self.get_installed_expired_packs()
        update_available = []
        for pack in expired_packs:
            if pack["author"] in self.custom_pack_authors:
                latest_version = self.artifact_provider.get_latest_version(pack["id"])
                if latest_version == pack["currentVersion"]:
                    continue
                tmpobj = {
                    "id": pack["id"],
                    "currentVersion": pack["currentVersion"],
                    "latest": latest_version,
                    "author": pack["author"],
                }
                update_available.append(tmpobj)
            elif not pack["updateAvailable"]:
                continue
            else:
                tmpobj = {
                    "id": pack["id"],
                    "currentVersion": pack["currentVersion"],
                    "latest": max(list(pack["changelog"]), key=version.parse),
                    "author": "Upstream",
                }
                update_available.append(tmpobj)

        return update_available
