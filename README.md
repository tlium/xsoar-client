# xsoar-client
-----

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [License](#license)

## Installation
1. Install with pip:
```
pip install xsoar-client
```

## Configuration
For the XSOAR client to work properly you need to have a few environment variables set:
- DEMISTO_API_KEY - API key for XSOAR
- DEMISTO_BASE_URL - URL to XSOAR
- AWS_PROJECT - must contain the name of the AWS profile configured below

This application requires that you store your deployment artifacts (XSOAR content packs) in an artifact repository somewhere. Currently only AWS S3 is supported.
You also need to be logged in to the proper AWS project.
Install `awscli` for your platform and make sure you are properly authenticated.

## License
`xsoar-client` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
