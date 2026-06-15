---
name: jtbd-interview-planner
description: Guidelines for conducting thorough code reviews with focus on security and performance.
metadata:
  author: your-team
  version: "1.0"
---

## Code Review Guidelines

When reviewing code, follow this checklist:

1. **Security**: Check for injection vulnerabilities, auth bypasses, and data exposure
2. **Performance**: Look for N+1 queries, unnecessary allocations, and blocking calls
3. **Readability**: Ensure clear naming, appropriate comments, and consistent style
4. **Testing**: Verify adequate test coverage for new functionality

### Severity Levels
- **Critical**: Security vulnerabilities, data loss risks → block merge
- **Major**: Performance issues, logic errors → request changes
- **Minor**: Style issues, naming suggestions → approve with comments