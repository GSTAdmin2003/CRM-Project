from django.contrib import admin
from .models import Call, CallRecording, CallLog


class CallLogInline(admin.TabularInline):
    model = CallLog
    extra = 0
    readonly_fields = ['event', 'data', 'timestamp']
    can_delete = False


class CallRecordingInline(admin.StackedInline):
    model = CallRecording
    extra = 0
    readonly_fields = ['file', 'duration', 'file_size', 'created_at']
    can_delete = False


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'direction', 'status', 'from_number', 'to_number',
        'user', 'duration_formatted', 'started_at', 'created_at'
    ]
    list_filter = ['direction', 'status', 'created_at']
    search_fields = ['from_number', 'to_number', 'asterisk_channel_id', 'asterisk_uniqueid']
    readonly_fields = [
        'asterisk_channel_id', 'asterisk_uniqueid', 'started_at',
        'answered_at', 'ended_at', 'duration', 'created_at', 'updated_at'
    ]
    raw_id_fields = ['contact', 'opportunity', 'user']
    inlines = [CallRecordingInline, CallLogInline]
    date_hierarchy = 'created_at'


@admin.register(CallRecording)
class CallRecordingAdmin(admin.ModelAdmin):
    list_display = ['id', 'call', 'duration', 'file_size_formatted', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['call', 'duration', 'file_size', 'created_at']


@admin.register(CallLog)
class CallLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'call', 'event', 'timestamp']
    list_filter = ['event', 'timestamp']
    readonly_fields = ['call', 'event', 'data', 'timestamp']
