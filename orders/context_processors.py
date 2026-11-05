from .cart import SESSION_KEY


def cart(request):
    items = request.session.get(SESSION_KEY, {}) if hasattr(request, 'session') else {}
    return {'cart_count': sum(items.values())}
