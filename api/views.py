from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework import viewsets
from django.contrib.auth.models import User
from .serializers import UserListSerializer, UserCreateSerializer, UserUpdateSerializer


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