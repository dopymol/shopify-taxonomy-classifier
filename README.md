# Shopify Product Taxonomy Classifier

A working Django prototype that imports large product catalogues, predicts a Shopify taxonomy category, extracts category attributes, calculates confidence, offers alternative categories, and routes uncertain results to a manual-review queue.

The supplied `Product List.xlsx` contains 4,999 products and 48 columns. The importer maps its fields directly, including 20 possible image URLs. It also accepts simpler CSV or Excel files with common names such as `sku`, `title`, `description`, `product_type`, `brand`, `color`, and `material`.

## What the prototype demonstrates

- Excel and CSV catalogue import
- Resilient per-product classification
- Confidence and two alternative suggestions
- Attribute extraction for colour, material, assembly requirement, and category-specific values
- Missing-description and missing-image support
- Database-backed batch processing that resumes without reprocessing completed rows
- Searchable result interface and manual approval/correction
- Progress JSON API and results API
- CSV export
- SQLite for zero-configuration evaluation and MariaDB configuration for production
- Automated tests

## Quick start on Windows

Open PowerShell in the project folder:

```powershell
py -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_taxonomy
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`, upload `sample_data/Product List.xlsx`, and select the immediate-processing option for a quick demonstration.

To classify the entire catalogue, open a second PowerShell window, activate the same environment, and run:

```powershell
python manage.py process_batches --watch
```

The worker command processes pending batches and can be stopped or restarted safely.


In a second terminal:

```bash
source venv/bin/activate
python manage.py process_batches --watch
```

## Application URLs

| URL | Purpose |
| --- | --- |
| `/` | Batch dashboard |
| `/upload/` | Upload CSV or Excel catalogue |
| `/batches/<id>/` | Results and progress |
| `/batches/<id>/progress/` | Progress JSON API |
| `/batches/<id>/api/products/` | Classification JSON API |
| `/batches/<id>/export/` | Export results as CSV |
| `/products/<id>/review/` | Approve or correct a result |
| `/admin/` | Django administration |

## Classification design

The prototype uses a hybrid, explainable retrieval classifier:

1. It combines title, description, product type, brand, colour, material, bullets, and set contents.
2. It compares the combined text against taxonomy paths and category keywords with TF-IDF word and bigram vectors.
3. It adds a bounded keyword-overlap signal.
4. It ranks all candidate categories and retains the top three.
5. It adjusts confidence using the score margin and available evidence.
6. It flags low-confidence or closely tied results for review.
7. It extracts only supported attributes found in the product evidence.

The included taxonomy JSON is a furniture-focused seed covering the supplied catalogue. It intentionally has clear local identifiers so the prototype does not misrepresent them as Shopify's official stable IDs. In production, replace this seed with a current official Shopify taxonomy export while keeping the same model fields.

This approach works without paid API keys, is fast enough for an online test, and gives deterministic results. A production enhancement could replace or blend TF-IDF with a sentence-transformer embedding model and CLIP image embeddings after calibration on labelled validation products.

## Missing and broken data

- Missing descriptions: classification continues with title, product type, brand, and other available fields; confidence is reduced.
- Missing images: no failure occurs because text classification is the baseline.
- Broken image URLs: the browser shows an unavailable-image state; classification is unaffected.
- Empty subcategory: the parent product category and remaining text are used.
- Per-product errors: the row is marked failed and the rest of the batch continues.
- Interrupted jobs: records stuck in `processing` are reset to `pending`; completed products remain untouched.

## Batch scaling

The catalogue is inserted with `bulk_create(..., batch_size=500)`. The worker claims pending products in chunks and writes progress after each row. The schema has indexes for batch/status and batch/review queries.

For multiple production workers, MariaDB/PostgreSQL should use `SELECT ... FOR UPDATE SKIP LOCKED`; Celery with Redis or RabbitMQ can call the same `process_batch` service. Taxonomy vectors should be cached and product texts vectorized in chunks. External AI calls should be batched, rate-limited, retried with exponential backoff, and protected by idempotency keys.

Ten thousand sequential two-second API requests take about 5 hours 33 minutes. Ten workers reduce the theoretical request time to about 33 minutes, subject to provider limits. Batching 20 products per request would reduce the call count from 10,000 to 500.

## MariaDB

Start the included database service:

```bash
docker compose up -d
```

## Tests

```bash
python manage.py test
```

The tests cover classification, missing descriptions, resumable processing, and progress reporting.

## Optional taxonomy web importer

Beautiful Soup can help parse a static taxonomy webpage or downloaded HTML. Selenium should be used only if the source renders taxonomy data exclusively through JavaScript. Neither is required for normal catalogue classification, and scraping must comply with the source's terms and rate limits. A versioned official file or repository export is more reliable than live scraping.

## Production improvements

- Import the full official Shopify taxonomy and attribute definitions.
- Cache fitted taxonomy vectors instead of fitting during each product classification.
- Add sentence-transformer text embeddings and optional CLIP image embeddings.
- Validate remote images in background tasks with strict timeouts, MIME checks, size limits, and SSRF protection.
- Add authentication and reviewer roles.
- Add Celery/Redis, multi-worker locking, monitoring, structured logs, and dead-letter handling.
- Calibrate confidence thresholds on labelled data and report top-1/top-3 accuracy by category.
- Add object storage, antivirus scanning, retention rules, and audit export.

## Assumptions and limitations

- The included taxonomy is a representative furniture subset for a working assessment prototype, not the complete official Shopify taxonomy.
- Confidence is a ranking confidence useful for review routing, not a statistically calibrated probability.
- Images are displayed but are not downloaded or analysed in the baseline. This avoids insecure arbitrary URL fetching during evaluation.
- The immediate browser action is capped at 250 rows to avoid request timeouts. Use the worker for all 4,999 products.



