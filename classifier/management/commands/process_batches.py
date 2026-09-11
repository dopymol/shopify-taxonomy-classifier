import time
from django.core.management.base import BaseCommand
from classifier.models import ImportBatch
from classifier.services.batches import process_batch, reset_interrupted

class Command(BaseCommand):
    help = "Process pending catalogues. Safe to restart; completed products are skipped."

    def add_arguments(self, parser):
        parser.add_argument("--batch", type=int)
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--chunk-size", type=int, default=100)

    def handle(self, *args, **options):
        while True:
            qs = ImportBatch.objects.exclude(status__in=[ImportBatch.Status.COMPLETED, ImportBatch.Status.COMPLETED_ERRORS, ImportBatch.Status.FAILED])
            if options["batch"]: qs = qs.filter(pk=options["batch"])
            batch = qs.order_by("created_at").first()
            if batch:
                reset_interrupted(batch)
                count = process_batch(batch.id, chunk_size=options["chunk_size"])
                self.stdout.write(self.style.SUCCESS(f"Batch {batch.id}: processed {count} products."))
            elif not options["watch"]:
                self.stdout.write("No pending batches.")
                return
            else:
                time.sleep(3)
