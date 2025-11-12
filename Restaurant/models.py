from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class MenuItem(models.Model):
    CATEGORY_CHOICES = [
        ('APPETIZER', 'Appetizer'),
        ('MAIN', 'Main Course'),
        ('DESSERT', 'Dessert'),
        ('BEVERAGE', 'Beverage'),
        ('SPECIAL', 'Special'),
    ]
    
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    description = models.TextField(blank=True)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} - ${self.price}"


class Table(models.Model):
    table_number = models.IntegerField(unique=True)
    capacity = models.IntegerField(validators=[MinValueValidator(1)])
    is_available = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['table_number']
    
    def __str__(self):
        return f"Table {self.table_number} (Capacity: {self.capacity})"


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('BOOKED', 'Booked'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField(blank=True, null=True)
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='reservations')
    date = models.DateField()
    time = models.TimeField()
    party_size = models.IntegerField(validators=[MinValueValidator(1)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='BOOKED')
    special_requests = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-time']
    
    def __str__(self):
        return f"{self.customer_name} - Table {self.table.table_number} on {self.date}"


class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('SERVED', 'Served'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='orders')
    customer_name = models.CharField(max_length=200, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Order #{self.id} - Table {self.table.table_number}"
    
    def calculate_total(self):
        total = sum(item.price * item.quantity for item in self.order_items.all())
        self.total_price = total
        self.save()
        return total


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    special_instructions = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"
    
    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.menu_item.price
        super().save(*args, **kwargs)


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Credit/Debit Card'),
        ('DIGITAL', 'Digital Wallet'),
        ('UPI', 'UPI'),
        ('BANK_TRANSFER', 'Bank Transfer'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('REFUNDED', 'Refunded'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    tip_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Payment #{self.id} - Order #{self.order.id} - ${self.final_amount}"
    
    def calculate_final_amount(self):
        self.final_amount = self.amount + self.tip_amount + self.tax_amount - self.discount_amount
        self.save()
        return self.final_amount


class Inventory(models.Model):
    item_name = models.CharField(max_length=200, unique=True)
    quantity = models.IntegerField(validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=50, default='units')
    reorder_level = models.IntegerField(validators=[MinValueValidator(0)])
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Inventory'
        ordering = ['item_name']
    
    def __str__(self):
        return f"{self.item_name} - {self.quantity} {self.unit}"
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level