from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .cart import Cart
from .forms import AddToCartForm, CheckoutForm, ProductForm
from .models import MAX_QUANTITY, Order, OrderItem, Product, ProductImage


def is_admin(user):
    return user.is_superuser


def is_staff_member(user):
    return user.is_staff or user.is_superuser


def _redirect_back(request, fallback):
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect(fallback)


# ---------- Browsing ----------

def menu(request):
    products = Product.objects.prefetch_related('images')
    if not is_admin(request.user):
        products = products.filter(is_available=True)
    by_category = {}
    for product in products:
        by_category.setdefault(product.category, []).append(product)
    # One section per category, in the order categories are defined; empty ones are skipped.
    sections = [
        (value, label, by_category[value])
        for value, label in Product.CATEGORY_CHOICES
        if value in by_category
    ]
    return render(request, 'orders/menu.html', {'sections': sections})


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.prefetch_related('images'), pk=pk)
    if not product.is_available and not is_admin(request.user):
        raise Http404
    return render(request, 'orders/product_detail.html', {
        'product': product,
        'form': AddToCartForm(),
        'max_quantity': MAX_QUANTITY,
    })


# ---------- Cart ----------

@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_available=True)
    form = AddToCartForm(request.POST)
    if form.is_valid():
        Cart(request).add(product, form.cleaned_data['quantity'])
        messages.success(request, f'Added {form.cleaned_data["quantity"]} × {product.name} to your cart.')
    else:
        messages.error(request, f'Please choose a quantity between 1 and {MAX_QUANTITY}.')
    return _redirect_back(request, 'order_menu')


def cart_view(request):
    cart = Cart(request)
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('qty_'):
                try:
                    cart.set(int(key[4:]), int(value))
                except ValueError:
                    pass
        if 'remove' in request.POST:
            cart.remove(request.POST['remove'])
        return redirect('order_cart')

    lines = cart.lines()
    return render(request, 'orders/cart.html', {
        'lines': lines,
        'total_items': sum(q for _, q in lines),
        'checkout_form': CheckoutForm(),
        'max_quantity': MAX_QUANTITY,
    })


@require_POST
@login_required
def checkout(request):
    cart = Cart(request)
    lines = cart.lines()
    if not lines:
        messages.error(request, 'Your cart is empty.')
        return redirect('order_cart')
    form = CheckoutForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Please shorten your notes and try again.')
        return redirect('order_cart')

    with transaction.atomic():
        order = Order.objects.create(user=request.user, notes=form.cleaned_data['notes'])
        OrderItem.objects.bulk_create([
            OrderItem(order=order, product=product, product_name=product.name, quantity=quantity)
            for product, quantity in lines
        ])
    cart.clear()
    messages.success(request, f'Thanks! Your order #{order.pk} has been placed.')
    return redirect('order_detail', pk=order.pk)


# ---------- Customer orders ----------

@login_required
def my_orders(request):
    orders = request.user.orders.prefetch_related('items')
    return render(request, 'orders/my_orders.html', {'orders': orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related('items__product__images'), pk=pk)
    if order.user != request.user and not is_staff_member(request.user):
        raise Http404
    statuses = [value for value, _ in Order.STATUS_CHOICES]
    current = statuses.index(order.status)
    status_steps = [
        (label, 'current' if i == current else 'done' if i < current else '')
        for i, (_, label) in enumerate(Order.STATUS_CHOICES)
    ]
    return render(request, 'orders/order_detail.html', {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
        'status_steps': status_steps,
    })


# ---------- Staff: manage orders ----------

@user_passes_test(is_staff_member)
def manage_orders(request):
    status = request.GET.get('status', 'open')
    orders = Order.objects.select_related('user').prefetch_related('items')
    if status == 'open':
        orders = orders.exclude(status=Order.STATUS_COMPLETED)
    elif status in dict(Order.STATUS_CHOICES):
        orders = orders.filter(status=status)
    else:
        status = 'all'
    counts = dict(Order.objects.values_list('status').annotate(n=Count('id')))
    return render(request, 'orders/manage_orders.html', {
        'orders': orders,
        'status_filter': status,
        'status_choices': Order.STATUS_CHOICES,
        'status_tabs': [(value, label, counts.get(value, 0)) for value, label in Order.STATUS_CHOICES],
        'open_count': counts.get(Order.STATUS_PLACED, 0) + counts.get(Order.STATUS_IN_PROGRESS, 0),
        'all_count': sum(counts.values()),
    })


@require_POST
@user_passes_test(is_staff_member)
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    status = request.POST.get('status')
    if status in dict(Order.STATUS_CHOICES):
        order.status = status
        order.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'Order #{order.pk} marked "{order.get_status_display()}".')
    else:
        messages.error(request, 'Unknown status.')
    return _redirect_back(request, 'manage_orders')


# ---------- Admin: manage products ----------

def _save_product(form):
    with transaction.atomic():
        product = form.save()
        remove_ids = form.cleaned_data.get('remove_images') or []
        for image in product.images.filter(pk__in=remove_ids):
            image.delete()
        start = (product.images.order_by('-position').values_list('position', flat=True).first() or 0) + 1
        for offset, upload in enumerate(form.cleaned_data.get('new_images') or []):
            ProductImage.objects.create(product=product, image=upload, position=start + offset)
    return product


@user_passes_test(is_admin)
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        product = _save_product(form)
        messages.success(request, f'"{product.name}" was added to the order page.')
        return redirect('order_product', pk=product.pk)
    return render(request, 'orders/product_form.html', {'form': form, 'is_edit': False})


@user_passes_test(is_admin)
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        product = _save_product(form)
        messages.success(request, f'"{product.name}" was updated.')
        return redirect('order_product', pk=product.pk)
    return render(request, 'orders/product_form.html', {'form': form, 'is_edit': True, 'product': product})


@require_POST
@user_passes_test(is_admin)
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    product.delete()
    messages.success(request, f'"{name}" was deleted. Past orders still list it by name.')
    return redirect('order_menu')
