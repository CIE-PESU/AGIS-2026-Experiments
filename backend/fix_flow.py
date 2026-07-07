import re

with open('app/services/flow_service.py', 'r') as f:
    content = f.read()

# Fix 1: session.session_id -> str(session.id)
content = content.replace("session.session_id", "str(session.id)")

# Fix 2: session.tipsc.get("ready_for_dfv") -> getattr(session.tipsc, "ready_for_dfv", False)
content = content.replace(
    'bool(session.tipsc and session.tipsc.get("ready_for_dfv"))',
    'bool(session.tipsc and getattr(session.tipsc, "ready_for_dfv", False))'
)

# Fix 3: _load_session_id_or_raise or whatever doesn't exist. Wait, the original in repo is _load_session
# Let's check if it exists: _load_session(self, session_id: str, student_id: str)
# Let's verify what trigger_tipsc, trigger_dfv calls:
# Actually wait, original had `session = await self._load_session(session_id, student_id)`
# So I don't need to fix _load_session if it was already correct before I broke it with sed!

# Fix 4: audit_service.log_event positional arguments -> keyword arguments
# In trigger_dfv
content = content.replace(
"""        await self._audit.log_event(
            str(session.id),
            "DFV_TRIGGERED",
            student_id,
            "student",
            {"correlation_id": correlation_id},
        )""",
"""        await self._audit.log_event(
            session_id=str(session.id),
            event="DFV_TRIGGERED",
            actor=student_id,
            actor_role="student",
            metadata={"correlation_id": correlation_id},
        )"""
)

# In trigger_discovery
content = content.replace(
"""        await self._audit.log_event(
            str(session.id),
            "DISCOVERY_TRIGGERED",
            student_id,
            "student",
            {"correlation_id": correlation_id},
        )""",
"""        await self._audit.log_event(
            session_id=str(session.id),
            event="DISCOVERY_TRIGGERED",
            actor=student_id,
            actor_role="student",
            metadata={"correlation_id": correlation_id},
        )"""
)

# Fix 5: Add triggered_at to return dicts
import datetime
# trigger_tipsc return
content = re.sub(
    r'(\s*"correlation_id": correlation_id,\n\s*)\}',
    r'\g<1>"triggered_at": datetime.utcnow().isoformat(),\n        }',
    content
)

with open('app/services/flow_service.py', 'w') as f:
    f.write("from datetime import datetime\n" + content)

print("Fixed flow_service.py")
