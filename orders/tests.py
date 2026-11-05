import io
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Order, Product, ProductImage

MEDIA_ROOT = tempfile.mkdtemp()


def make_image(name='photo.jpg'):
    buf = io.BytesIO()
    Image.new('RGB', (8, 8), (200, 150, 80)).save(buf, 'JPEG')
    return SimpleUploadedFile(name, buf.getvalue(), content_type='image/jpeg')


@override_settings(MEDIA_ROOT=MEDIA_ROOT, SITE_ROLE='main', ROOT_URLCONF='bensbreads.urls')
class OrderTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.customer = User.objects.create_user('cust', 'cust@example.com', 'pw')
        self.other = User.objects.create_user('other', 'other@example.com', 'pw')
        self.staff = User.objects.create_user('staff', 'staff@example.com', 'pw', is_staff=True)
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'pw')
        self.loaf = Product.objects.create(name='Sourdough', description='Tangy', category='bread')
        ProductImage.objects.create(product=self.loaf, image=make_image())
        self.croissant = Product.objects.create(name='Croissant', description='Flaky', category='viennoiserie')
        self.hidden = Product.objects.create(name='Secret Loaf', description='Shh', category='other', is_available=False)

    def add(self, product, qty):
        return self.client.post(reverse('order_cart_add', args=[product.pk]), {'quantity': qty})


class BrowsingTests(OrderTestCase):
    def test_menu_shows_available_products_in_category_sections(self):
        r = self.client.get(reverse('order_menu'))
        html = r.content.decode()
        self.assertContains(r, 'Sourdough')
        self.assertContains(r, 'Croissant')
        self.assertNotContains(r, 'Secret Loaf')
        # Sections appear in category order, each with its own products; empty "Other" is omitted.
        self.assertLess(html.index('id="section-bread"'), html.index('Sourdough'))
        self.assertLess(html.index('Sourdough'), html.index('id="section-viennoiserie"'))
        self.assertLess(html.index('id="section-viennoiserie"'), html.index('Croissant'))
        self.assertNotIn('id="section-other"', html)

    def test_product_detail_links_from_card(self):
        r = self.client.get(reverse('order_menu'))
        self.assertContains(r, reverse('order_product', args=[self.loaf.pk]))
        r = self.client.get(reverse('order_product', args=[self.loaf.pk]))
        self.assertContains(r, 'Tangy')
        self.assertContains(r, 'Add to cart')

    def test_hidden_product_is_404_for_customers_but_visible_to_admin(self):
        self.assertEqual(self.client.get(reverse('order_product', args=[self.hidden.pk])).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('order_product', args=[self.hidden.pk])).status_code, 200)
        self.assertContains(self.client.get(reverse('order_menu')), 'Secret Loaf')


class CartAndCheckoutTests(OrderTestCase):
    def test_anonymous_can_build_cart_but_must_log_in_to_order(self):
        self.add(self.loaf, 2)
        self.add(self.loaf, 1)
        self.add(self.croissant, 4)
        r = self.client.get(reverse('order_cart'))
        self.assertContains(r, 'name="qty_%d" value="3"' % self.loaf.pk)
        self.assertContains(r, 'Log in to place order')
        r = self.client.post(reverse('order_checkout'))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r['Location'].startswith('/login/'))
        self.assertEqual(Order.objects.count(), 0)

    def test_cart_survives_login_and_order_is_placed_with_quantities(self):
        self.add(self.loaf, 3)
        self.add(self.croissant, 6)
        self.client.post(reverse('login'), {'username': 'cust', 'password': 'pw'})
        r = self.client.post(reverse('order_checkout'), {'notes': 'Pickup Saturday'})
        order = Order.objects.get()
        self.assertRedirects(r, reverse('order_detail', args=[order.pk]))
        self.assertEqual(order.user, self.customer)
        self.assertEqual(order.status, Order.STATUS_PLACED)
        self.assertEqual(order.notes, 'Pickup Saturday')
        self.assertEqual(
            sorted((i.product_name, i.quantity) for i in order.items.all()),
            [('Croissant', 6), ('Sourdough', 3)],
        )
        # Cart is emptied after ordering.
        self.assertContains(self.client.get(reverse('order_cart')), 'Your cart is empty')

    def test_cart_update_and_remove(self):
        self.add(self.loaf, 2)
        self.add(self.croissant, 1)
        self.client.post(reverse('order_cart'), {f'qty_{self.loaf.pk}': '5', f'qty_{self.croissant.pk}': '1'})
        self.client.post(reverse('order_cart'), {f'qty_{self.loaf.pk}': '5', 'remove': str(self.croissant.pk)})
        self.client.force_login(self.customer)
        self.client.post(reverse('order_checkout'))
        self.assertEqual([(i.product_name, i.quantity) for i in Order.objects.get().items.all()], [('Sourdough', 5)])

    def test_quantity_limits(self):
        self.assertEqual(self.add(self.loaf, 0).status_code, 302)
        self.add(self.loaf, 500)
        self.assertNotIn('cart', self.client.session)
        self.add(self.loaf, 60)
        self.add(self.loaf, 60)  # capped at 99
        self.assertEqual(self.client.session['cart'][str(self.loaf.pk)], 99)

    def test_hidden_products_cannot_be_added_and_drop_out_of_cart(self):
        self.assertEqual(self.add(self.hidden, 1).status_code, 404)
        self.add(self.loaf, 1)
        self.loaf.is_available = False
        self.loaf.save()
        self.client.force_login(self.customer)
        self.client.post(reverse('order_checkout'))
        self.assertEqual(Order.objects.count(), 0)

    def test_order_survives_product_deletion(self):
        self.client.force_login(self.customer)
        self.add(self.loaf, 2)
        self.client.post(reverse('order_checkout'))
        self.loaf.delete()
        r = self.client.get(reverse('my_orders'))
        self.assertContains(r, '2 × Sourdough')


