import math
from pathlib import Path
import pandas as pd
from django.db import transaction
from classifier.models import Product

ALIASES = {
    "external_id": ["Product Number", "product_number", "id", "sku"],
    "model_number": ["Model Number", "model_number", "model"],
    "title": ["Product Name", "title", "name"],
    "description": ["Product Description", "Product Description ", "description"],
    "category": ["Product Category", "product_category", "category"],
    "subcategory": ["Product Sub Category", "product_sub_category", "subcategory", "product_type"],
    "brand": ["Brand", "brand", "vendor"],
    "color": ["Product Color", "Color Collection", "color"],
    "material": ["Materials", "material"],
}

def clean(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).replace("_x000D_", " ").strip()

def pick(row, key):
    for name in ALIASES[key]:
        if name in row and clean(row[name]):
            return clean(row[name])
    return ""

def load_dataframe(path):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype=object, keep_default_na=False)
    return pd.read_excel(path, dtype=object)

@transaction.atomic
def import_catalogue(batch):
    df = load_dataframe(batch.source_file.path)
    if len(df) > 100000:
        raise ValueError("This prototype accepts up to 100,000 products per batch.")
    records = []
    for index, row in df.iterrows():
        data = {str(k).strip(): clean(v) for k, v in row.to_dict().items()}
        external_id = pick(row, "external_id") or f"ROW-{index + 2}"
        title = pick(row, "title") or external_id
        images = [clean(row[c]) for c in df.columns if str(c).lower().startswith("image") and clean(row[c])]
        product_type = " > ".join(x for x in [pick(row, "category"), pick(row, "subcategory")] if x)
        records.append(Product(batch=batch, external_id=external_id[:255], model_number=pick(row, "model_number")[:255],
            title=title[:1000], description=pick(row, "description"), product_type=product_type[:500],
            brand=pick(row, "brand")[:255], color=pick(row, "color")[:255], material=pick(row, "material")[:500],
            image_urls=images, raw_data=data))
    Product.objects.bulk_create(records, batch_size=500)
    batch.total_products = len(records)
    batch.save(update_fields=["total_products"])
    return len(records)
