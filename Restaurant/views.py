from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from datetime import datetime, date
from decimal import Decimal

from .models import MenuItem, Table, Reservation, Order, OrderItem, Payment, Inventory
from .serializers import (
    MenuItemSerializer, TableSerializer, ReservationSerializer,
    OrderSerializer, OrderCreateSerializer, OrderItemSerializer,
    PaymentSerializer, PaymentCreateSerializer, InventorySerializer,
    DailySalesReportSerializer, TableAvailabilitySerializer
)


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by availability
        available = self.request.query_params.get('available', None)
        if available is not None:
            queryset = queryset.filter(available=available.lower() == 'true')
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Get list of all categories"""
        categories = MenuItem.objects.values_list('category', flat=True).distinct()
        return Response(list(categories))
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get only available menu items"""
        available_items = self.queryset.filter(available=True)
        serializer = self.get_serializer(available_items, many=True)
        return Response(serializer.data)


class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Get all available tables"""
        available_tables = self.queryset.filter(is_available=True)
        serializer = TableAvailabilitySerializer(available_tables, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_available(self, request, pk=None):
        """Mark a table as available"""
        table = self.get_object()
        table.is_available = True
        table.save()
        serializer = self.get_serializer(table)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_unavailable(self, request, pk=None):
        """Mark a table as unavailable"""
        table = self.get_object()
        table.is_available = False
        table.save()
        serializer = self.get_serializer(table)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_capacity(self, request):
        """Get tables by minimum capacity"""
        min_capacity = request.query_params.get('min_capacity', 1)
        tables = self.queryset.filter(capacity__gte=min_capacity, is_available=True)
        serializer = TableAvailabilitySerializer(tables, many=True)
        return Response(serializer.data)


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status.upper())
        
        # Filter by date
        date_param = self.request.query_params.get('date', None)
        if date_param:
            queryset = queryset.filter(date=date_param)
        
        # Filter by customer
        customer_phone = self.request.query_params.get('customer_phone', None)
        if customer_phone:
            queryset = queryset.filter(customer_phone=customer_phone)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a reservation"""
        reservation = self.get_object()
        reservation.status = 'CANCELLED'
        reservation.save()
        serializer = self.get_serializer(reservation)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark reservation as completed"""
        reservation = self.get_object()
        reservation.status = 'COMPLETED'
        reservation.save()
        serializer = self.get_serializer(reservation)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's reservations"""
        today = timezone.now().date()
        reservations = self.queryset.filter(date=today)
        serializer = self.get_serializer(reservations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming reservations"""
        today = timezone.now().date()
        reservations = self.queryset.filter(
            date__gte=today,
            status='BOOKED'
        ).order_by('date', 'time')
        serializer = self.get_serializer(reservations, many=True)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status.upper())
        
        # Filter by table
        table = self.request.query_params.get('table', None)
        if table:
            queryset = queryset.filter(table_id=table)
        
        # Filter by date
        date_param = self.request.query_params.get('date', None)
        if date_param:
            queryset = queryset.filter(timestamp__date=date_param)
        
        return queryset
    
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """Update order status"""
        order = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Order.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = new_status
        order.save()
        
        # If order is served or cancelled, mark table as available
        if new_status in ['SERVED', 'CANCELLED']:
            order.table.is_available = True
            order.table.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """Add item to existing order"""
        order = self.get_object()
        
        if order.status in ['SERVED', 'CANCELLED']:
            return Response(
                {'error': 'Cannot add items to served or cancelled orders'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        menu_item_id = request.data.get('menu_item_id')
        quantity = request.data.get('quantity', 1)
        special_instructions = request.data.get('special_instructions', '')
        
        try:
            menu_item = MenuItem.objects.get(id=menu_item_id, available=True)
        except MenuItem.DoesNotExist:
            return Response(
                {'error': 'Menu item not found or unavailable'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        order_item = OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            quantity=quantity,
            price=menu_item.price,
            special_instructions=special_instructions
        )
        
        order.calculate_total()
        
        serializer = OrderItemSerializer(order_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'])
    def remove_item(self, request, pk=None):
        """Remove item from order"""
        order = self.get_object()
        item_id = request.data.get('item_id')
        
        if order.status in ['SERVED', 'CANCELLED']:
            return Response(
                {'error': 'Cannot remove items from served or cancelled orders'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            order_item = OrderItem.objects.get(id=item_id, order=order)
            order_item.delete()
            order.calculate_total()
            return Response({'message': 'Item removed successfully'})
        except OrderItem.DoesNotExist:
            return Response(
                {'error': 'Order item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active orders (pending or in progress)"""
        active_orders = self.queryset.filter(
            status__in=['PENDING', 'IN_PROGRESS']
        )
        serializer = self.get_serializer(active_orders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's orders"""
        today = timezone.now().date()
        orders = self.queryset.filter(timestamp__date=today)
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    permission_classes = [AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PaymentCreateSerializer
        return PaymentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by payment status
        payment_status = self.request.query_params.get('payment_status', None)
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status.upper())
        
        # Filter by payment method
        payment_method = self.request.query_params.get('payment_method', None)
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method.upper())
        
        # Filter by date
        date_param = self.request.query_params.get('date', None)
        if date_param:
            queryset = queryset.filter(payment_date__date=date_param)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def complete_payment(self, request, pk=None):
        """Mark payment as completed"""
        payment = self.get_object()
        
        if payment.payment_status == 'COMPLETED':
            return Response(
                {'error': 'Payment already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transaction_id = request.data.get('transaction_id', '')
        
        payment.payment_status = 'COMPLETED'
        payment.transaction_id = transaction_id
        payment.save()
        
        # Update order status
        payment.order.status = 'SERVED'
        payment.order.save()
        
        # Mark table as available
        payment.order.table.is_available = True
        payment.order.table.save()
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        """Process payment refund"""
        payment = self.get_object()
        
        if payment.payment_status != 'COMPLETED':
            return Response(
                {'error': 'Can only refund completed payments'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment.payment_status = 'REFUNDED'
        payment.save()
        
        # Update order status
        payment.order.status = 'CANCELLED'
        payment.order.save()
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's payments"""
        today = timezone.now().date()
        payments = self.queryset.filter(payment_date__date=today)
        serializer = self.get_serializer(payments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get payment summary by method"""
        date_param = request.query_params.get('date', timezone.now().date())
        
        payments = self.queryset.filter(
            payment_date__date=date_param,
            payment_status='COMPLETED'
        )
        
        summary = payments.values('payment_method').annotate(
            total=Sum('final_amount'),
            count=Count('id')
        )
        
        return Response(summary)


class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get items with low stock"""
        low_stock_items = self.queryset.filter(
            quantity__lte=models.F('reorder_level')
        )
        serializer = self.get_serializer(low_stock_items, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def update_quantity(self, request, pk=None):
        """Update inventory quantity"""
        inventory = self.get_object()
        quantity_change = request.data.get('quantity_change', 0)
        
        new_quantity = inventory.quantity + quantity_change
        
        if new_quantity < 0:
            return Response(
                {'error': 'Insufficient inventory'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        inventory.quantity = new_quantity
        inventory.save()
        
        serializer = self.get_serializer(inventory)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def restock(self, request, pk=None):
        """Restock inventory item"""
        inventory = self.get_object()
        quantity = request.data.get('quantity', 0)
        
        if quantity <= 0:
            return Response(
                {'error': 'Quantity must be positive'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        inventory.quantity += quantity
        inventory.save()
        
        serializer = self.get_serializer(inventory)
        return Response(serializer.data)


class ReportViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def daily_sales(self, request):
        """Generate daily sales report"""
        date_param = request.query_params.get('date', timezone.now().date())
        
        if isinstance(date_param, str):
            date_param = datetime.strptime(date_param, '%Y-%m-%d').date()
        
        orders = Order.objects.filter(timestamp__date=date_param)
        
        total_orders = orders.count()
        total_revenue = orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        payments = Payment.objects.filter(
            payment_date__date=date_param,
            payment_status='COMPLETED'
        )
        
        total_payments = payments.count()
        total_paid = payments.aggregate(Sum('final_amount'))['final_amount__sum'] or 0
        
        cancelled_orders = orders.filter(status='CANCELLED').count()
        pending_orders = orders.filter(status__in=['PENDING', 'IN_PROGRESS']).count()
        
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        report_data = {
            'date': date_param,
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'total_payments': total_payments,
            'total_paid': total_paid,
            'average_order_value': avg_order_value,
            'cancelled_orders': cancelled_orders,
            'pending_orders': pending_orders
        }
        
        serializer = DailySalesReportSerializer(report_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def inventory_alerts(self, request):
        """Get inventory items needing restock"""
        from .models import Inventory as InventoryModel
        low_stock = InventoryModel.objects.filter(
            quantity__lte=models.F('reorder_level')
        )
        serializer = InventorySerializer(low_stock, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def reservation_summary(self, request):
        """Get reservation summary for a date range"""
        start_date = request.query_params.get('start_date', timezone.now().date())
        end_date = request.query_params.get('end_date', timezone.now().date())
        
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        reservations = Reservation.objects.filter(
            date__range=[start_date, end_date]
        )
        
        summary = {
            'total_reservations': reservations.count(),
            'booked': reservations.filter(status='BOOKED').count(),
            'completed': reservations.filter(status='COMPLETED').count(),
            'cancelled': reservations.filter(status='CANCELLED').count(),
            'start_date': start_date,
            'end_date': end_date
        }
        
        return Response(summary)
    
    @action(detail=False, methods=['get'])
    def popular_items(self, request):
        """Get most popular menu items"""
        date_param = request.query_params.get('date', timezone.now().date())
        
        if isinstance(date_param, str):
            date_param = datetime.strptime(date_param, '%Y-%m-%d').date()
        
        popular = OrderItem.objects.filter(
            order__timestamp__date=date_param
        ).values(
            'menu_item__id',
            'menu_item__name',
            'menu_item__category'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum(models.F('price') * models.F('quantity'))
        ).order_by('-total_quantity')[:10]
        
        return Response(list(popular))