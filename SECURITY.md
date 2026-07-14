# Security Policy

## Immediate credential action

Exchange credentials were previously stored in tracked repository files. The current branch has been sanitized, but Git history can retain earlier values.

Any credential that has ever appeared in this repository must be revoked or rotated at the exchange before private API access is used again.

## Repository rules

- Never commit API keys, secrets, passphrases, seed phrases, private keys, or access tokens.
- Keep private credentials in a local environment file or operating-system key store.
- Keep exchange withdrawal permission disabled for trading keys.
- Use paper mode by default.
- Live order submission must remain disabled until a separate security and execution review is completed.

## Paper mode guarantee

The `paper_trading` package contains no exchange SDK imports and no network order-submission routes. It accepts caller-supplied prices and produces virtual fills only.
