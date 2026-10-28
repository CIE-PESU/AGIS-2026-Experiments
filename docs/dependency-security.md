# Dependency security

The lockfile is authoritative. Run `uv run python scripts/audit_dependencies.py` and `npm audit --prefix frontend` after dependency changes. The Python checker prints known upstream risks and rejects new, changed-version, or expired exceptions. It does not claim that the environment is free of advisories. Run `uv run pip-audit` for the unfiltered findings.

As of 28 October 2026, seven Python advisories remain in two transitive dependencies:

- **ChromaDB 1.5.9:** CrewAI requires it; the latest published ChromaDB release has four server-side advisories and no patched release. AGIS does not start a Chroma HTTP server or expose Chroma collection configuration. Do not deploy a Chroma server alongside this application. [CrewAI upstream issue](https://github.com/crewAIInc/crewAI/issues/8313), [published ChromaDB release](https://pypi.org/project/chromadb/).
- **Filelock 3.32.7:** LiteLLM declares `filelock<4`, which prevents selecting the patched 4.2.1 release without violating the supported dependency contract. The affected features involve SQLite reader/writer locks or Windows soft locks in directories writable by other local accounts. Run AGIS as a dedicated user with private cache/lock directories; do not use shared writable temporary directories for locks. [POSIX/SQLite advisory](https://github.com/advisories/GHSA-v4x8-3wr5-3wq8), [Windows SQLite advisory](https://github.com/advisories/GHSA-9vhv-jxww-xfm5), [Windows soft-lock advisory](https://github.com/advisories/GHSA-567q-5qvw-pf92).

Exact versions, IDs, reasons, and the next review deadline are recorded in `dependency-advisories.json`. Exceptions expire on 1 January 2027. Replace affected dependencies or remove exceptions when upstream compatibility permits a patch. A future upgrade must be tested; do not force an incompatible version simply to silence an audit.

The frontend lock currently has no npm audit findings. JWT handling uses PyJWT with explicit algorithm and required claims. Local passwords use salted scrypt. Refresh tokens use indexed SHA-256 digests of high-entropy random tokens and atomic one-time rotation.

## Existing installations

Encrypted passwords are migrated to scrypt on successful login when the original private `FERNET_KEY` remains configured. New installations do not need Fernet. Old bcrypt refresh tokens require users to sign in again. JWT lifetimes follow the configured value; the new template defaults to 15 minutes. Existing `.env` files are deliberately not overwritten.

Tracked account seed data has been removed from the current tree and replaced with empty fixtures. Historical Git commits can still contain those records. Anyone who had access to both old seed data and the shared Fernet key could recover passwords: rotate affected credentials and review repository access. No shared keys, external passwords, or Git history are changed automatically by this code update.

New unique indexes enforce one active student workspace and one active session per owner. If an existing database contains duplicates, back it up and resolve ownership/archive conflicts before startup. Never delete existing records solely to make an index build succeed. Database backups and TLS/reverse-proxy deployment are operator responsibilities.

The latest compatible Beanie/lazy-model and CrewAI-tools releases also emit upstream deprecation warnings. Tests do not suppress them; moving to Beanie 2 requires a separate Motor/PyMongo migration and compatibility validation. They are warnings rather than failing application checks.
