from __future__ import annotations

import tarfile
from io import BytesIO, StringIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .xsoar_client import Client


class Content:
    def __init__(self, client: Client) -> None:
        self.client = client

    def get_bundle(self) -> dict[str, StringIO]:
        """Downloads and extracts the custom content bundle."""
        endpoint = "/content/bundle"
        response = self.client._make_request(endpoint=endpoint, method="GET")
        loaded_files: dict[str, StringIO] = {}

        with tarfile.open(fileobj=BytesIO(response.content), mode="r") as tar:
            tar_members = tar.getmembers()

            for file in tar_members:
                file_name = file.name.lstrip("/")

                if extracted_file := tar.extractfile(file):
                    file_data = StringIO(extracted_file.read().decode("utf-8"))
                    loaded_files[file_name] = file_data
        return loaded_files

    def get_detached(self, content_type: str | None):
        """Returns detached content. Currently supports script, playbooks, layouts."""
        pass

    def download_item(self, item_type: str, item_id: str) -> bytes:
        """Downloads a content item by type and ID."""
        if item_type == "playbook":
            endpoint = f"/{item_type}/{item_id}/yaml"
            response = self.client._make_request(endpoint=endpoint, method="GET")
        else:
            msg = 'Uknown item_type selected for download. Must be one of ["playbook"]'
            raise ValueError(msg)
        response.raise_for_status()
        return response.content

    def attach_item(self, item_type: str, item_id: str) -> None:
        """Attaches a content item to the server-managed version."""
        if item_type == "playbook":
            endpoint = f"/{item_type}/attach/{item_id}"
            response = self.client._make_request(endpoint=endpoint, method="POST")
        else:
            msg = 'Uknown item_type selected. Must be one of ["playbook"]'
            raise ValueError(msg)
        response.raise_for_status()

    def detach_item(self, item_type: str, item_id: str) -> None:
        """Detaches a content item from the server-managed version."""
        if item_type == "playbook":
            endpoint = f"/{item_type}/detach/{item_id}"
            response = self.client._make_request(endpoint=endpoint, method="POST")
        else:
            msg = 'Uknown item_type selected. Must be one of ["playbook"]'
            raise ValueError(msg)
        response.raise_for_status()
