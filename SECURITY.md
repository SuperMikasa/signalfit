# Security and privacy

SignalFit is designed to work with career data, which can contain personally identifying information.

The default CLI reads resumes locally and writes results only to the Git-ignored `.signalfit/` directory. It does not upload resumes or publish reports. Users should still review generated artifacts before moving them outside that directory.

## Supported versions

Security and privacy fixes are applied to the latest release.

## Report a problem

Do not open a public issue if you discover exposed credentials, cookies, private resumes, private messages, or other sensitive data. Contact the repository owner privately through the security-reporting channel configured on the source host.

Include the affected path, why it is sensitive, and the minimum steps needed to reproduce the exposure. Do not copy additional private data while investigating.

## Local import boundary

The public web interface reads imported JSON in the browser. The current version does not send imported files to a server or persist them in a database.
