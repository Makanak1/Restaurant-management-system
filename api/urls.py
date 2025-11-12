# restaurant_system/urls.py

from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI Schema
schema_view = get_schema_view(
    openapi.Info(
        title="Restaurant Management System API",
        default_version='v1',
        description="""
        A comprehensive Restaurant Management System API that handles:
        - Menu Items Management
        - Table Management
        - Reservations
        - Orders and Order Items
        - Payment Processing
        - Inventory Management
        - Reporting and Analytics
        """,
        terms_of_service="https://www.yourrestaurant.com/terms/",
        contact=openapi.Contact(email="contact@restaurant.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/', include('Restaurant.urls')),
    
    # API Documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', 
            schema_view.without_ui(cache_timeout=0), 
            name='schema-json'),
    path('swagger/', 
        schema_view.with_ui('swagger', cache_timeout=0), 
        name='schema-swagger-ui'),
    path('redoc/', 
        schema_view.with_ui('redoc', cache_timeout=0), 
        name='schema-redoc'),
    
    # DRF Browsable API auth
    path('api-auth/', include('rest_framework.urls')),
]