from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MenuItemViewSet, TableViewSet, ReservationViewSet,
    OrderViewSet, PaymentViewSet, InventoryViewSet, ReportViewSet
)

# Create router
router = DefaultRouter()
router.register(r'menu', MenuItemViewSet, basename='menu')
router.register(r'tables', TableViewSet, basename='table')
router.register(r'reservations', ReservationViewSet, basename='reservation')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'reports', ReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
]