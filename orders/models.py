import os
import uuid

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

MAX_QUANTITY = 99


def product_image_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'product_images/{uuid.uuid4().hex}{ext}'


class Product(models.Model):
    CATEGORY_CHOICES = [
        ('bread', 'Bread'),
        ('viennoiserie', 'Viennoiserie'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=120)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='bread')
    # Hidden products stay attached to past orders but can't be ordered.
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def cover_image(self):
        images = list(self.images.all())
        return images[0] if images else None


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to=product_image_upload_path)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f'Image for {self.product}'


@receiver(post_delete, sender=ProductImage)
def delete_product_image_file(sender, instance, **kwargs):
    # Runs for direct deletes and for cascades from Product; works with S3 and local storage.
    if instance.image:
        instance.image.delete(save=False)


class Order(models.Model):
    STATUS_PLACED = 'placed'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_PLACED, 'Order placed'),
        (STATUS_IN_PROGRESS, 'In progress'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    user = models.ForeignKey(User, related_name='orders', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLACED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.pk} ({self.user})'

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', null=True, blank=True, on_delete=models.SET_NULL)
    # Snapshot so past orders still read correctly if the product is renamed or deleted.
    product_name = models.CharField(max_length=120)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(MAX_QUANTITY)])

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity} × {self.product_name}'
