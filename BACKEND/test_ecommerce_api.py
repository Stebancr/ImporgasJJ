"""
Ecommerce API smoke-test — corrected field names.
Run inside the container: python test_ecommerce_api.py
"""
import urllib.request
import json
import sys

BASE = "http://localhost:8000"
PASS = 0
FAIL = 0

# ─────────────────────────────────────────────────────────────────────────────

def get(path):
    url = BASE + path
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}, e.code
    except Exception as e:
        return {"error": str(e)}, 0


def post(path, payload):
    url = BASE + path
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}, e.code
    except Exception as e:
        return {"error": str(e)}, 0


def delete(path):
    url = BASE + path
    req = urllib.request.Request(url, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return {}, resp.status
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}, e.code
    except Exception as e:
        return {"error": str(e)}, 0


def check(label, condition, info=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  OK  {label}" + (f"  [{info}]" if info else ""))
    else:
        FAIL += 1
        print(f"  XX  {label}" + (f"  [{info}]" if info else ""))

# ─────────────────────────────────────────────────────────────────────────────

print("\n-- 1. Brands --")
r, s = get("/brands")
check("GET /brands -> 200", s == 200, f"status={s}")
check("Response has pagination", all(k in r for k in ("data", "total", "page", "per_page", "total_pages")))
brands = r.get("data", [])
check("Has brands in DB", len(brands) >= 1, f"count={len(brands)}")
if brands:
    b = brands[0]
    check("Brand fields present",
          all(k in b for k in ("id", "name", "slug", "is_active")), str(list(b.keys())))

print("\n-- 2. Categories --")
r, s = get("/categories")
check("GET /categories -> 200", s == 200, f"status={s}")
cats = r.get("data", [])
check("Has categories in DB", len(cats) >= 1, f"count={len(cats)}")
if cats:
    c = cats[0]
    check("Category has product_count", "product_count" in c)
    check("Category has slug", "slug" in c)

print("\n-- 3. Products (list) --")
r, s = get("/products")
check("GET /products -> 200", s == 200, f"status={s}")
prods = r.get("data", [])
check("Has products in DB", len(prods) >= 1, f"count={len(prods)}")
if prods:
    p = prods[0]
    list_fields = ("id", "name", "slug", "price", "discount_percentage",
                   "category_id", "category_name", "brand_id", "brand_name",
                   "is_available", "is_featured", "rating", "reviews_count", "primary_image")
    check("ProductList has all required fields",
          all(k in p for k in list_fields),
          f"missing={[k for k in list_fields if k not in p]}")
    check("price is positive", float(p["price"]) > 0, f"price={p['price']}")
    check("discount_percentage is int", isinstance(p["discount_percentage"], int), f"val={p['discount_percentage']}")

print("\n-- 4. Products filters --")
r, s = get("/products?is_featured=true")
check("GET /products?is_featured=true -> 200", s == 200)
check("Featured products found", len(r.get("data", [])) >= 1, f"count={len(r.get('data', []))}")

r, s = get("/products?search=calentador")
check("GET /products?search=calentador -> 200", s == 200)
check("Search finds results", len(r.get("data", [])) >= 1, f"count={len(r.get('data', []))}")

print("\n-- 5. Product detail (by id) --")
if prods:
    pid = prods[0]["id"]
    r, s = get(f"/products/{pid}")
    check(f"GET /products/{pid} -> 200", s == 200, f"status={s}")
    detail = r.get("data", {})
    check("Detail wrapped in 'data'", "data" in r)
    check("Detail has images array", isinstance(detail.get("images"), list))
    check("Detail has specifications array", isinstance(detail.get("specifications"), list))
    check("Detail has nested brand object", isinstance(detail.get("brand"), dict))
    check("Detail has nested category object", isinstance(detail.get("category"), dict))

print("\n-- 6. Product by slug --")
if prods:
    slug = prods[0].get("slug", "")
    r, s = get(f"/products/slug/{slug}")
    check(f"GET /products/slug/{slug} -> 200", s == 200, f"status={s}")
    check("Slug detail wrapped in 'data'", "data" in r)

print("\n-- 7. Locations --")
r, s = get("/locations")
check("GET /locations -> 200", s == 200, f"status={s}")

print("\n-- 8. Spec Attributes --")
r, s = get("/spec-attributes")
check("GET /spec-attributes -> 200", s == 200, f"status={s}")

print("\n-- 9. Product CRUD --")
if brands and cats:
    brand_id = brands[0]["id"]
    cat_id   = cats[0]["id"]
    payload = {
        "name": "Producto de Prueba API",
        "description": "Descripcion de prueba para verificar el endpoint POST",
        "price": "299000.00",
        "original_price": "350000.00",
        "category": cat_id,
        "brand": brand_id,
        "is_available": True,
        "is_featured": False,
    }
    r, s = post("/products", payload)
    check("POST /products -> 201", s == 201, f"status={s}, resp={str(r)[:150]}")
    created_id = r.get("id") or r.get("data", {}).get("id")
    if created_id:
        r2, s2 = get(f"/products/{created_id}")
        check("Created product retrievable", s2 == 200)
        r3, s3 = delete(f"/products/{created_id}")
        check("DELETE /products/{id} -> 204", s3 == 204, f"status={s3}")

print("\n-- 10. Sub-resources --")
if prods:
    pid = prods[0]["id"]
    r, s = get(f"/products/{pid}/images")
    check(f"GET /products/{pid}/images -> 200", s == 200, f"status={s}")
    r, s = get(f"/products/{pid}/stock")
    check(f"GET /products/{pid}/stock -> 200", s == 200, f"status={s}")
    r, s = get(f"/products/{pid}/reviews")
    check(f"GET /products/{pid}/reviews -> 200", s == 200, f"status={s}")
    r, s = get(f"/products/{pid}/specs")
    check(f"GET /products/{pid}/specs -> 200", s == 200, f"status={s}")

# ─────────────────────────────────────────────────────────────────────────────
total = PASS + FAIL
print(f"\n{'='*55}")
print(f"Results: {PASS}/{total} passed  |  {FAIL} failed")
if FAIL:
    print("SOME TESTS FAILED")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")

