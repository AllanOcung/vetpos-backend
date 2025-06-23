from django.contrib.auth.models import User, Group
from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from inventory.models import Setting, Supplier, Product, RestockHistory, Sale, SaleItem, Promotion
from django.db import transaction

class UserListSerializer(serializers.ModelSerializer):
    # This field gets the user's role from the group they belong to.
    role = serializers.CharField(source='groups.first.name', read_only=True)
     # Add a method field to get the full name
    full_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        # Define the fields to include in the API response.
        # Add first_name, last_name, and our new full_name to the fields list
        fields = ['id', 'username', 'email', 'role', 'last_login', 'full_name', 'status', 'date_joined']
        
        
    def get_full_name(self, obj):
          # Use Django's built-in method to get the full name.
          # It gracefully handles cases where first/last names are blank.
          # If the full name is empty, it will fall back to the username.
          return obj.get_full_name() or obj.username
    def get_status(self, obj):
        return "active" if obj.is_active else "inactive"
   

class UserCreateSerializer(serializers.ModelSerializer):
    # We expect a 'role_name' field from the frontend to assign a group
    role_name = serializers.CharField(write_only=True)

    class Meta:
        model = User
        # Define the fields the frontend will send to create a user
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role_name']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Pop our custom 'role_name' field from the data
        role_name = validated_data.pop('role_name')
        
        # Create the user using the standard create_user method to handle password hashing
        user = User.objects.create_user(**validated_data)
        
        # Assign the user to a group based on the role_name
        try:
            group = Group.objects.get(name=role_name)
            user.groups.add(group)
        except Group.DoesNotExist:
            # This is a safeguard. Assumes 'admin', 'cashier', etc. groups exist.
            # You could add error handling here if needed.
            pass
            
        return user
   

# serializer for updating users
class UserUpdateSerializer(serializers.ModelSerializer):
    # 'role_name' will be used to change the user's group
    role_name = serializers.CharField(write_only=True, required=False)
    # 'is_active' will be used to change the user's status
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = User
        # Define the fields that can be updated.
        # We make 'username' read-only to prevent it from being changed.
        fields = ['username', 'email', 'first_name', 'last_name', 'role_name', 'is_active']
        read_only_fields = ['username']

    def update(self, instance, validated_data):
        # If a new role is provided, find the corresponding group and update the user.
        if 'role_name' in validated_data:
            role_name = validated_data.pop('role_name')
            try:
                group = Group.objects.get(name=role_name)
                instance.groups.set([group]) # .set() replaces any existing groups
            except Group.DoesNotExist:
                # If the group doesn't exist, we can ignore it or raise an error.
                # For now, we'll ignore it.
                pass

        # If a new status is provided, update the user's is_active flag.
        if 'is_active' in validated_data:
            instance.is_active = validated_data.pop('is_active')

        # Let the parent class handle updating the other standard fields.
        return super().update(instance, validated_data)
   
    
# Add this new serializer for Suppliers
class SupplierSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='get_status_display', read_only=True)
    # The frontend uses 'contact', so we'll map it from 'contact_person'
    contact = serializers.CharField(source='contact_person', required=False, allow_blank=True)
    
    # These fields don't exist on the model yet, so we provide defaults.
    # We will implement the logic for these later with the Restocking module.
    totalOrders = serializers.SerializerMethodField()
    lastOrder = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        # We make 'is_active' a normal field. The frontend will now receive it
        # and can send it back directly for updates.
        fields = ['id', 'name', 'contact', 'email', 'phone', 'address', 'status', 'totalOrders', 'lastOrder', 'is_active']


    def get_status_display(self, obj):
        return "active" if obj.is_active else "inactive"

    def get_totalOrders(self, obj):
        # Placeholder logic
        return 0
    
    def get_lastOrder(self, obj):
        # Placeholder logic
        return "N/A"


class ProductSerializer(serializers.ModelSerializer):
    # Read-only fields for displaying related data and calculated status
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Product
        # List all fields to be sent to the frontend
        fields = [
            'id', 'name', 'category', 'batch_number', 'expiry_date', 'unit',
            'quantity', 'price', 'supplier', 'supplier_name', 'status'
        ]
        # 'supplier' is write-only because we use 'supplier_name' for reading
        extra_kwargs = {'supplier': {'write_only': True}}

    def get_status(self, obj):
        """Calculates product status based on quantity and expiry date."""
        today = timezone.now().date()
        if obj.expiry_date < today:
            return 'expired'
        if obj.quantity == 0:
            return 'out-of-stock'
        # Using a hardcoded threshold of 10 for low stock for now
        if obj.quantity < 10:
            return 'low-stock'
        if obj.expiry_date <= today + timedelta(days=30):
            return 'expiring-soon'
        return 'in-stock' 
    
    
