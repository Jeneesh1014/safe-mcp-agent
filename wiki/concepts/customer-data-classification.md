---
type: "Concept"
sources: ["summaries/infosec_policy.md"]
description: "Classification of customer data into public, internal, confidential, and restricted levels"
---

# Customer Data Classification

Customer data is classified into four levels:

### Level 1: Public
* Marketing materials, published product docs.

### Level 2: Internal
* General company information, policy documents

### Level 3: Confidential
* Customer PII, account data

### Level 4: Restricted
* Payment card data, authentication tokens, API keys



# Acceptable Encryption Standards

* Data at rest: AES-256 minimum



# Incident Response

* All suspected security incidents must be reported immediately. infosec policy



# Penetration Testing and Vulnerability Disclosure

* External penetration tests are performed annually.



# Monitoring and Audit Logging

* All access to Level 3 and Level 4 data is logged.



# Third-Party and API Integrations

* Any third-party integration that reads or writes customer data requires a security review before production deployment.

This concept is part of [[concepts/customer-data-classification]]. infosec policy

## Related Documents
- [[summaries/infosec_policy]]
