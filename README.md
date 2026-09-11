# Shopify Product Taxonomy Classifier

This is a Django-based prototype for classifying product catalogues into suitable Shopify Product Taxonomy categories. It was developed using the supplied furniture product catalogue as part of a Python developer assignment.

The application reads product information from an Excel or CSV file, predicts a suitable category, extracts available attributes and marks uncertain results for manual review.

## Main features

- Upload product catalogues in Excel or CSV format
- Process products in batches
- Predict a suitable taxonomy category
- Display a confidence score
- Suggest alternative categories
- Detect available attributes such as colour and material
- Continue when descriptions, attributes or images are missing
- Mark uncertain predictions for manual review
- Allow a reviewer to correct and approve a category
- Track batch progress
- Resume processing without repeating completed products
- Export the final results as a CSV file

## Technologies used

- Python
- Django
- HTML, CSS and JavaScript
- SQLite
- Pandas and openpyxl
- Scikit-learn

SQLite is used because it makes the prototype easy to install and demonstrate locally. A production version could use MariaDB or PostgreSQL and a distributed background-task system.

## How classification works

The classifier combines the available product information, including the product title, description, category, subcategory, brand, colour, material, bullet points and set contents.

It compares this information with taxonomy category paths and keywords using TF-IDF, cosine similarity and keyword matching. The title and product type receive more importance because they usually give the clearest indication of what the product is.

The application saves the best category, its confidence score and two alternatives. A result is sent for manual review when its confidence is low or when the two best categories receive very similar scores.

## Project structure

```text
shopify-taxonomy-classifier/
├── classifier/
│   ├── management/        # Taxonomy and batch commands
│   ├── migrations/        # Database migrations
│   ├── services/          # Import, classification and batch logic
│   ├── admin.py
│   ├── forms.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── config/                # Django settings
├── data/
│   └── taxonomy_seed.json
├── sample_data/           # Optional anonymized sample
├── static/                # CSS
├── templates/             # HTML templates
├── .gitignore
├── manage.py
├── README.md
└── requirements.txt
```

## Setup on Windows

Python 3.11 or a newer supported version is recommended.

### 1. Create a virtual environment

Open PowerShell in the folder containing `manage.py`:

```powershell
py -3.11 -m venv venv
venv\Scripts\activate
```

### 2. Install the packages

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Prepare the database

```powershell
python manage.py migrate
```

### 4. Load the taxonomy categories

```powershell
python manage.py seed_taxonomy
```

### 5. Start the application

```powershell
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Using the application

1. Open the dashboard and select **Upload catalogue**.
2. Choose an `.xlsx` or `.csv` product file.
3. Select the immediate-processing option to classify the first 250 products during a quick demonstration.
4. Open the batch page to view predictions, confidence scores and progress.
5. Use **Needs review** to find uncertain classifications.
6. Open a product to change or approve its category.
7. Select **Export CSV** to download the final results.

The supplied company catalogue is not included in this public repository. It can be uploaded locally when demonstrating the application.

## Processing the complete catalogue

The immediate-processing option is limited to 250 products so that the browser request does not stay open for too long.

To process the complete catalogue, keep the development server running and open a second terminal. Activate the same environment and run:

```powershell
venv\Scripts\activate
python manage.py process_batches --watch
```

The worker processes pending products and saves each result separately. If it is stopped, running the same command again continues with the remaining products.

## Tests

Run the tests with:

```powershell
python manage.py test
```

The tests cover basic classification, missing descriptions, resumable processing and batch-progress calculation.

## Important URLs

| URL | Purpose |
| --- | --- |
| `/` | Batch dashboard |
| `/upload/` | Catalogue upload |
| `/batches/<id>/` | Classification results |
| `/batches/<id>/progress/` | Batch-progress API |
| `/batches/<id>/api/products/` | Product-results API |
| `/batches/<id>/export/` | CSV export |
| `/products/<id>/review/` | Manual review |

## Current limitations

- The included taxonomy is a furniture-focused subset prepared for the supplied catalogue. It is not the complete official Shopify taxonomy.
- Product images are displayed during review but are not currently used as classification inputs.
- Confidence is a ranking score used to identify uncertain products, not a calibrated probability.
- The prototype uses a local database and a single background worker.

For a production version, I would import the complete official taxonomy, add controlled image classification, test confidence using verified product labels and use a production database with managed background workers.

