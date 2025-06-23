from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, F, Count
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework import viewsets, status, permissions
from django.contrib.auth.models import User
from .serializers import ( 
                          UserListSerializer, UserCreateSerializer, UserUpdateSerializer, 
                          SupplierSerializer, ProductSerializer, RestockSerializer, RestockHistorySerializer, 
                          SaleCreateSerializer, SaleListSerializer, PromotionSerializer
                          )
from inventory.models import Supplier, Product, RestockHistory, Sale, Setting, Promotion


# Custom permission to only allow users in the 'admin' group
class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='admin').exists()

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    user = request.user
    # Get the user's group (role). We assume one group per user for simplicity.
    group = user.groups.first()
    
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': group.name if group else None
    })
    

# ViewSet for listing users
class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed.
    """
    queryset = User.objects.all().order_by('-date_joined')
    # Default serializer for listing users
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
    
    # Add this method to specify a different serializer for the 'create' action
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        # Add this condition to use the update serializer for edit actions
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserListSerializer
    
class IsAdminOrInventoryManager(BasePermission):
    """
    Allows access only to admin or inventory manager users.
    """
    def has_permission(self, request, view):
        return request.user.groups.filter(name__in=['admin', 'inventory_manager']).exists()
    
    
class IsAdminOrCashier(BasePermission):
    """
    Allows access only to admin or cashier users.
    """
    def has_permission(self, request, view):
        return request.user.groups.filter(name__in=['admin', 'cashier']).exists()
    
# More specific permission class for products
class ProductAccessPermission(BasePermission):
    """
    - Allows read access (GET) to cashiers, inventory managers, and admins.
    - Restricts write access (POST, PUT, DELETE) to inventory managers and admins.
    """
    def has_permission(self, request, view):
        # Allow read access for any of the three roles
        if request.method in permissions.SAFE_METHODS:
            return request.user.groups.filter(name__in=['admin', 'inventory_manager', 'cashier']).exists()
        
        # Restrict write access to inventory managers and admins
        return request.user.groups.filter(name__in=['admin', 'inventory_manager']).exists()
    

   

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all().order_by('name')
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, IsAdminOrInventoryManager]
    

class ProductViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows products to be viewed or edited.
    """
    queryset = Product.objects.all().select_related('supplier').order_by('name')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, ProductAccessPermission]
    
    @action(detail=True, methods=['post'], url_path='restock')
    def restock(self, request, pk=None):
        product = self.get_object()
        serializer = RestockSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            # Update product quantity
            product.quantity += data['quantity_added']
            product.save()

            # Create history record
            RestockHistory.objects.create(
                product=product,
                user=request.user,
                quantity_added=data['quantity_added'],
                supplier_id=data['supplier_id'],
                cost_per_unit=data['cost_per_unit'],
                notes=data.get('notes', '')
            )
            
            # Return the updated product data
            return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Add this new ViewSet for the history
class RestockHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to view restock history.
    """
    queryset = RestockHistory.objects.all().select_related('product', 'supplier', 'user').order_by('-restock_date')
    serializer_class = RestockHistorySerializer
    permission_classes = [IsAuthenticated, IsAdminOrInventoryManager]
    

class DashboardStatsView(APIView):
    """
    Provides aggregated statistics for the main dashboard overview.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # 1. Total Revenue
        total_revenue = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or 0

        # 2. Products in Stock (sum of all quantities)
        products_in_stock = Product.objects.aggregate(total=Sum('quantity'))['total'] or 0

        # 3. Sales Today
        today = timezone.now().date()
        sales_today = Sale.objects.filter(created_at__date=today).count()

        # 4. Low Stock Alerts (e.g., quantity less than a threshold, here we use 10)
        low_stock_threshold = 10
        low_stock_alerts = Product.objects.filter(quantity__lt=low_stock_threshold).count()

        # 5. Expiring Soon (e.g., within the next 30 days)
        # This requires an 'expiry_date' field on the Product model.
        # We will add a placeholder for now and can implement this later.
        expiring_soon = 0 # Placeholder    
        
        data = {
            'total_revenue': total_revenue,
            'products_in_stock': products_in_stock,
            'sales_today': sales_today,
            'low_stock_alerts': low_stock_alerts,
            'expiring_soon': expiring_soon,
        }
        return Response(data, status=status.HTTP_200_OK)


# ViewSet for Sales at the end of the file
class SaleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for creating and viewing sales.
    - `POST /api/sales/`: Creates a new sale.
    - `GET /api/sales/`: Lists all past sales.
    """
    queryset = Sale.objects.all().order_by('-created_at')
    permission_classes = [IsAuthenticated, IsAdminOrCashier]

    def get_serializer_class(self):
        if self.action == 'create':
            return SaleCreateSerializer
        return SaleListSerializer

    def perform_create(self, serializer):
        # When a new sale is created, assign the current user to it.
        serializer.save(user=self.request.user)
        

class SettingsView(APIView):
    """
    View to manage system-wide settings.
    - GET: Retrieves all settings as a key-value object.
    - POST: Updates multiple settings at once.
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, *args, **kwargs):
        settings = Setting.objects.all()
        # Convert list of setting objects into a single dictionary
        data = {setting.key: setting.value for setting in settings}
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        settings_data = request.data
        for key, value in settings_data.items():
            # Update setting if it exists, or create it if it's new
            Setting.objects.update_or_create(
                key=key,
                defaults={'value': str(value)}
            )
        return Response({"message": "Settings updated successfully"}, status=status.HTTP_200_OK)
    
    
class PromotionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for creating and managing promotions.
    Only accessible by Admins and Inventory Managers.
    """
    queryset = Promotion.objects.all().order_by('-start_date')
    serializer_class = PromotionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrInventoryManager]
