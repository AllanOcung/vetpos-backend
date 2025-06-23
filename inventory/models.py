from django.db import models
from django.conf import settings

class Supplier(models.Model):
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
   
class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    batch_number = models.CharField(max_length=100, blank=True)
    expiry_date = models.DateField()
    unit = models.CharField(max_length=50) # e.g., 'Tablets', 'ml', 'Bottles'
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='products')
    
    # Auto-managed timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Batch: {self.batch_number})"
   

class RestockHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='restock_history')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='restocks')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    quantity_added = models.PositiveIntegerField()
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    restock_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Restocked {self.quantity_added} of {self.product.name} on {self.restock_date.strftime('%Y-%m-%d')}"
   
# Model for system-wide settings
class Setting(models.Model):
    key = models.CharField(max_length=50, unique=True)
    value = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.key}: {self.value}"


class Promotion(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    # We'll start with a simple percentage discount type
    promotion_type = models.CharField(max_length=20, default='product_percentage')
    value = models.DecimalField(max_digits=5, decimal_places=2) # e.g., 20.00 for 20%
    start_date = models.DateField()
    end_date = models.DateField()
    products = models.ManyToManyField(Product, related_name='promotions')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.value}%)"
   
   
class Sale(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    promotion_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_type = models.CharField(max_length=20, default='none') # e.g., 'none', 'percentage', 'fixed'
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0) # The % or fixed value
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0) # The calculated discount amount
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sale {self.id} on {self.created_at.strftime('%Y-%m-%d')}"

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2) # Price at the time of sale

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Sale {self.sale.id}"