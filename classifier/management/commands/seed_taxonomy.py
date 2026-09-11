import json
from pathlib import Path
from django.core.management.base import BaseCommand
from classifier.models import TaxonomyCategory

class Command(BaseCommand):
    help = "Load the bundled furniture-focused Shopify taxonomy subset"

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(Path(__file__).resolve().parents[3] / "data" / "taxonomy_seed.json"))

    def handle(self, *args, **options):
        rows = json.loads(Path(options["file"]).read_text(encoding="utf-8"))
        for row in rows:
            TaxonomyCategory.objects.update_or_create(taxonomy_id=row["taxonomy_id"], defaults=row)
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(rows)} taxonomy categories."))
