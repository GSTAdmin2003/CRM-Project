from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Max

User = get_user_model()


def _next_extension() -> str:
    """Return the next available SIP extension (starts at 100, no gaps needed)."""
    existing = (
        User.objects.filter(extension__regex=r'^\d+$')
        .values_list('extension', flat=True)
    )
    nums = [int(e) for e in existing if e]
    return str(max(nums) + 1) if nums else '100'


class RoleSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='role.id')
    name = serializers.CharField(source='role.name')


class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    roles = RoleSerializer(source='user_roles', many=True, read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'is_active', 'extension', 'roles']


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    extension = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'extension', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        # Auto-assign extension if not provided
        if not validated_data.get('extension', '').strip():
            validated_data['extension'] = _next_extension()
        user = super().create(validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(update_fields=['password'])
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=['password'])
        return user
