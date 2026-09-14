# enterprise-synthetic-document-generator

[中文](./README.md) | English

---

## 1. Overview

Convert reference PDFs (contracts, forms, reports) into synthetic versions—keeping structure and formatting intact, but replacing body text and PII with realistic fictional content, then scanning for any missed PII (Huawei Cloud NLP audit).

Suitable for: RAG evaluation corpus generation, model benchmarking, partner document handovers.

---

## 2. Key Features

- **PDF to Synthetic Document**: Keep original layout, chapter structure, table formats; replace text with fictional content
- **PII Audit**: Huawei Cloud NLP entity recognition, auto-detect names, addresses, IDs, etc.
- **Multi-variable Generation**: Generate N independent synthetic versions from the same PDF
- **Offline Data Generation**: Use presets to generate structured synthetic data without API calls

---

## 3. Huawei Cloud Services

| Service | Usage | Pricing |
|---------|-------|---------|
| ModelArts Studio | Document rewriting LLM | Per token |
| NLP Entity Recognition | PII detection | Per call |
| OBS | Temporary file storage | Per storage |

---

## 4. Prerequisites

- Huawei Cloud account (real-name authenticated)
- ModelArts Studio service enabled
- NLP service enabled
- AK/SK credentials
- Python 3.10+

---

## 5. Quick Start

```bash
# Clone repository
git clone <repo-url>
cd enterprise-synthetic-document-generator

# Install
pip install -e .

# Configure credentials
export HUAWEI_CLOUD=1
export HUAWEI_AK="your-ak"
export HUAWEI_SK="your-sk"
export HUAWEI_REGION="cn-north-4"

# Convert PDF (synthetic mode)
pocsynth convert contract.pdf --model pangu_s --format html --mode synthetic --pii-audit --redact-values

# Generate synthetic data (offline, no API)
pocsynth generate --preset crm_contacts --rows 1000 --seed 42 -o ./out
```

---

## 6. Directory Structure

```
enterprise-synthetic-document-generator/
├── docs/
│   ├── architecture.md           # Huawei Cloud architecture
│   ├── deployment-guide.md      # Deployment guide
│   └── response-constraints.md # Constraints
├── others/                      # Artifacts
├── src/
│   └── adapter/                # Huawei Cloud adapter
│       ├── huawei_session.py
│       ├── modelarts_adapter.py
│       ├── nlp_adapter.py
│       └── cloud_switcher.py
├── LICENSE
├── README.md
└── README-en.md
```

---

## 7. Supported PDF Types

| Type | Description |
|------|-------------|
| Contracts | Terms, party information |
| Forms | Fields, filled content |
| Reports | Data, analysis conclusions |

---

## 8. PII Detection Entities

| Entity Type | Example |
|-------------|---------|
| Person Name | Zhang San, Li Si |
| ID Number | ID card, passport |
| Address | Home address, office address |
| Phone | Mobile, landline |

---

## 9. Offline Presets

| Preset | Description |
|--------|-------------|
| crm_contacts | CRM contact data |
| invoices | Invoice data |
| orders | Order data |

---

## 10. License

MIT No Attribution - Copyright Huawei Cloud
