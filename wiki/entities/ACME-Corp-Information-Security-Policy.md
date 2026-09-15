---
sources: ["summaries/infosec_policy.md"]
type: "Other"
description: "The ACME Corp Information Security Policy outlines the company's requirements for protecting customer and company data."
---

# ACME Corp Information Security Policy
This policy defines ACME Corp's requirements for protecting the confidentiality, integrity, and availability of customer and company data.

## Access Control
*Access to systems is granted on a least-privilege basis.*

## Customer Data Classification
*Customer data is classified into four levels:*

Level 1: Public (marketing materials, published product docs.)
Level 2: Internal (general company information, policy documents)
Level 3: Confidential (customer PII, account data)
Level 4: Restricted (payment card data, authentication tokens, API keys)

## Acceptable Encryption Standards
*Data at rest:* AES-256 minimum

## Incident Response
*All suspected security incidents must be reported immediately.

## Penetration Testing and Vulnerability Disclosure
*External penetration tests are performed annually.*

## Monitoring and Audit Logging
*All access to Level 3 and Level 4 data is logged.

## Third-Party and API Integrations
*Any third-party integration that reads or writes customer data requires a security review before production deployment.*

## Related Documents
- [[summaries/infosec_policy]]
