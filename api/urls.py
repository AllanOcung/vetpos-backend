from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'suppliers', views.SupplierViewSet, basename='supplier')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'restock-history', views.RestockHistoryViewSet, basename='restock-history')
router.register(r'promotions', views.PromotionViewSet, basename='promotion')
router.register(r'sales', views.SaleViewSet, basename='sale')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('user/profile/', views.user_profile, name='user_profile'),
    path('dashboard-stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('', include(router.urls)),
]