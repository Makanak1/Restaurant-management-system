from rest_framework import serializers
from .models import MenuItem, Table, Reservation, Order, OrderItem, Payment, Inventory
from django.utils import timezone
from datetime import datetime

class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = '__all__'


class ReservationSerializer(serializers.ModelSerializer):
    table_number = serializers.IntegerField(source='table.table_number', read_only=True)
    table_capacity = serializers.IntegerField(source='table.capacity', read_only=True)
    
    class Meta:
        model = Reservation
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, data):
        # Check if table capacity is sufficient
        if data.get('party_size') and data.get('table'):
            if data['party_size'] > data['table'].capacity:
                raise serializers.ValidationError(
                    f"Party size ({data['party_size']}) exceeds table capacity ({data['table'].capacity})"
                )
        
        # Check if table is available for the date/time
        if data.get('table') and data.get('date') and data.get('time'):
            existing_reservations = Reservation.objects.filter(
                table=data['table'],
                date=data['date'],
                time=data['time'],
                status='BOOKED'
            )
            
            if self.instance:
                existing_reservations = existing_reservations.exclude(pk=self.instance.pk)
            
            if existing_reservations.exists():
                raise serializers.ValidationError(
                    "This table is already reserved for the selected date and time"
                )
        
        return data


class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'menu_item', 'menu_item_name', 'quantity', 'price', 
                  'special_instructions', 'subtotal']
        read_only_fields = ['price']
    
    def get_subtotal(self, obj):
        return obj.price * obj.quantity


class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    table_number = serializers.IntegerField(source='table.table_number', read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'table', 'table_number', 'customer_name', 'total_price', 
                  'status', 'timestamp', 'updated_at', 'notes', 'order_items']
        read_only_fields = ['total_price', 'timestamp', 'updated_at']


class OrderCreateSerializer(serializers.ModelSerializer):
    items = serializers.ListField(
        child=serializers.DictField(),
        write_only=True
    )
    
    class Meta:
        model = Order
        fields = ['table', 'customer_name', 'notes', 'items']
    
    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must contain at least one item")
        
        for item in value:
            if 'menu_item_id' not in item or 'quantity' not in item:
                raise serializers.ValidationError(
                    "Each item must have 'menu_item_id' and 'quantity'"
                )
            
            try:
                menu_item = MenuItem.objects.get(id=item['menu_item_id'])
                if not menu_item.available:
                    raise serializers.ValidationError(
                        f"{menu_item.name} is currently unavailable"
                    )
            except MenuItem.DoesNotExist:
                raise serializers.ValidationError(
                    f"Menu item with id {item['menu_item_id']} does not exist"
                )
        
        return value
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        
        total = 0
        for item_data in items_data:
            menu_item = MenuItem.objects.get(id=item_data['menu_item_id'])
            order_item = OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=item_data['quantity'],
                price=menu_item.price,
                special_instructions=item_data.get('special_instructions', '')
            )
            total += order_item.price * order_item.quantity
        
        order.total_price = total
        order.save()
        
        # Mark table as unavailable
        order.table.is_available = False
        order.table.save()
        
        return order


class PaymentSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    order_total = serializers.DecimalField(
        source='order.total_price', 
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )
    
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['payment_date', 'updated_at', 'final_amount']
    
    def validate(self, data):
        # Validate amount matches order total
        if data.get('order') and data.get('amount'):
            if data['amount'] != data['order'].total_price:
                raise serializers.ValidationError(
                    f"Payment amount (${data['amount']}) must match order total (${data['order'].total_price})"
                )
        
        return data
    
    def create(self, validated_data):
        payment = Payment.objects.create(**validated_data)
        payment.calculate_final_amount()
        
        # If payment is completed, update order status
        if payment.payment_status == 'COMPLETED':
            payment.order.status = 'SERVED'
            payment.order.save()
        
        return payment


class PaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['order', 'payment_method', 'tip_amount', 'discount_amount', 'notes']
    
    def validate_order(self, value):
        # Check if order already has a payment
        if hasattr(value, 'payment'):
            raise serializers.ValidationError("This order already has a payment")
        
        # Check if order is in valid state for payment
        if value.status == 'CANCELLED':
            raise serializers.ValidationError("Cannot create payment for cancelled order")
        
        return value
    
    def create(self, validated_data):
        order = validated_data['order']
        
        # Calculate tax (assuming 8% tax rate)
        tax_amount = order.total_price * 0.08
        
        payment = Payment.objects.create(
            order=order,
            amount=order.total_price,
            payment_method=validated_data['payment_method'],
            tip_amount=validated_data.get('tip_amount', 0),
            discount_amount=validated_data.get('discount_amount', 0),
            tax_amount=tax_amount,
            notes=validated_data.get('notes', ''),
            payment_status='PENDING'
        )
        
        payment.calculate_final_amount()
        return payment


class InventorySerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Inventory
        fields = '__all__'
        read_only_fields = ['last_updated']


class DailySalesReportSerializer(serializers.Serializer):
    date = serializers.DateField()
    total_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_payments = serializers.IntegerField()
    total_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    cancelled_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()


class TableAvailabilitySerializer(serializers.ModelSerializer):
    current_order = serializers.SerializerMethodField()
    
    class Meta:
        model = Table
        fields = ['id', 'table_number', 'capacity', 'is_available', 'current_order']
    
    def get_current_order(self, obj):
        if not obj.is_available:
            current_order = obj.orders.filter(
                status__in=['PENDING', 'IN_PROGRESS']
            ).first()
            if current_order:
                return {
                    'order_id': current_order.id,
                    'status': current_order.status,
                    'total': str(current_order.total_price)
                }
        return None