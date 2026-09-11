from django.contrib import admin
from .models import ClassificationAudit, ImportBatch, Product, TaxonomyCategory

@admin.register(TaxonomyCategory)
class TaxonomyCategoryAdmin(admin.ModelAdmin):
    list_display = ("taxonomy_id", "full_path", "is_active")
    search_fields = ("taxonomy_id", "name", "full_path", "keywords")

@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "status", "processed_products", "total_products", "created_at")

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("external_id", "title", "predicted_category", "confidence", "requires_review", "approved")
    list_filter = ("processing_status", "requires_review", "approved")
    search_fields = ("external_id", "title", "model_number")

admin.site.register(ClassificationAudit)
