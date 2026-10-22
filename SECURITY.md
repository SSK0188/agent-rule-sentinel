# Security Policy

Agent Rule Sentinel manipulates local instruction files, which could contain confidential operational details.

**Scope:** This project refuses path traversal and symlink targets, requires explicit apply, and backs up existing text. Its regex-based secret detection is intentionally limited and is not a security certification. It does not contact third-party systems or execute project instructions.

**Report vulnerabilities privately:** Use GitHub's "Report a vulnerability" option in the Security tab if the repository supports private vulnerability reporting. If unavailable, ask for a private contact channel through a public Issue **without including exploitation details or credentials**.

Do not publish token values, private keys, internal project instructions, or exploit steps against real systems. High-risk fixes should include regression tests and evidence of safe handling. No service-level response time is promised.
