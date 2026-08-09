ACME Corp — Information Security Policy
=========================================
Classification: Internal | Version: 2.1 | Owner: Security Team

1. Purpose
-----------
This policy defines ACME Corp's requirements for protecting the
confidentiality, integrity, and availability of customer and company data.
All employees and contractors with access to company systems must comply.

2. Access Control
------------------
Access to systems is granted on a least-privilege basis. Employees may only
access data and systems required for their current role. Access is revoked
within 24 hours of role change or employment termination.

Shared credentials are prohibited. Each user must have an individual
account. Service accounts require IT security approval and must be reviewed
quarterly.

3. Customer Data Classification
---------------------------------
Level 1 — Public: marketing materials, published product docs.
Level 2 — Internal: general company information, policy documents.
Level 3 — Confidential: customer PII (name, email, address), account data.
Level 4 — Restricted: payment card data, authentication tokens, API keys.

Level 3 and Level 4 data must never be transmitted via unencrypted channels
or included in outbound Slack messages, emails to unverified recipients, or
support ticket notes visible to third parties.

4. Acceptable Encryption Standards
------------------------------------
Data at rest: AES-256 minimum.
Data in transit: TLS 1.2 minimum (TLS 1.3 preferred).
Password storage: bcrypt or Argon2 with a minimum cost factor of 12.
API tokens must be stored in a secrets manager, never in environment files
committed to version control.

5. Incident Response
----------------------
All suspected security incidents must be reported immediately to the
Security team via security@acme-corp.example.com or the #security-incidents
Slack channel. The on-call security engineer carries a pager and will
respond within 15 minutes during business hours, 30 minutes out of hours.

A post-incident review (PIR) is required within 5 business days for any
Level 3 or Level 4 data exposure.

6. Penetration Testing and Vulnerability Disclosure
-----------------------------------------------------
External penetration tests are performed annually. Internal red-team
exercises occur quarterly. Employees who discover vulnerabilities in ACME
systems must report them through the internal disclosure process
(security@acme-corp.example.com) and must not exploit them further or
disclose them publicly.

7. Monitoring and Audit Logging
---------------------------------
All access to Level 3 and Level 4 data is logged with: user ID, timestamp,
action taken, and data record identifier. Logs are retained for 12 months.
Employees should not expect privacy when using company systems; monitoring
is in place for security and compliance purposes.

8. Third-Party and API Integrations
--------------------------------------
Any third-party integration that reads or writes customer data requires a
security review before production deployment. API keys used by integrations
must be scoped to the minimum permissions needed and rotated every 90 days.

Non-compliance with this policy may result in disciplinary action up to and
including termination. Legal action will be pursued for intentional breaches
involving customer data.
