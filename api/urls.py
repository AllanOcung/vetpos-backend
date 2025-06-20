from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='user')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('user/profile/', views.user_profile, name='user_profile'),
    # This line includes the new /users/ URL
    path('', include(router.urls)),
]