"""Session-backed cart: works before login and survives logging in on this site."""
from .models import MAX_QUANTITY, Product

SESSION_KEY = 'cart'


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.items = {k: v for k, v in self.session.get(SESSION_KEY, {}).items()}

    def _save(self):
        self.session[SESSION_KEY] = self.items
        self.session.modified = True

    def add(self, product, quantity):
        key = str(product.pk)
        self.items[key] = min(self.items.get(key, 0) + quantity, MAX_QUANTITY)
        self._save()

    def set(self, product_id, quantity):
        key = str(product_id)
        if quantity <= 0:
            self.items.pop(key, None)
        else:
            self.items[key] = min(quantity, MAX_QUANTITY)
        self._save()

    def remove(self, product_id):
        self.set(product_id, 0)

    def clear(self):
        self.items = {}
        self._save()

    def lines(self):
        """[(product, quantity)] for products that still exist and are available.

        Anything no longer orderable is dropped from the cart.
        """
        products = Product.objects.filter(pk__in=self.items.keys(), is_available=True).prefetch_related('images')
        by_id = {str(p.pk): p for p in products}
        stale = [k for k in self.items if k not in by_id]
        if stale:
            for k in stale:
                self.items.pop(k)
            self._save()
        return [(by_id[k], q) for k, q in self.items.items()]

    def __len__(self):
        return sum(self.items.values())
