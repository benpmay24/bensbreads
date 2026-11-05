from django.urls import path

from . import views

urlpatterns = [
    path('', views.menu, name='order_menu'),
    path('item/<int:pk>/', views.product_detail, name='order_product'),
    path('item/new/', views.product_create, name='order_product_create'),
    path('item/<int:pk>/edit/', views.product_edit, name='order_product_edit'),
    path('item/<int:pk>/delete/', views.product_delete, name='order_product_delete'),
    path('cart/', views.cart_view, name='order_cart'),
    path('cart/add/<int:pk>/', views.cart_add, name='order_cart_add'),
    path('checkout/', views.checkout, name='order_checkout'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('my-orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('manage/', views.manage_orders, name='manage_orders'),
    path('manage/<int:pk>/status/', views.update_order_status, name='order_update_status'),
]
