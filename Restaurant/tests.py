# restaurant/tests.py

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, time

from .models import MenuItem, Table, Reservation, Order, OrderItem, Payment, Inventory


class MenuItemTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.menu_item = MenuItem.objects.create(
            name='Test Burger',
            category='MAIN',
            price=Decimal('12.99'),
            description='Test description',
            available=True
        )
    
    def test_list_menu_items(self):
        response = self.client.get('/api/menu/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_create_menu_item(self):
        data = {
            'name': 'New Pizza',
            'category': 'MAIN',
            'price': '15.99',
            'description': 'Delicious pizza',
            'available': True
        }
        response = self.client.post('/api/menu/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MenuItem.objects.count(), 2)
    
    def test_filter_available_items(self):
        MenuItem.objects.create(
            name='Unavailable Item',
            category='MAIN',
            price=Decimal('10.00'),
            available=False
        )
        response = self.client.get('/api/menu/available/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class TableTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.table = Table.objects.create(
            table_number=1,
            capacity=4,
            is_available=True
        )
    
    def test_list_tables(self):
        response = self.client.get('/api/tables/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_available_tables(self):
        Table.objects.create(table_number=2, capacity=2, is_available=False)
        response = self.client.get('/api/tables/available/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_mark_table_unavailable(self):
        response = self.client.post(f'/api/tables/{self.table.id}/mark_unavailable/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.table.refresh_from_db()
        self.assertFalse(self.table.is_available)


class ReservationTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.table = Table.objects.create(
            table_number=1,
            capacity=4,
            is_available=True
        )
    
    def test_create_reservation(self):
        data = {
            'customer_name': 'John Doe',
            'customer_phone': '+1234567890',
            'customer_email': 'john@example.com',
            'table': self.table.id,
            'date': str(date.today()),
            'time': '18:00:00',
            'party_size': 4,
            'special_requests': 'Window seat'
        }
        response = self.client.post('/api/reservations/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reservation.objects.count(), 1)
    
    def test_prevent_overbooking(self):
        # Create first reservation
        Reservation.objects.create(
            customer_name='First Customer',
            customer_phone='+1111111111',
            table=self.table,
            date=date.today(),
            time=time(18, 0),
            party_size=4,
            status='BOOKED'
        )
        
        # Try to create conflicting reservation
        data = {
            'customer_name': 'Second Customer',
            'customer_phone': '+2222222222',
            'table': self.table.id,
            'date': str(date.today()),
            'time': '18:00:00',
            'party_size': 4
        }
        response = self.client.post('/api/reservations/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_cancel_reservation(self):
        reservation = Reservation.objects.create(
            customer_name='Test Customer',
            customer_phone='+1234567890',
            table=self.table,
            date=date.today(),
            time=time(19, 0),
            party_size=2,
            status='BOOKED'
        )
        response = self.client.post(f'/api/reservations/{reservation.id}/cancel/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'CANCELLED')


class OrderTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.table = Table.objects.create(
            table_number=1,
            capacity=4,
            is_available=True
        )
        self.menu_item1 = MenuItem.objects.create(
            name='Burger',
            category='MAIN',
            price=Decimal('12.99'),
            available=True
        )
        self.menu_item2 = MenuItem.objects.create(
            name='Fries',
            category='APPETIZER',
            price=Decimal('4.99'),
            available=True
        )
    
    def test_create_order(self):
        data = {
            'table': self.table.id,
            'customer_name': 'Test Customer',
            'notes': 'No onions',
            'items': [
                {
                    'menu_item_id': self.menu_item1.id,
                    'quantity': 2
                },
                {
                    'menu_item_id': self.menu_item2.id,
                    'quantity': 1
                }
            ]
        }
        response = self.client.post('/api/orders/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        
        order = Order.objects.first()
        expected_total = (self.menu_item1.price * 2) + (self.menu_item2.price * 1)
        self.assertEqual(order.total_price, expected_total)
        
        # Check table is marked unavailable
        self.table.refresh_from_db()
        self.assertFalse(self.table.is_available)
    
    def test_add_item_to_order(self):
        order = Order.objects.create(
            table=self.table,
            customer_name='Test Customer'
        )
        
        data = {
            'menu_item_id': self.menu_item1.id,
            'quantity': 1
        }
        response = self.client.post(f'/api/orders/{order.id}/add_item/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(order.order_items.count(), 1)
    
    def test_update_order_status(self):
        order = Order.objects.create(
            table=self.table,
            customer_name='Test Customer',
            status='PENDING'
        )
        
        data = {'status': 'IN_PROGRESS'}
        response = self.client.patch(f'/api/orders/{order.id}/update_status/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, 'IN_PROGRESS')


class PaymentTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.table = Table.objects.create(
            table_number=1,
            capacity=4,
            is_available=False
        )
        self.menu_item = MenuItem.objects.create(
            name='Test Item',
            category='MAIN',
            price=Decimal('20.00'),
            available=True
        )
        self.order = Order.objects.create(
            table=self.table,
            customer_name='Test Customer',
            total_price=Decimal('20.00'),
            status='PENDING'
        )
        OrderItem.objects.create(
            order=self.order,
            menu_item=self.menu_item,
            quantity=1,
            price=self.menu_item.price
        )
    
    def test_create_payment(self):
        data = {
            'order': self.order.id,
            'payment_method': 'CARD',
            'tip_amount': '3.00',
            'discount_amount': '0.00'
        }
        response = self.client.post('/api/payments/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        payment = Payment.objects.first()
        # Final amount = order total + tip + tax(8%) - discount
        expected_final = Decimal('20.00') + Decimal('3.00') + (Decimal('20.00') * Decimal('0.08'))
        self.assertEqual(payment.final_amount, expected_final)
    
    def test_complete_payment(self):
        payment = Payment.objects.create(
            order=self.order,
            amount=self.order.total_price,
            payment_method='CASH',
            payment_status='PENDING'
        )
        payment.calculate_final_amount()
        
        data = {'transaction_id': 'TXN123456'}
        response = self.client.post(f'/api/payments/{payment.id}/complete_payment/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        payment.refresh_from_db()
        self.assertEqual(payment.payment_status, 'COMPLETED')
        
        # Check order is marked as served
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'SERVED')
        
        # Check table is available
        self.table.refresh_from_db()
        self.assertTrue(self.table.is_available)
    
    def test_prevent_duplicate_payment(self):
        Payment.objects.create(
            order=self.order,
            amount=self.order.total_price,
            payment_method='CARD',
            payment_status='COMPLETED'
        )
        
        data = {
            'order': self.order.id,
            'payment_method': 'CASH'
        }
        response = self.client.post('/api/payments/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class InventoryTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.inventory = Inventory.objects.create(
            item_name='Test Item',
            quantity=50,
            unit='pieces',
            reorder_level=20,
            cost_per_unit=Decimal('5.00')
        )
    
    def test_list_inventory(self):
        response = self.client.get('/api/inventory/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_low_stock_alert(self):
        # Create low stock item
        Inventory.objects.create(
            item_name='Low Stock Item',
            quantity=10,
            unit='units',
            reorder_level=15
        )
        
        response = self.client.get('/api/inventory/low_stock/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_restock_item(self):
        data = {'quantity': 30}
        response = self.client.post(f'/api/inventory/{self.inventory.id}/restock/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 80)


class ReportTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.table = Table.objects.create(table_number=1, capacity=4)
        self.menu_item = MenuItem.objects.create(
            name='Test Item',
            category='MAIN',
            price=Decimal('25.00')
        )
    
    def test_daily_sales_report(self):
        # Create some orders
        order1 = Order.objects.create(
            table=self.table,
            total_price=Decimal('25.00'),
            status='SERVED'
        )
        order2 = Order.objects.create(
            table=self.table,
            total_price=Decimal('30.00'),
            status='SERVED'
        )
        
        today = date.today()
        response = self.client.get(f'/api/reports/daily_sales/?date={today}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_orders'], 2)
        self.assertEqual(Decimal(response.data['total_revenue']), Decimal('55.00'))