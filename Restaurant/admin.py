from django.contrib import admin
from .models import MenuItem, Table, Reservation, Order, OrderItem, Payment, Inventory


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'available', 'created_at']
    list_filter = ['category', 'available', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['category', 'name']
    list_editable = ['available', 'price']


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ['table_number', 'capacity', 'is_available']
    list_filter = ['is_available', 'capacity']
    ordering = ['table_number']
    list_editable = ['is_available']


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'customer_phone', 'table', 'date', 'time', 'party_size', 'status']
    list_filter = ['status', 'date', 'table']
    search_fields = ['customer_name', 'customer_phone']
    ordering = ['-date', '-time']
    list_editable = ['status']
    date_hierarchy = 'date'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    readonly_fields = ['price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'table', 'customer_name', 'total_price', 'status', 'timestamp']
    list_filter = ['status', 'timestamp', 'table']
    search_fields = ['customer_name', 'id']
    ordering = ['-timestamp']
    readonly_fields = ['total_price', 'timestamp']
    inlines = [OrderItemInline]
    date_hierarchy = 'timestamp'
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.calculate_total()


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'menu_item', 'quantity', 'price', 'get_subtotal']
    list_filter = ['order__status', 'menu_item__category']
    search_fields = ['order__id', 'menu_item__name']
    readonly_fields = ['price']
    
    def get_subtotal(self, obj):
        return obj.price * obj.quantity
    get_subtotal.short_description = 'Subtotal'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'amount', 'payment_method', 'payment_status', 
                    'final_amount', 'payment_date']
    list_filter = ['payment_status', 'payment_method', 'payment_date']
    search_fields = ['order__id', 'transaction_id']
    ordering = ['-payment_date']
    readonly_fields = ['payment_date', 'final_amount']
    date_hierarchy = 'payment_date'
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order', 'amount')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'payment_status', 'transaction_id')
        }),
        ('Amounts', {
            'fields': ('tip_amount', 'tax_amount', 'discount_amount', 'final_amount')
        }),
        ('Timestamps', {
            'fields': ('payment_date', 'updated_at')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['item_name', 'quantity', 'unit', 'reorder_level', 
                    'is_low_stock', 'cost_per_unit', 'last_updated']
    list_filter = ['last_updated']
    search_fields = ['item_name']
    ordering = ['item_name']
    readonly_fields = ['last_updated']
    
    def is_low_stock(self, obj):
        return obj.quantity <= obj.reorder_level
    is_low_stock.boolean = True
    is_low_stock.short_description = 'Low Stock'


# Customize admin site
admin.site.site_header = "Restaurant Management System"
admin.site.site_title = "Restaurant Admin"
admin.site.index_title = "Welcome to Restaurant Management System"