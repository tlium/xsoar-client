from xsoar_client.xsoar_client import Client


class TestClass:
    client = Client(verify_ssl=False, server_version=6, artifacts_location="S3", custom_pack_authors=["MyOrg"], s3_bucket_name="xsoar-cicd")
    assert isinstance(client, Client)

    def test_xsoar_connectivity(self) -> None:
        connectivity_ok = self.client.test_connectivity()
        assert connectivity_ok is True

    def test_xsoar_installed_packs(self) -> None:
        results = self.client.get_installed_packs()
        assert results is not None

    def test_xsoar_expired_packs(self) -> None:
        results = self.client.get_installed_expired_packs()
        assert results is not None

    def test_xsoar_outdated_packs(self) -> None:
        results = self.client.get_outdated_packs()
        assert results is not None
