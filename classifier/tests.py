from pathlib import Path
from tempfile import NamedTemporaryFile
import pandas as pd
from django.core.files import File
from django.core.management import call_command
from django.test import TestCase
from .models import ImportBatch, Product, TaxonomyCategory
from .services.batches import process_batch
from .services.classifier import classify_product
from .services.importer import import_catalogue

class ClassifierTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_taxonomy", verbosity=0)

    def test_sofa_classification(self):
        batch = ImportBatch.objects.create(original_filename="test.csv", source_file="catalogues/test.csv")
        p = Product.objects.create(batch=batch, external_id="S1", title="Empress upholstered leather sofa", description="Three seat tufted living room couch", product_type="Living Room > Sofas and Armchairs", color="White", material="Leather")
        classify_product(p)
        p.refresh_from_db()
        self.assertIn("Sofa", p.predicted_category.name)
        self.assertGreater(p.confidence, 0.5)
        self.assertEqual(p.detected_attributes["color"], "White")

    def test_missing_description_still_classifies(self):
        batch = ImportBatch.objects.create(original_filename="test.csv", source_file="catalogues/test.csv")
        p = Product.objects.create(batch=batch, external_id="L1", title="Modern arc floor lamp")
        classify_product(p)
        p.refresh_from_db()
        self.assertEqual(p.processing_status, Product.Status.COMPLETED)
        self.assertIsNotNone(p.predicted_category)

    def test_resume_skips_completed(self):
        batch = ImportBatch.objects.create(original_filename="test.csv", source_file="catalogues/test.csv", total_products=2)
        Product.objects.create(batch=batch, external_id="A", title="Office desk", processing_status=Product.Status.COMPLETED)
        Product.objects.create(batch=batch, external_id="B", title="Dining chair")
        count = process_batch(batch.id)
        self.assertEqual(count, 1)

    def test_progress_api(self):
        batch = ImportBatch.objects.create(original_filename="test.csv", source_file="catalogues/test.csv", total_products=10, processed_products=5)
        response = self.client.get(f"/batches/{batch.id}/progress/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["percentage"], 50.0)
