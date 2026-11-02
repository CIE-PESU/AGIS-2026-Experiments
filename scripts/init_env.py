"""Create .env with unique local secrets; never overwrite an existing configuration."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    raise SystemExit(".env already exists; left unchanged")
text = (root / ".env.example").read_text(encoding="utf-8")
text = text.replace(
    "CHANGE_ME_TO_A_LONG_RANDOM_SECRET_AT_LEAST_32_CHARACTERS", secrets.token_urlsafe(48)
)
text = text.replace("CHANGE_ME_TO_A_LONG_RANDOM_WORKER_SECRET", secrets.token_urlsafe(48))
with target.open("x", encoding="utf-8") as output:
    output.write(text)
target.chmod(0o600)
print("Created .env; configure the LLM/search API keys before starting AGIS")
