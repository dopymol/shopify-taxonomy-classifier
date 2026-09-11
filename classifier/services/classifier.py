import re
from collections import Counter
from django.conf import settings
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from classifier.models import TaxonomyCategory

TOKEN_RE = re.compile(r"[a-z0-9]+")
COLORS = {"black","white","gray","grey","red","blue","green","yellow","brown","beige","pink","orange","purple","navy","teal","gold","silver","natural","walnut","espresso"}
MATERIALS = {"wood","metal","steel","aluminum","glass","leather","fabric","polyester","velvet","linen","marble","plastic","rattan","wicker","foam","acrylic","ceramic"}

def normalized_text(product):

    return " ".join(filter(None, [product.title, product.title, product.title,
        product.product_type, product.product_type, product.description, product.brand,
        product.material, product.color, str(product.raw_data.get("Bullets", "")), str(product.raw_data.get("Set Includes", ""))]))

def detect_attributes(product, category):
    text = normalized_text(product).lower()
    tokens = set(TOKEN_RE.findall(text))
    result = {}
    color = next((c for c in [product.color.lower()] if c), "")
    if color:
        result["color"] = product.color
    else:
        found = sorted(tokens & COLORS)
        if found: result["color"] = found[0].title()
    if product.material:
        result["material"] = product.material
    else:
        found = sorted(tokens & MATERIALS)
        if found: result["material"] = found[0].title()
    for attr in category.attributes:
        key = attr.get("name", "").lower().replace(" ", "_")
        if key and key not in result:
            values = attr.get("values", [])
            match = next((v for v in values if str(v).lower() in text), None)
            if match: result[key] = match
    if product.raw_data.get("Assembly Required"):
        result["assembly_required"] = product.raw_data["Assembly Required"]
    return result

def classify_product(product):
    categories = list(TaxonomyCategory.objects.filter(is_active=True))
    if not categories:
        raise RuntimeError("No taxonomy categories are loaded. Run seed_taxonomy first.")
    product_text = normalized_text(product)
    if not product_text.strip():
        product.requires_review = True
        product.processing_status = product.Status.FAILED
        product.error_message = "No usable product information"
        product.processed_at = timezone.now()
        product.save()
        return product
    category_docs = [" ".join([c.full_path, c.name, c.keywords]) for c in categories]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
    matrix = vectorizer.fit_transform(category_docs + [product_text])
    semantic = cosine_similarity(matrix[-1], matrix[:-1]).ravel()

    p_tokens = Counter(TOKEN_RE.findall(product_text.lower()))
    title_tokens = set(TOKEN_RE.findall(product.title.lower()))
    scores = []
    for i, category in enumerate(categories):
        c_tokens = set(TOKEN_RE.findall((category.name + " " + category.keywords).lower()))
        keyword_hits = sum(min(p_tokens[t], 2) for t in c_tokens)
        keyword_score = min(keyword_hits / max(3, len(c_tokens) * 0.25), 1.0)
        title_hits = len(title_tokens & c_tokens)
        title_score = min(title_hits / 2, 1.0)
        score = float(0.60 * semantic[i] + 0.22 * keyword_score + 0.18 * title_score)
        scores.append((score, category))
    scores.sort(key=lambda x: x[0], reverse=True)
    top = scores[:3]
    best_score, best = top[0]
    margin = best_score - (top[1][0] if len(top) > 1 else 0)
    evidence_bonus = 0.10 if product.description else 0
    type_bonus = 0.10 if product.product_type and best.name.lower() in product.product_type.lower() else 0
    confidence = min(0.99, max(0.05, best_score + evidence_bonus + type_bonus + min(margin * 1.5, 0.18)))
    if not product.description: confidence *= 0.88
    product.predicted_category = best
    product.confidence = round(confidence, 4)
    product.alternatives = [{"taxonomy_id": c.taxonomy_id, "category": c.full_path, "score": round(float(s), 4)} for s, c in top[1:]]
    product.detected_attributes = detect_attributes(product, best)
    product.requires_review = confidence < settings.CLASSIFICATION_REVIEW_THRESHOLD or margin < 0.025
    product.processing_status = product.Status.COMPLETED
    product.error_message = ""
    product.processed_at = timezone.now()
    product.save(update_fields=["predicted_category", "confidence", "alternatives", "detected_attributes", "requires_review", "processing_status", "error_message", "processed_at"])
    return product
