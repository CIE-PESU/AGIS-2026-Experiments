# Dependency security

The lockfile is authoritative. Run `uv run python scripts/audit_dependencies.py` and `npm audit --prefix frontend` after dependency changes. The Python checker prints known upstream risks and rejects new, changed-version, or expired exceptions. It does not claim that the environment is free of advisories. Run `uv run pip-audit` for the unfiltered findings.

As of 2 November 2026, four reviewed Python advisories remain in ChromaDB 1.5.9. CrewAI requires this package; the audit lists no patched release. AGIS does not start a Chroma HTTP server or expose Chroma collection configuration. [CrewAI upstream issue](https://github.com/crewAIInc/crewAI/issues/8313), [published ChromaDB release](https://pypi.org/project/chromadb/).

Filelock is upgraded to 4.2.6, removing the thirteen findings from 3.32.7. LiteLLM still declares `filelock<4`, so root `pyproject.toml` uses an explicit uv override. This is a deliberate compatibility override: the installed consumers use the retained `FileLock`, `SoftFileLock`, and `Timeout` APIs. `tests/backend/unit/test_filelock_compatibility.py` exercises LiteLLM's profile-lock pattern, Hugging Face's `WeakFileLock`, and CacheControl's file cache. Full application and browser integration tests also run with the upgraded package. See the [upstream changelog](https://py-filelock.readthedocs.io/en/latest/changelog.html).

Only the four ChromaDB exceptions remain in `dependency-advisories.json`, expiring on 1 January 2027. No new advisory is suppressed. New or changed findings continue to fail the audit. Use the root uv environment; a standalone pip resolver will still see LiteLLM's old metadata upper bound. Review and remove the override when LiteLLM's dependency metadata permits the patched version directly.

For pip installations, use `python -m pip install --no-deps -r requirements.txt`: the generated export already contains the entire locked runtime dependency set, including platform markers. Omitting `--no-deps` produces `ResolutionImpossible` for LiteLLM/Filelock. `pip check` still reports that upstream metadata mismatch even in the validated uv environment; the application compatibility tests and advisory checker cover the intentional override. Do not use `--no-deps` when adding arbitrary new dependencies; update and validate the root lockfile instead.

The frontend lock currently has no npm audit findings. JWT handling uses PyJWT with explicit algorithm and required claims. Local passwords use salted scrypt. Refresh tokens use indexed SHA-256 digests of high-entropy random tokens and atomic one-time rotation.

## Existing installations

Encrypted passwords are migrated to scrypt on successful login when the original private `FERNET_KEY` remains configured. New installations do not need Fernet. Old bcrypt refresh tokens require users to sign in again. JWT lifetimes follow the configured value; the new template defaults to 15 minutes. Existing `.env` files are deliberately not overwritten.

Tracked account seed data has been removed from the current tree and replaced with empty fixtures. Historical Git commits can still contain those records. Anyone who had access to both old seed data and the shared Fernet key could recover passwords: rotate affected credentials and review repository access. No shared keys, external passwords, or Git history are changed automatically by this code update.

New unique indexes enforce one active student workspace and one active session per owner. If an existing database contains duplicates, back it up and resolve ownership/archive conflicts before startup. Never delete existing records solely to make an index build succeed. Database backups and TLS/reverse-proxy deployment are operator responsibilities.

The latest compatible Beanie/lazy-model and CrewAI-tools releases also emit upstream deprecation warnings. Tests do not suppress them; moving to Beanie 2 requires a separate Motor/PyMongo migration and compatibility validation. They are warnings rather than failing application checks.

## CI correction after merge verification

The first merge verification identified 17 advisories but left the audit failing. The follow-up upgrade to Filelock 4.2.6 resolves all thirteen Filelock findings and removes their old exceptions. The audit now succeeds while visibly reporting the four existing reviewed ChromaDB findings.