# Serializer to handle the data for a new restock
class RestockSerializer(serializers.Serializer):
    quantity_added = serializers.IntegerField(min_value=1)
    supplier_id = serializers.IntegerField()
    cost_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2)
    notes = serializers.CharField(required=False, allow_blank=True)

# Serializer to display the restock history
class RestockHistorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = RestockHistory
        fields = [
            'id', 'product_name', 'supplier_name', 'user_name', 
            'quantity_added', 'cost_per_unit', 'notes', 'restock_date'
        ]


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = '__all__'
                
        
# Serializer for Sale and SaleItem models
class SaleItemSerializer(serializers.ModelSerializer):
    """Serializer for items within a sale."""
    product_name = serializers.CharField(source='product.name', read_only=True)
    class Meta:
        model = SaleItem
        fields = ['product', 'product_name', 'quantity', 'unit_price']

class SaleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new sale."""
    items = SaleItemSerializer(many=True)
    discount_type = serializers.CharField(required=False, default='none')
    discount_value = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    
    # Make these fields read-only as they will be calculated on the server
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    tax_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Sale
        
        fields = ['id', 'total_amount', 'items', 'subtotal', 'tax_amount', 'created_at', 'discount_type', 'discount_value', 
            'discount_amount']
       

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        discount_type = validated_data.pop('discount_type', 'none')
        discount_value = validated_data.pop('discount_value', Decimal('0'))
        
        # Use a database transaction to ensure all operations succeed or none do.
        with transaction.atomic():
            # Calculate subtotal from item list
            subtotal = sum(Decimal(item['unit_price']) * item['quantity'] for item in items_data)
            
            # --- Apply Automatic Promotions ---
            promotion_discount_amount = Decimal('0')
            today = timezone.now().date()
            active_promotions = Promotion.objects.filter(
                is_active=True, 
                start_date__lte=today, 
                end_date__gte=today
            ).prefetch_related('products')

            promo_map = {p.id: promo for promo in active_promotions for p in promo.products.all()}

            for item_data in items_data:
                product = item_data['product']
                if product.id in promo_map:
                    promo = promo_map[product.id]
                    if promo.promotion_type == 'product_percentage':
                        item_price = Decimal(item_data.get('unit_price', product.price))
                        item_total = item_price * item_data['quantity']
                        promotion_discount_amount += item_total * (promo.value / Decimal('100.0'))

            # --- Apply Manual Discount (on the price after promotions) ---
            price_after_promos = subtotal - promotion_discount_amount
            manual_discount_amount = Decimal('0')
            if discount_type == 'percentage':
                manual_discount_amount = price_after_promos * (discount_value / Decimal('100.0'))
            elif discount_type == 'fixed':
                manual_discount_amount = discount_value
            
            manual_discount_amount = min(price_after_promos, manual_discount_amount)

            taxable_amount = price_after_promos - manual_discount_amount

            
            
            # Get tax rate from settings, default to 0 if not found
            try:
                tax_rate_setting = Setting.objects.get(key='tax_rate')
                tax_rate = Decimal(tax_rate_setting.value)
            except (Setting.DoesNotExist, ValueError):
                tax_rate = Decimal('0.0')
                
             # Calculate tax and total
            tax_amount = taxable_amount * (tax_rate / Decimal('100.0'))
            total_amount = taxable_amount + tax_amount
            
            
            # Create the sale with calculated values
            sale = Sale.objects.create(
                subtotal=subtotal,
                discount_type=discount_type,
                discount_value=discount_value,
                discount_amount=manual_discount_amount,
                tax_amount=tax_amount,
                total_amount=total_amount,
                **validated_data
            )
            
             # Create sale items and update product stock
            for item_data in items_data:
                product = item_data['product']
                quantity_sold = item_data['quantity']
                
                if product.quantity < quantity_sold:
                    raise serializers.ValidationError(f"Not enough stock for {product.name}. Available: {product.quantity}, Requested: {quantity_sold}")

                SaleItem.objects.create(sale=sale, **item_data)
                
                # Decrease product quantity
                product.quantity -= quantity_sold
                product.save()
                
            return sale

class SaleListSerializer(serializers.ModelSerializer):
    """Serializer for listing past sales."""
    user_name = serializers.CharField(source='user.username', read_only=True)
    items = SaleItemSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = ['id', 'user_name', 'total_amount', 'created_at', 'items']


    # Serializer for the Setting model
class SettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setting
        fields = ['key', 'value']