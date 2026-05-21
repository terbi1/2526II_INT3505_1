from flask import Blueprint, request, jsonify
from week11.models.database import products_db

query_bp = Blueprint('query', __name__)

@query_bp.route('/products', methods=['GET'])
def search_products_get():
    category  = request.args.get('category')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    min_stock = request.args.get('min_stock', type=int)
    keyword   = request.args.get('q')
    sort_by   = request.args.get('sort', 'name')
    order     = request.args.get('order', 'asc')
    fields    = request.args.get('fields')

    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))

    results = list(products_db.values())

    if category:
        results = [p for p in results if p['category'] == category]

    if min_price is not None:
        results = [p for p in results if p['price'] >= min_price]

    if max_price is not None:
        results = [p for p in results if p['price'] <= max_price]

    if min_stock is not None:
        results = [p for p in results if p['stock'] >= min_stock]

    if keyword:
        kw = keyword.lower()
        results = [p for p in results
                   if kw in p['name'].lower() or kw in p['category'].lower()]

    allowed_sort = {'name', 'price', 'stock', 'rating'}
    if sort_by not in allowed_sort:
        return jsonify({
            "error": "invalid_sort",
            "message": f"Chỉ được sort theo: {allowed_sort}"
        }), 400

    results.sort(key=lambda p: p.get(sort_by, 0), reverse=(order == 'desc'))

    total  = len(results)
    start  = (page - 1) * per_page
    items  = results[start: start + per_page]

    if fields:
        wanted = set(fields.split(','))
        items = [{k: v for k, v in p.items() if k in wanted} for p in items]

    return jsonify({
        "data": items,
        "meta": {
            "total":       total,
            "page":        page,
            "per_page":    per_page,
            "total_pages": (total + per_page - 1) // per_page,
            "filters_applied": {
                "category":  category,
                "min_price": min_price,
                "max_price": max_price,
                "keyword":   keyword,
            }
        }
    })

@query_bp.route('/products/advanced', methods=['POST'])
def search_products_post():
    body = request.get_json() or {}

    filters    = body.get('filters', {})
    sorts      = body.get('sort', [])
    pagination = body.get('pagination', {"page": 1, "per_page": 10})
    fields     = body.get('fields')

    results = list(products_db.values())

    results = _apply_filter_node(results, filters)

    for sort_spec in reversed(sorts):
        field = sort_spec.get('field', 'name')
        desc  = sort_spec.get('order', 'asc') == 'desc'
        results.sort(key=lambda p: p.get(field, 0), reverse=desc)

    page     = pagination.get('page', 1)
    per_page = pagination.get('per_page', 10)
    total    = len(results)
    start    = (page - 1) * per_page
    items    = results[start: start + per_page]

    if fields:
        wanted = set(fields)
        items = [{k: v for k, v in p.items() if k in wanted} for p in items]

    return jsonify({
        "data": items,
        "meta": {"total": total, "page": page, "per_page": per_page}
    })


def _apply_filter_node(items, node):
    if not node:
        return items

    if 'AND' in node:
        for sub in node['AND']:
            items = _apply_filter_node(items, sub)
        return items

    if 'OR' in node:
        result_set = {}
        for sub in node['OR']:
            for p in _apply_filter_node(list(items), sub):
                result_set[p['id']] = p
        return list(result_set.values())

    field = node.get('field')
    op    = node.get('op')
    value = node.get('value')

    if not all([field, op, value is not None]):
        return items

    ops = {
        'eq':       lambda a, b: a == b,
        'ne':       lambda a, b: a != b,
        'gt':       lambda a, b: a > b,
        'gte':      lambda a, b: a >= b,
        'lt':       lambda a, b: a < b,
        'lte':      lambda a, b: a <= b,
        'contains': lambda a, b: b.lower() in str(a).lower(),
    }

    fn = ops.get(op)
    if not fn:
        return items

    return [p for p in items if field in p and fn(p[field], value)]

@query_bp.route('/products/cursor', methods=['GET'])
def cursor_pagination():
    after = request.args.get('after')
    limit = int(request.args.get('limit', 3))

    all_products = list(products_db.values())

    if after:
        try:
            cursor_idx = next(i for i, p in enumerate(all_products)
                              if p['id'] == after)
            all_products = all_products[cursor_idx + 1:]
        except StopIteration:
            return jsonify({"error": "invalid_cursor"}), 400

    items    = all_products[:limit]
    has_more = len(all_products) > limit

    return jsonify({
        "data":     items,
        "has_more": has_more,
        "next_cursor": items[-1]['id'] if has_more and items else None,
        "explanation": (
            "Cursor pagination: dùng ID của item cuối làm con trỏ. "
            "Không bị lệch khi có insert/delete giữa các trang."
        )
    })