class OrderHistoryTests(OrderTestCase):
    def setUp(self):
        super().setUp()
        self.order = Order.objects.create(user=self.customer)
        self.order.items.create(product=self.loaf, product_name='Sourdough', quantity=2)

    def test_customer_sees_own_orders_with_status(self):
        self.client.force_login(self.customer)
        r = self.client.get(reverse('my_orders'))
        self.assertContains(r, f'Order #{self.order.pk}')
        self.assertContains(r, 'Order placed')
        self.assertEqual(self.client.get(reverse('order_detail', args=[self.order.pk])).status_code, 200)

    def test_other_customers_cannot_see_the_order(self):
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse('my_orders')), f'Order #{self.order.pk}')
        self.assertEqual(self.client.get(reverse('order_detail', args=[self.order.pk])).status_code, 404)

    def test_my_orders_requires_login(self):
        r = self.client.get(reverse('my_orders'))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r['Location'].startswith('/login/'))


class StaffTests(OrderTestCase):
    def setUp(self):
        super().setUp()
        self.order = Order.objects.create(user=self.customer)
        self.order.items.create(product=self.loaf, product_name='Sourdough', quantity=2)

    def test_staff_and_admin_can_manage_and_update_status(self):
        for user, status in [(self.staff, Order.STATUS_IN_PROGRESS), (self.admin, Order.STATUS_COMPLETED)]:
            self.client.force_login(user)
            self.assertContains(self.client.get(reverse('manage_orders') + '?status=all'), f'Order #{self.order.pk}')
            self.client.post(reverse('order_update_status', args=[self.order.pk]), {'status': status})
            self.order.refresh_from_db()
            self.assertEqual(self.order.status, status)
        # Completed orders drop out of the default "open" view.
        card_link = f'href="{reverse("order_detail", args=[self.order.pk])}"'
        self.assertNotContains(self.client.get(reverse('manage_orders')), card_link)
        self.assertContains(self.client.get(reverse('manage_orders') + '?status=completed'), card_link)
        # The customer sees the new status.
        self.client.force_login(self.customer)
        self.assertContains(self.client.get(reverse('my_orders')), 'Completed')

    def test_customers_cannot_manage_orders(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse('manage_orders')).status_code, 302)
        self.client.post(reverse('order_update_status', args=[self.order.pk]), {'status': Order.STATUS_COMPLETED})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PLACED)

    def test_invalid_status_is_rejected(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('order_update_status', args=[self.order.pk]), {'status': 'shipped'})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PLACED)


class ProductAdminTests(OrderTestCase):
    def test_admin_creates_product_with_multiple_photos(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('order_product_create'), {
            'name': 'Pain au Chocolat', 'description': 'Buttery', 'category': 'viennoiserie',
            'is_available': 'on', 'new_images': [make_image('a.jpg'), make_image('b.jpg')],
        })
        product = Product.objects.get(name='Pain au Chocolat')
        self.assertRedirects(r, reverse('order_product', args=[product.pk]))
        self.assertEqual(product.category, 'viennoiserie')
        self.assertEqual(product.images.count(), 2)

    def test_photo_is_required(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse('order_product_create'), {'name': 'X', 'description': 'Y', 'category': 'bread'})
        self.assertContains(r, 'Add at least one photo.')
        self.assertFalse(Product.objects.filter(name='X').exists())

    def test_edit_can_add_and_remove_photos_but_not_remove_all(self):
        self.client.force_login(self.admin)
        first = self.loaf.images.get()
        url = reverse('order_product_edit', args=[self.loaf.pk])
        base = {'name': 'Sourdough', 'description': 'Tangy', 'category': 'bread', 'is_available': 'on'}
        r = self.client.post(url, {**base, 'remove_images': [first.pk]})
        self.assertContains(r, 'Add at least one photo.')
        self.client.post(url, {**base, 'remove_images': [first.pk], 'new_images': [make_image('new.jpg')]})
        self.assertEqual(self.loaf.images.count(), 1)
        self.assertNotEqual(self.loaf.images.get().pk, first.pk)

    def test_staff_who_are_not_admins_cannot_manage_products(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('order_product_create')).status_code, 302)
        self.client.post(reverse('order_product_delete', args=[self.loaf.pk]))
        self.assertTrue(Product.objects.filter(pk=self.loaf.pk).exists())

    def test_admin_can_delete_product(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('order_product_delete', args=[self.loaf.pk]))
        self.assertFalse(Product.objects.filter(pk=self.loaf.pk).exists())
