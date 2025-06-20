from django.contrib.auth.models import User, Group
from rest_framework import serializers

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