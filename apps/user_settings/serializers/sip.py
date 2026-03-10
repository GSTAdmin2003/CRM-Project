from rest_framework import serializers
from apps.calls.models import SIPSettings


class SipSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="SIP password (write-only; stored encrypted)",
    )

    class Meta:
        model = SIPSettings
        fields = [
            'id',
            'server_ip',
            'server_port',
            'username',
            'password',
            'caller_id',
            'is_active',
            'registration_status',
            'last_registration_check',
            'working_hours_start',
            'working_hours_end',
            'working_days',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'registration_status', 'last_registration_check', 'created_at', 'updated_at']

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.password = password
            instance.save(update_fields=['_password'])
        return instance

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        instance = super().create(validated_data)
        if password:
            instance.password = password
            instance.save(update_fields=['_password'])
        return instance
