# xsoar-client

Python client library for Palo Alto XSOAR (formerly Demisto). Provides programmatic access to XSOAR servers for content pack management, case operations, and artifact handling.

This library is the foundation for [xsoar-cli](https://github.com/tlium/xsoar-cli). Use `xsoar-client` directly when building custom integrations or automation scripts. For command-line usage, use `xsoar-cli` instead.

## Installation

```bash
pip install xsoar-client
```

## Requirements

- Python 3.10 or higher
- XSOAR/XSIAM server (version 6 or 8)
- Valid API credentials

## Configuration

### Environment Variables

Authentication credentials are read from environment variables:

- `DEMISTO_API_KEY` - XSOAR API key
- `DEMISTO_BASE_URL` - XSOAR server URL (e.g., `https://xsoar.example.com`)
- `XSIAM_AUTH_ID` - XSIAM authentication ID (XSOAR 8 only)

### ClientConfig Parameters

- `server_version` (required) - XSOAR server version (6 or 8)
- `custom_pack_authors` - List of custom pack authors (default: `[]`)
- `api_token` - API token (default: from `DEMISTO_API_KEY` environment variable)
- `server_url` - Server URL (default: from `DEMISTO_BASE_URL` environment variable)
- `xsiam_auth_id` - XSIAM auth ID (default: from `XSIAM_AUTH_ID` environment variable)
- `verify_ssl` - SSL verification, boolean or path to CA bundle (default: `False`)

## Artifact Providers

Artifact providers handle storage and retrieval of custom content packs from cloud storage.

### AWS S3

Requires AWS credentials configured via AWS CLI or standard AWS environment variables.

### Azure Blob Storage

Requires `AZURE_STORAGE_SAS_TOKEN` environment variable.

## Use Cases

- Custom automation scripts for XSOAR operations
- CI/CD pipeline integration for content deployment
- Bulk operations across multiple XSOAR instances
- Custom tooling built on top of XSOAR APIs

For CLI-based workflows and usage examples, see [xsoar-cli](https://github.com/tlium/xsoar-cli).

## License

Distributed under the MIT license.
