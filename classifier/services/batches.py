from django.db import transaction
from django.db.models import F
from django.utils import timezone
from classifier.models import ImportBatch, Product
from .classifier import classify_product

def claim_pending(batch, size=100):
    with transaction.atomic():
        ids = list(Product.objects.select_for_update().filter(batch=batch, processing_status=Product.Status.PENDING).values_list("id", flat=True)[:size])
        Product.objects.filter(id__in=ids).update(processing_status=Product.Status.PROCESSING)
    return ids

def process_batch(batch_id, chunk_size=100, limit=None):
    batch = ImportBatch.objects.get(pk=batch_id)
    if not batch.started_at:
        batch.started_at = timezone.now()
    batch.status = ImportBatch.Status.PROCESSING
    batch.error_message = ""
    batch.save(update_fields=["status", "started_at", "error_message"])
    processed_this_run = 0
    while True:
        ids = claim_pending(batch, min(chunk_size, limit - processed_this_run) if limit else chunk_size)
        if not ids: break
        for product in Product.objects.filter(id__in=ids).order_by("id"):
            try:
                classify_product(product)
                ImportBatch.objects.filter(pk=batch_id).update(processed_products=F("processed_products") + 1, successful_products=F("successful_products") + 1)
            except Exception as exc:
                Product.objects.filter(pk=product.pk).update(processing_status=Product.Status.FAILED, error_message=str(exc)[:2000], processed_at=timezone.now(), requires_review=True)
                ImportBatch.objects.filter(pk=batch_id).update(processed_products=F("processed_products") + 1, failed_products=F("failed_products") + 1)
            processed_this_run += 1
            if limit and processed_this_run >= limit: break
        if limit and processed_this_run >= limit: break
    batch.refresh_from_db()
    remaining = batch.products.filter(processing_status__in=[Product.Status.PENDING, Product.Status.PROCESSING]).exists()
    if not remaining:
        batch.status = ImportBatch.Status.COMPLETED_ERRORS if batch.failed_products else ImportBatch.Status.COMPLETED
        batch.completed_at = timezone.now()
        batch.save(update_fields=["status", "completed_at"])
    return processed_this_run

def reset_interrupted(batch):
    return batch.products.filter(processing_status=Product.Status.PROCESSING).update(processing_status=Product.Status.PENDING)
