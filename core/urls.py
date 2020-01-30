from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('',views.ProductList.as_view(),name='product_list'),
    path('product/create/',views.ProductCreateView.as_view(),name='product_create'),
    path('product/<int:pk>/',views.ProductUpdateView.as_view(),name='product_update'),
    path('product/<int:pk>/delete',views.ProductDeleteView.as_view(),name='product_delete'),
    path('detail/<int:pk>/',views.product_detail,name='product_detail'),
    path('category/<category_slug>/',views.list_of_product_by_category,name='list_of_product_by_category'),
    path('checkout/',views.CheckoutView.as_view(),name='checkoutpage'),
    path('order-summary/',views.OrderSummaryView.as_view(),name='order-summary'),
    path('add-to-cart/<int:pk>/',views.add_to_cart,name='add-to-cart'),
    path('remove-from-cart/<int:pk>/',views.remove_from_cart,name='remove_from_cart'),
    path('remove-single-item-from-cart/<int:pk>/',views.remove_single_item_from_cart,name='remove-single-item-from-cart'),
    path('payment/<payment_option>/',views.PaymentView.as_view(),name='payment'),
    path('profile/',views.profile,name='profile'),
    path('account_update/',views.update_profile,name='account_update'),
    path('search/',views.SearchResultsView.as_view(),name='search_results'),
    path('comment/<int:pk>/delete/',views.comment_remove,name='comment_delete'),
    path('add-coupon/',views.AddCouponView.as_view(),name='add-coupon'),
]
