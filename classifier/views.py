import csv
import json
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import ReviewForm, UploadCatalogueForm
from .models import ClassificationAudit, ImportBatch, Product, TaxonomyCategory
from .services.batches import process_batch, reset_interrupted
from .services.importer import import_catalogue

def dashboard(request):
    batches = ImportBatch.objects.annotate(review_count=Count("products", filter=Q(products__requires_review=True))).order_by("-created_at")[:20]
    return render(request, "classifier/dashboard.html", {"batches": batches})

def upload_catalogue(request):
    form = UploadCatalogueForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        f = form.cleaned_data["catalogue"]
        batch = ImportBatch.objects.create(original_filename=f.name, source_file=f)
        try:
            import_catalogue(batch)
            if form.cleaned_data["process_now"]:
                process_batch(batch.id, limit=250)
                messages.success(request, "Catalogue imported. Up to 250 products were classified for the live demonstration.")
            else:
                messages.success(request, "Catalogue imported. Run the worker command to process it in the background.")
            return redirect("batch_detail", pk=batch.pk)
        except Exception as exc:
            batch.status = ImportBatch.Status.FAILED
            batch.error_message = str(exc)
            batch.save(update_fields=["status", "error_message"])
            messages.error(request, f"Import failed: {exc}")
    return render(request, "classifier/upload.html", {"form": form})

def batch_detail(request, pk):
    batch = get_object_or_404(ImportBatch, pk=pk)
    products = batch.products.select_related("predicted_category").all().order_by("id")
    status = request.GET.get("status")
    if status == "review": products = products.filter(requires_review=True)
    elif status == "approved": products = products.filter(approved=True)
    elif status == "failed": products = products.filter(processing_status=Product.Status.FAILED)
    query = request.GET.get("q", "").strip()
    if query: products = products.filter(Q(title__icontains=query) | Q(external_id__icontains=query))
    page = Paginator(products, 50).get_page(request.GET.get("page"))
    return render(request, "classifier/batch_detail.html", {"batch": batch, "page": page, "status_filter": status or "", "query": query})

def product_review(request, pk):
    product = get_object_or_404(Product.objects.select_related("predicted_category", "batch"), pk=pk)
    form = ReviewForm(request.POST or None, initial={"category": product.predicted_category, "approved": product.approved})
    if request.method == "POST" and form.is_valid():
        old = product.predicted_category.full_path if product.predicted_category else ""
        category = form.cleaned_data["category"]
        product.predicted_category = category
        product.approved = form.cleaned_data["approved"]
        product.requires_review = not product.approved
        product.save(update_fields=["predicted_category", "approved", "requires_review"])
        ClassificationAudit.objects.create(product=product, action="manual_review", old_category=old, new_category=category.full_path, note=form.cleaned_data["note"])
        messages.success(request, "Review saved.")
        return redirect("batch_detail", pk=product.batch_id)
    return render(request, "classifier/product_review.html", {"product": product, "form": form})

@require_POST
def process_batch_now(request, pk):
    batch = get_object_or_404(ImportBatch, pk=pk)
    reset_interrupted(batch)
    count = process_batch(batch.id, limit=250)
    messages.success(request, f"Processed {count} product(s). Use the worker command for the complete catalogue.")
    return redirect("batch_detail", pk=pk)

def batch_progress(request, pk):
    batch = get_object_or_404(ImportBatch, pk=pk)
    return JsonResponse({"id": batch.id, "status": batch.status, "total": batch.total_products,
        "processed": batch.processed_products, "successful": batch.successful_products,
        "failed": batch.failed_products, "percentage": batch.percentage,
        "review": batch.products.filter(requires_review=True).count()})

def products_api(request, pk):
    batch = get_object_or_404(ImportBatch, pk=pk)
    products = batch.products.select_related("predicted_category").order_by("id")[:500]
    return JsonResponse({"batch": batch.id, "count": batch.total_products, "results": [{
        "id": p.id, "external_id": p.external_id, "title": p.title,
        "category": p.predicted_category.full_path if p.predicted_category else None,
        "taxonomy_id": p.predicted_category.taxonomy_id if p.predicted_category else None,
        "confidence": p.confidence, "alternatives": p.alternatives, "attributes": p.detected_attributes,
        "requires_review": p.requires_review, "approved": p.approved, "status": p.processing_status,
    } for p in products]})

def export_results(request, pk):
    batch = get_object_or_404(ImportBatch, pk=pk)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="batch-{batch.id}-classified.csv"'
    writer = csv.writer(response)
    writer.writerow(["product_number", "product_name", "shopify_taxonomy_id", "shopify_category", "confidence", "alternative_categories", "attributes", "requires_review", "approved", "status", "error"])
    for p in batch.products.select_related("predicted_category").order_by("id").iterator(chunk_size=500):
        writer.writerow([p.external_id, p.title, p.predicted_category.taxonomy_id if p.predicted_category else "",
            p.predicted_category.full_path if p.predicted_category else "", p.confidence or "",
            json.dumps(p.alternatives), json.dumps(p.detected_attributes), p.requires_review, p.approved, p.processing_status, p.error_message])
    return response
