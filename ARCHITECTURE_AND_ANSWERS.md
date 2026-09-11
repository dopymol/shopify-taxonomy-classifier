# Architecture and Candidate Answers

## High-level architecture

Browser → Django views/API → MariaDB/SQLite

Django creates durable product jobs. A background worker claims pending rows, calls the classification service, saves predictions and audit data, and updates progress. The classification service reads versioned taxonomy data and returns the best category, alternatives, confidence, and detected attributes. Reviewers approve or correct results in the web interface, and exports read the approved database state.

## 1. Category, attributes, and values

Use hierarchical candidate retrieval followed by ranking. Normalize the available product fields, retrieve likely taxonomy branches using text embeddings or TF-IDF, rerank the best candidates with category keywords and optional image evidence, then extract attributes allowed by the winning category. This is easier to audit than an unconstrained generated answer and cannot invent categories outside the taxonomy.

## 2. Title only

Normalize the title and retrieve the top taxonomy candidates. Lower confidence because evidence is missing, show alternatives, and send close or low-scoring results to review. Do not reject the entire product.

## 3. Images

Validate file type and size, fetch through a protected image service, and encode the image with CLIP or a commerce vision model. Compare its embedding with candidate category labels and combine image and text scores. Text receives more weight unless image performance has been validated. Broken images fall back to text.

## 4. Processing 10,000 products

Import with bulk database operations. Create durable product-level jobs. Workers claim small chunks, process concurrently, update progress, and retry transient failures. Cache taxonomy embeddings and send AI requests in provider-supported batches. Keep web requests short.

## 5. Taxonomy storage

Store a category ID, name, full path, parent relationship/path, version, active flag, keywords, and related attribute definitions. A normalized production schema would use separate Category, Attribute, CategoryAttribute, and AttributeValue tables. Version taxonomy releases so old classifications remain reproducible.

## 6. Confidence

Combine normalized model similarity, reranker score, agreement between text and image, amount of available evidence, and the margin between first and second candidates. Calibrate the final score on labelled validation data with isotonic regression or Platt scaling. The prototype exposes an uncalibrated ranking confidence and states that limitation.

## 7. No confident category

Return the top three candidates, mark `requires_review`, and avoid automatic approval. Capture the reviewer correction as future labelled training/evaluation data.

## 8. Broken image

Use short connection/read timeouts, content-type and size validation, bounded retries, and per-row exception handling. Record the failure and continue using text. Never stop the batch for one image.

## 9. API and database

Use REST endpoints for batch creation, progress, paginated products, product detail, review decisions, retry, and export. Use indexed status fields and immutable audit events. Apply authentication, permissions, pagination, validation, idempotency, and rate limits in production.

## 10. Two seconds per external request

Sequential time is 20,000 seconds, about 5 hours 33 minutes. Batch products when supported, cache duplicate work, prefilter candidates locally, and use bounded concurrency within API limits. Ten parallel workers give a theoretical 33-minute request time. Batches of 20 reduce 10,000 calls to 500.

## 11. Resume after 6,000 products

Persist status per product. A worker claims only `pending` rows and saves each result before taking more work. On restart, reset abandoned `processing` rows to `pending`; leave 6,000 completed rows untouched. Use idempotency keys for external calls.

## 12. Technology selection

Django supplies validation, ORM, administration, security defaults, forms, and a fast review interface. MariaDB provides durable indexed storage. Celery plus Redis/RabbitMQ is suitable for distributed production workers; the prototype uses a dependency-light Django worker command. Pandas/openpyxl import Excel. Scikit-learn supplies the explainable baseline. Sentence Transformers and CLIP are optional accuracy upgrades.

## 13. Complete design

Catalogue upload → schema mapping and validation → bulk product insert → background job queue → text/image feature preparation → taxonomy candidate retrieval → reranking → attribute extraction → confidence/review rule → database result → reviewer approval → API/CSV export. Monitoring tracks throughput, error rate, latency, review rate, and accuracy from reviewed samples.

## 14. Production effort estimate

Assumptions: one experienced Python developer, official taxonomy data is available, product schema is stable, an AI provider and infrastructure are approved, and labelled validation data is limited.

| Task | Hours |
| --- | ---: |
| Discovery, taxonomy analysis, acceptance metrics | 12 |
| Database design, taxonomy versioning, migrations | 18 |
| Secure catalogue import and validation | 20 |
| Baseline text classifier and candidate retrieval | 30 |
| Attribute extraction and validation | 24 |
| Image pipeline and multimodal ranking | 32 |
| Confidence calibration and evaluation dataset | 28 |
| Distributed batch processing, retries, resumption | 30 |
| REST API, authentication, permissions | 24 |
| Review UI, search, filters, bulk approval | 30 |
| Exports, audit history, reporting | 14 |
| Automated tests and load/failure testing | 34 |
| Security hardening and observability | 24 |
| Deployment, CI/CD, runbooks | 20 |
| Documentation and handover | 14 |
| Contingency (about 15%) | 45 |
| **Total** | **365 hours** |

At 35 productive hours per week, this is roughly 10–11 developer-weeks. A two-person team can shorten calendar time but not halve it because design, integration, and review remain sequential. Major risks are taxonomy version changes, image access, provider limits/cost, sparse product evidence, missing labelled truth, category imbalance, and unclear accuracy targets.

## 15. Practical task

This repository is the working prototype. It includes the actual catalogue importer, classifier, confidence and alternatives, review interface, progress/results APIs, resumable worker, export, and automated tests.
