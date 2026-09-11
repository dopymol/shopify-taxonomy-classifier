from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("upload/", views.upload_catalogue, name="upload_catalogue"),
    path("batches/<int:pk>/", views.batch_detail, name="batch_detail"),
    path("batches/<int:pk>/process/", views.process_batch_now, name="process_batch_now"),
    path("batches/<int:pk>/progress/", views.batch_progress, name="batch_progress"),
    path("batches/<int:pk>/api/products/", views.products_api, name="products_api"),
    path("batches/<int:pk>/export/", views.export_results, name="export_results"),
    path("products/<int:pk>/review/", views.product_review, name="product_review"),
]
