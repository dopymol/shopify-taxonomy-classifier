from django.db import models

class TaxonomyCategory(models.Model):
    taxonomy_id = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=255)
    full_path = models.CharField(max_length=1000, db_index=True)
    parent_path = models.CharField(max_length=1000, blank=True)
    keywords = models.TextField(blank=True)
    attributes = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["full_path"]

    def __str__(self):
        return self.full_path

class ImportBatch(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        COMPLETED_ERRORS = "completed_errors", "Completed with errors"
        FAILED = "failed", "Failed"

    original_filename = models.CharField(max_length=255)
    source_file = models.FileField(upload_to="catalogues/%Y/%m/%d/")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING, db_index=True)
    total_products = models.PositiveIntegerField(default=0)
    processed_products = models.PositiveIntegerField(default=0)
    successful_products = models.PositiveIntegerField(default=0)
    failed_products = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    @property
    def percentage(self):
        return round(self.processed_products * 100 / self.total_products, 1) if self.total_products else 0

class Product(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="products")
    external_id = models.CharField(max_length=255)
    model_number = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=1000)
    description = models.TextField(blank=True)
    product_type = models.CharField(max_length=500, blank=True)
    brand = models.CharField(max_length=255, blank=True)
    color = models.CharField(max_length=255, blank=True)
    material = models.CharField(max_length=500, blank=True)
    image_urls = models.JSONField(default=list, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    predicted_category = models.ForeignKey(TaxonomyCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name="predictions")
    confidence = models.FloatField(null=True, blank=True)
    alternatives = models.JSONField(default=list, blank=True)
    detected_attributes = models.JSONField(default=dict, blank=True)
    requires_review = models.BooleanField(default=False, db_index=True)
    approved = models.BooleanField(default=False, db_index=True)
    processing_status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    error_message = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["batch", "external_id"], name="unique_product_per_batch")]
        indexes = [models.Index(fields=["batch", "processing_status"]), models.Index(fields=["batch", "requires_review"])]

    def __str__(self):
        return self.title

class ClassificationAudit(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="audit_events")
    action = models.CharField(max_length=50)
    old_category = models.CharField(max_length=1000, blank=True)
    new_category = models.CharField(max_length=1000, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
