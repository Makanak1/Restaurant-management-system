# restaurant/management/commands/seed.py

from django.core.management.base import BaseCommand
from Restaurant.models import MenuItem, Table, Inventory
from decimal import Decimal

class Command(BaseCommand):
    help = 'Seed the database with initial data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')
        
        # Clear existing data
        self.stdout.write('Clearing existing data...')
        MenuItem.objects.all().delete()
        Table.objects.all().delete()
        Inventory.objects.all().delete()
        
        # Create Menu Items
        self.stdout.write('Creating menu items...')
        
        menu_items = [
            # Appetizers
            {'name': 'Bruschetta', 'category': 'APPETIZER', 'price': Decimal('8.99'), 
            'description': 'Toasted bread with tomatoes, garlic, and basil', 'available': True},
            {'name': 'Mozzarella Sticks', 'category': 'APPETIZER', 'price': Decimal('7.99'), 
            'description': 'Deep-fried mozzarella with marinara sauce', 'available': True},
            {'name': 'Caesar Salad', 'category': 'APPETIZER', 'price': Decimal('9.99'), 
            'description': 'Romaine lettuce with Caesar dressing and croutons', 'available': True},
            {'name': 'Chicken Wings', 'category': 'APPETIZER', 'price': Decimal('11.99'), 
            'description': 'Buffalo or BBQ style wings', 'available': True},
            
            # Main Courses
            {'name': 'Grilled Salmon', 'category': 'MAIN', 'price': Decimal('24.99'), 
            'description': 'Fresh Atlantic salmon with vegetables', 'available': True},
            {'name': 'Ribeye Steak', 'category': 'MAIN', 'price': Decimal('32.99'), 
            'description': '12oz ribeye with mashed potatoes', 'available': True},
            {'name': 'Chicken Parmesan', 'category': 'MAIN', 'price': Decimal('18.99'), 
            'description': 'Breaded chicken with marinara and mozzarella', 'available': True},
            {'name': 'Spaghetti Carbonara', 'category': 'MAIN', 'price': Decimal('16.99'), 
            'description': 'Classic pasta with bacon and cream sauce', 'available': True},
            {'name': 'Margherita Pizza', 'category': 'MAIN', 'price': Decimal('14.99'), 
            'description': 'Fresh mozzarella, tomatoes, and basil', 'available': True},
            {'name': 'Beef Burger', 'category': 'MAIN', 'price': Decimal('13.99'), 
            'description': 'Angus beef burger with fries', 'available': True},
            
            # Desserts
            {'name': 'Tiramisu', 'category': 'DESSERT', 'price': Decimal('7.99'), 
            'description': 'Classic Italian dessert with coffee and mascarpone', 'available': True},
            {'name': 'Chocolate Lava Cake', 'category': 'DESSERT', 'price': Decimal('8.99'), 
            'description': 'Warm chocolate cake with vanilla ice cream', 'available': True},
            {'name': 'Cheesecake', 'category': 'DESSERT', 'price': Decimal('6.99'), 
            'description': 'New York style cheesecake', 'available': True},
            {'name': 'Panna Cotta', 'category': 'DESSERT', 'price': Decimal('6.99'), 
            'description': 'Italian custard with berry compote', 'available': True},
            
            # Beverages
            {'name': 'Coca Cola', 'category': 'BEVERAGE', 'price': Decimal('2.99'), 
            'description': 'Regular or Diet', 'available': True},
            {'name': 'Fresh Lemonade', 'category': 'BEVERAGE', 'price': Decimal('3.99'), 
            'description': 'Freshly squeezed lemonade', 'available': True},
            {'name': 'Iced Tea', 'category': 'BEVERAGE', 'price': Decimal('2.99'), 
            'description': 'Sweet or Unsweet', 'available': True},
            {'name': 'Cappuccino', 'category': 'BEVERAGE', 'price': Decimal('4.99'), 
            'description': 'Espresso with steamed milk', 'available': True},
            {'name': 'Red Wine', 'category': 'BEVERAGE', 'price': Decimal('8.99'), 
            'description': 'House red wine', 'available': True},
            {'name': 'White Wine', 'category': 'BEVERAGE', 'price': Decimal('8.99'), 
            'description': 'House white wine', 'available': True},
        ]
        
        for item_data in menu_items:
            MenuItem.objects.create(**item_data)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(menu_items)} menu items'))
        
        # Create Tables
        self.stdout.write('Creating tables...')
        
        tables_data = [
            {'table_number': 1, 'capacity': 2, 'is_available': True},
            {'table_number': 2, 'capacity': 2, 'is_available': True},
            {'table_number': 3, 'capacity': 4, 'is_available': True},
            {'table_number': 4, 'capacity': 4, 'is_available': True},
            {'table_number': 5, 'capacity': 4, 'is_available': True},
            {'table_number': 6, 'capacity': 6, 'is_available': True},
            {'table_number': 7, 'capacity': 6, 'is_available': True},
            {'table_number': 8, 'capacity': 8, 'is_available': True},
            {'table_number': 9, 'capacity': 2, 'is_available': True},
            {'table_number': 10, 'capacity': 4, 'is_available': True},
        ]
        
        for table_data in tables_data:
            Table.objects.create(**table_data)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(tables_data)} tables'))
        
        # Create Inventory Items
        self.stdout.write('Creating inventory items...')
        
        inventory_data = [
            {'item_name': 'Salmon Fillets', 'quantity': 50, 'unit': 'pieces', 
            'reorder_level': 15, 'cost_per_unit': Decimal('12.00')},
            {'item_name': 'Ribeye Steaks', 'quantity': 30, 'unit': 'pieces', 
            'reorder_level': 10, 'cost_per_unit': Decimal('18.00')},
            {'item_name': 'Chicken Breasts', 'quantity': 60, 'unit': 'pieces', 
            'reorder_level': 20, 'cost_per_unit': Decimal('6.00')},
            {'item_name': 'Pasta', 'quantity': 100, 'unit': 'lbs', 
            'reorder_level': 25, 'cost_per_unit': Decimal('2.50')},
            {'item_name': 'Tomatoes', 'quantity': 80, 'unit': 'lbs', 
            'reorder_level': 20, 'cost_per_unit': Decimal('1.50')},
            {'item_name': 'Mozzarella Cheese', 'quantity': 40, 'unit': 'lbs', 
            'reorder_level': 15, 'cost_per_unit': Decimal('4.00')},
            {'item_name': 'Lettuce', 'quantity': 30, 'unit': 'heads', 
            'reorder_level': 10, 'cost_per_unit': Decimal('1.00')},
            {'item_name': 'Eggs', 'quantity': 120, 'unit': 'pieces', 
            'reorder_level': 30, 'cost_per_unit': Decimal('0.25')},
            {'item_name': 'Flour', 'quantity': 150, 'unit': 'lbs', 
            'reorder_level': 40, 'cost_per_unit': Decimal('0.50')},
            {'item_name': 'Olive Oil', 'quantity': 20, 'unit': 'bottles', 
            'reorder_level': 5, 'cost_per_unit': Decimal('8.00')},
        ]
        
        for inv_data in inventory_data:
            Inventory.objects.create(**inv_data)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(inventory_data)} inventory items'))
        
        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))