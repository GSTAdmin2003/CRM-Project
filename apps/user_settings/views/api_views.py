"""
Settings REST API views — used by Svelte island components.
All views require authentication. Admin-only views enforce ownership/staff check.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import path
from rest_framework import status
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

User = get_user_model()


def _is_admin(user):
    return user.is_staff or (hasattr(user, 'has_role') and (user.has_role('Owner') or user.has_role('IT Admin')))


def _is_it_admin(user):
    return user.is_staff or (hasattr(user, 'has_role') and (user.has_role('IT Admin') or user.has_role('Owner')))


# ─── Profile ──────────────────────────────────────────────────────────────────

class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.user_settings.serializers.profile import ProfileSerializer
        return Response(ProfileSerializer(request.user).data)

    def patch(self, request):
        from apps.user_settings.serializers.profile import ProfileSerializer
        s = ProfileSerializer(request.user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.user_settings.serializers.profile import ChangePasswordSerializer
        s = ChangePasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        old_password = s.validated_data['old_password']
        new_password = s.validated_data['new_password']

        if not request.user.check_password(old_password):
            return Response(
                {'old_password': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(new_password, user=request.user)
        except DjangoValidationError as exc:
            return Response({'new_password': list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(new_password)
        request.user.save()
        return Response({'detail': 'Password changed successfully.'})


# ─── Users ────────────────────────────────────────────────────────────────────

class UserListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.user_settings.serializers.users import UserListSerializer

        qs = User.objects.prefetch_related('user_roles__role').order_by('-date_joined')

        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
            )

        status_filter = request.query_params.get('status', '').strip()
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'inactive':
            qs = qs.filter(is_active=False)

        return Response(UserListSerializer(qs, many=True).data)

    def post(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.user_settings.serializers.users import UserCreateUpdateSerializer
        from core.models import Role, UserRole
        s = UserCreateUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        role_ids = request.data.get('role_ids', [])
        if role_ids:
            for role in Role.objects.filter(id__in=role_ids, is_active=True):
                UserRole.objects.get_or_create(user=user, role=role, defaults={'assigned_by': request.user})
        return Response(UserCreateUpdateSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.user_settings.serializers.users import UserListSerializer
        user = get_object_or_404(User, pk=pk)
        return Response(UserListSerializer(user).data)

    def patch(self, request, pk):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.user_settings.serializers.users import UserCreateUpdateSerializer
        from core.models import Role, UserRole
        user = get_object_or_404(User, pk=pk)
        s = UserCreateUpdateSerializer(user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        if 'role_ids' in request.data:
            role_ids = request.data.get('role_ids', [])
            desired = set(Role.objects.filter(id__in=role_ids, is_active=True).values_list('id', flat=True))
            current = set(user.user_roles.values_list('role_id', flat=True))
            for role_id in current - desired:
                user.user_roles.filter(role_id=role_id).delete()
            for role_id in desired - current:
                role = Role.objects.get(id=role_id)
                UserRole.objects.create(user=user, role=role, assigned_by=request.user)
        return Response(s.data)


class UserToggleActiveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.user_settings.serializers.users import UserListSerializer
        target = get_object_or_404(User, pk=pk)

        if target.pk == request.user.pk:
            return Response(
                {'detail': 'You cannot deactivate your own account.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])
        return Response(UserListSerializer(target).data)


class RoleListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from core.models import Role
        roles = Role.objects.filter(is_active=True).values('id', 'name', 'description')
        return Response(list(roles))


# ─── General ──────────────────────────────────────────────────────────────────

class LanguageSettingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.user_settings.models.general import SystemConfiguration
        language = SystemConfiguration.get_setting('system_language', 'en')
        return Response({'language': language})

    def patch(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.user_settings.models.general import SystemConfiguration
        language = request.data.get('language', '').strip()
        if language not in ('en', 'ka'):
            return Response({'language': 'Must be "en" or "ka".'}, status=status.HTTP_400_BAD_REQUEST)
        SystemConfiguration.set_setting(
            key='system_language',
            value=language,
            description='System-wide default language',
            data_type='string',
            user=request.user,
        )
        return Response({'language': language})


# ─── SIP / VoIP ───────────────────────────────────────────────────────────────

class SipSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_or_create_sip(self, user):
        from apps.calls.models import SIPSettings
        sip, _ = SIPSettings.objects.get_or_create(
            user=user,
            defaults={
                'server_ip': '',
                'server_port': 5060,
                'username': '',
                '_password': '',
                'caller_id': '',
            },
        )
        return sip

    def get(self, request):
        from apps.user_settings.serializers.sip import SipSerializer
        sip = self._get_or_create_sip(request.user)
        return Response(SipSerializer(sip).data)

    def patch(self, request):
        from apps.user_settings.serializers.sip import SipSerializer
        sip = self._get_or_create_sip(request.user)
        s = SipSerializer(sip, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(SipSerializer(sip).data)


class VoipConfigAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_sip(self, user):
        from apps.calls.models import SIPSettings
        try:
            return user.sip_settings
        except SIPSettings.DoesNotExist:
            return None

    def get(self, request):
        if not _is_it_admin(request.user):
            return Response({'detail': 'IT admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.user_settings.serializers.sip import SipSerializer
        sip = self._get_sip(request.user)
        if sip is None:
            return Response({})
        return Response(SipSerializer(sip).data)

    def patch(self, request):
        if not _is_it_admin(request.user):
            return Response({'detail': 'IT admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.calls.models import SIPSettings
        from apps.user_settings.serializers.sip import SipSerializer
        sip, _ = SIPSettings.objects.get_or_create(
            user=request.user,
            defaults={
                'server_ip': '',
                'server_port': 5060,
                'username': '',
                '_password': '',
                'caller_id': '',
            },
        )
        s = SipSerializer(sip, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(SipSerializer(sip).data)


class WorkingHoursAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_sip(self, user):
        from apps.calls.models import SIPSettings
        try:
            return user.sip_settings
        except SIPSettings.DoesNotExist:
            return None

    def get(self, request):
        if not _is_it_admin(request.user):
            return Response({'detail': 'IT admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        sip = self._get_sip(request.user)
        if sip is None:
            return Response({'working_hours_start': None, 'working_hours_end': None, 'working_days': ''})
        return Response({
            'working_hours_start': sip.working_hours_start,
            'working_hours_end': sip.working_hours_end,
            'working_days': sip.working_days,
        })

    def patch(self, request):
        if not _is_it_admin(request.user):
            return Response({'detail': 'IT admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.calls.models import SIPSettings
        sip = self._get_sip(request.user)
        if sip is None:
            return Response(
                {'detail': 'Set up SIP credentials first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fields = {}
        if 'working_hours_start' in request.data:
            fields['working_hours_start'] = request.data['working_hours_start'] or None
        if 'working_hours_end' in request.data:
            fields['working_hours_end'] = request.data['working_hours_end'] or None
        if 'working_days' in request.data:
            fields['working_days'] = request.data['working_days']

        for attr, val in fields.items():
            setattr(sip, attr, val)
        if fields:
            sip.save(update_fields=list(fields.keys()))

        return Response({
            'working_hours_start': sip.working_hours_start,
            'working_hours_end': sip.working_hours_end,
            'working_days': sip.working_days,
        })


class VoipSoundsListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # No separate VoipSound model exists; sounds are fields on SIPSettings.
        # Return the sound file URLs from the current user's SIPSettings.
        from apps.calls.models import SIPSettings
        try:
            sip = request.user.sip_settings
        except SIPSettings.DoesNotExist:
            return Response({'hold_music': None, 'welcome_sound': None, 'non_working_hours_sound': None})

        def _url(field):
            if field and hasattr(field, 'url'):
                try:
                    return field.url
                except ValueError:
                    return None
            return None

        return Response({
            'hold_music': _url(sip.hold_music),
            'welcome_sound': _url(sip.welcome_sound),
            'non_working_hours_sound': _url(sip.non_working_hours_sound),
        })


class VoipSoundDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        # pk is used as a sound type identifier: 1=hold_music, 2=welcome_sound, 3=non_working_hours_sound
        # No separate VoipSound model — return 501 for generic deletes.
        return Response(
            {'detail': 'Sound deletion via API is not implemented. Use the settings form.'},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


# ─── WhatsApp ─────────────────────────────────────────────────────────────────

class WhatsAppCredentialsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_config(self):
        from apps.messaging.models import WhatsAppConfig
        return WhatsAppConfig.get_or_create_config()

    def get(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        config = self._get_config()
        return Response({
            'phone_number_id': config.phone_number_id,
            'waba_id': config.waba_id,
            'app_id': config.app_id,
            'webhook_verify_token': config.webhook_verify_token,
            'app_secret': config.app_secret,
            'access_token_set': bool(config.access_token),
            'is_active': config.is_active,
            'is_configured': config.is_configured(),
            'can_submit_templates': config.can_submit_templates(),
        })

    def patch(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        config = self._get_config()
        allowed = ['phone_number_id', 'waba_id', 'app_id', 'webhook_verify_token', 'app_secret', 'access_token', 'is_active']
        for field in allowed:
            if field in request.data:
                setattr(config, field, request.data[field])
        config.save()
        return Response({
            'phone_number_id': config.phone_number_id,
            'waba_id': config.waba_id,
            'app_id': config.app_id,
            'webhook_verify_token': config.webhook_verify_token,
            'app_secret': config.app_secret,
            'access_token_set': bool(config.access_token),
            'is_active': config.is_active,
            'is_configured': config.is_configured(),
            'can_submit_templates': config.can_submit_templates(),
        })


class WhatsAppTemplateListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.messaging.models import WhatsAppTemplate
        templates = WhatsAppTemplate.objects.all().values(
            'id', 'name', 'display_name', 'language', 'body_preview',
            'variable_names', 'meta_locale', 'is_active', 'approval_status',
            'created_at', 'updated_at',
        )
        return Response(list(templates))

    def post(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.messaging.models import WhatsAppTemplate
        required = ['name', 'display_name', 'language', 'body_preview']
        errors = {f: ['This field is required.'] for f in required if not request.data.get(f)}
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        template = WhatsAppTemplate.objects.create(
            name=request.data['name'],
            display_name=request.data['display_name'],
            language=request.data.get('language', 'en_US'),
            body_preview=request.data['body_preview'],
            variable_names=request.data.get('variable_names', []),
            is_active=request.data.get('is_active', True),
        )
        return Response({
            'id': template.id,
            'name': template.name,
            'display_name': template.display_name,
            'language': template.language,
            'body_preview': template.body_preview,
            'variable_names': template.variable_names,
            'meta_locale': template.meta_locale,
            'is_active': template.is_active,
            'approval_status': template.approval_status,
            'created_at': template.created_at,
            'updated_at': template.updated_at,
        }, status=status.HTTP_201_CREATED)


class WhatsAppTemplateDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_template(self, pk):
        from apps.messaging.models import WhatsAppTemplate
        return get_object_or_404(WhatsAppTemplate, pk=pk)

    def get(self, request, pk):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        t = self._get_template(pk)
        return Response({
            'id': t.id, 'name': t.name, 'display_name': t.display_name,
            'language': t.language, 'body_preview': t.body_preview,
            'variable_names': t.variable_names, 'meta_locale': t.meta_locale,
            'is_active': t.is_active, 'approval_status': t.approval_status,
            'created_at': t.created_at, 'updated_at': t.updated_at,
        })

    def put(self, request, pk):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        t = self._get_template(pk)
        updatable = ['name', 'display_name', 'language', 'body_preview', 'variable_names', 'is_active']
        for field in updatable:
            if field in request.data:
                setattr(t, field, request.data[field])
        t.save()
        return Response({
            'id': t.id, 'name': t.name, 'display_name': t.display_name,
            'language': t.language, 'body_preview': t.body_preview,
            'variable_names': t.variable_names, 'meta_locale': t.meta_locale,
            'is_active': t.is_active, 'approval_status': t.approval_status,
            'created_at': t.created_at, 'updated_at': t.updated_at,
        })

    def delete(self, request, pk):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        t = self._get_template(pk)
        t.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WhatsAppTemplateSubmitAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.messaging.models import WhatsAppTemplate, WhatsAppConfig
        from apps.messaging.meta_client import submit_template_for_approval

        template = get_object_or_404(WhatsAppTemplate, pk=pk)
        config = WhatsAppConfig.get_config()
        if not config or not config.can_submit_templates():
            return Response(
                {'error': 'WABA ID not configured. Set it in WhatsApp Credentials.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        header_file_path = ""
        header_filename = ""
        if template.name.startswith("sales_pitch"):
            from apps.crm.models import SalesTeam
            if template.language == 'ka':
                team = SalesTeam.objects.filter(is_active=True).exclude(pitch_pdf_ka='').first()
                pdf_field = 'pitch_pdf_ka'
                filename_field = 'pitch_pdf_filename_ka'
            else:
                team = SalesTeam.objects.filter(is_active=True).exclude(pitch_pdf='').first()
                pdf_field = 'pitch_pdf'
                filename_field = 'pitch_pdf_filename'
            if team:
                pdf_file = getattr(team, pdf_field)
                if pdf_file:
                    try:
                        header_file_path = pdf_file.path
                        header_filename = getattr(team, filename_field) or "sales_pitch.pdf"
                    except Exception:
                        pass

        try:
            submit_template_for_approval(
                config.waba_id,
                template.name,
                template.language,
                template.body_preview,
                header_file_path=header_file_path,
                header_filename=header_filename,
            )
            template.approval_status = 'pending'
            template.save(update_fields=['approval_status'])
            return Response({'success': True})
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class WhatsAppTemplateDeleteFromMetaAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.messaging.models import WhatsAppTemplate, WhatsAppConfig
        from apps.messaging.meta_client import delete_meta_template_by_name

        template = get_object_or_404(WhatsAppTemplate, pk=pk)
        config = WhatsAppConfig.get_config()
        if not config or not config.can_submit_templates():
            return Response({'error': 'WABA ID not configured.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            found = delete_meta_template_by_name(config.waba_id, template.name)
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        template.approval_status = "draft"
        template.meta_locale = ""
        template.save(update_fields=["approval_status", "meta_locale"])

        return Response({'success': True, 'was_found_on_meta': found})


class WhatsAppTemplateRefreshAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.messaging.models import WhatsAppConfig, WhatsAppTemplate
        from apps.messaging.meta_client import fetch_template_details, _LANGUAGE_TO_LOCALE

        config = WhatsAppConfig.get_config()
        if not config or not config.can_submit_templates():
            return Response(
                {'error': 'WABA ID not configured. Set it in WhatsApp Credentials.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            details = fetch_template_details(config.waba_id)
        except Exception as exc:
            return Response({'error': f'Failed to fetch statuses from Meta: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)

        updated = 0
        valid = {c[0] for c in WhatsAppTemplate._meta.get_field("approval_status").choices}
        for tmpl in WhatsAppTemplate.objects.all():
            locale = _LANGUAGE_TO_LOCALE.get(tmpl.language, tmpl.language)
            actual_locale = None
            meta = details.get((tmpl.name, locale))
            if meta:
                actual_locale = locale
            else:
                meta = details.get((tmpl.name, tmpl.language))
                if meta:
                    actual_locale = tmpl.language

            fields_to_save = []
            new_status = meta.get("status", "").lower() if meta else "draft"
            if new_status in valid and new_status != tmpl.approval_status:
                tmpl.approval_status = new_status
                fields_to_save.append("approval_status")

            if meta and actual_locale:
                if actual_locale != tmpl.meta_locale:
                    tmpl.meta_locale = actual_locale
                    fields_to_save.append("meta_locale")

                body_text = meta.get("body_text", "")
                var_count = meta.get("variable_count", 0)
                if body_text and body_text != tmpl.body_preview:
                    tmpl.body_preview = body_text
                    fields_to_save.append("body_preview")
                if var_count != len(tmpl.variable_names):
                    existing = list(tmpl.variable_names or [])
                    tmpl.variable_names = [
                        existing[i] if i < len(existing) else f"Variable {i + 1}"
                        for i in range(var_count)
                    ]
                    fields_to_save.append("variable_names")

            if fields_to_save:
                tmpl.save(update_fields=fields_to_save)
                updated += 1

        return Response({'updated': updated})


class WhatsAppPitchDefaultUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.messaging.services.whatsapp_service import WhatsAppService
        from core.exceptions import ValidationError as SvcError

        uploaded_file = request.FILES.get('pitch_pdf')
        if not uploaded_file:
            return Response({'error': 'pitch_pdf file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        language = request.data.get('language', 'en')
        if language not in ('en', 'ka'):
            language = 'en'

        try:
            WhatsAppService.upload_default_pitch_pdf(
                file=uploaded_file,
                filename=uploaded_file.name,
                language=language,
            )
        except SvcError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'success': True, 'language': language})

    def delete(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.messaging.models import WhatsAppConfig
        config = WhatsAppConfig.get_or_create_config()
        language = request.data.get('language', 'en')
        if language == 'ka':
            config.default_pitch_media_id_ka = ''
            config.default_pitch_filename_ka = ''
            config.save(update_fields=['default_pitch_media_id_ka', 'default_pitch_filename_ka'])
        else:
            config.default_pitch_media_id = ''
            config.default_pitch_filename = ''
            config.save(update_fields=['default_pitch_media_id', 'default_pitch_filename'])
        return Response({'success': True, 'language': language})


class WhatsAppTeamPitchUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request, team_pk):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.messaging.services.whatsapp_service import WhatsAppService
        from core.exceptions import NotFoundError, ValidationError as SvcError

        uploaded_file = request.FILES.get('pitch_pdf')
        if not uploaded_file:
            return Response({'error': 'pitch_pdf file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        language = request.data.get('language', 'en')
        if language not in ('en', 'ka'):
            language = 'en'

        try:
            WhatsAppService.upload_team_pitch_pdf(
                sales_team_id=team_pk,
                file=uploaded_file,
                filename=uploaded_file.name,
                language=language,
            )
        except (NotFoundError, SvcError) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'success': True, 'team_pk': team_pk, 'language': language})

    def delete(self, request, team_pk):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.crm.models import SalesTeam
        team = get_object_or_404(SalesTeam, pk=team_pk)
        language = request.data.get('language', 'en')
        if language == 'ka':
            if team.pitch_pdf_ka:
                team.pitch_pdf_ka.delete(save=False)
            team.pitch_pdf_media_id_ka = ''
            team.pitch_pdf_filename_ka = ''
            team.save(update_fields=['pitch_pdf_ka', 'pitch_pdf_media_id_ka', 'pitch_pdf_filename_ka'])
        else:
            if team.pitch_pdf:
                team.pitch_pdf.delete(save=False)
            team.pitch_pdf_media_id = ''
            team.pitch_pdf_filename = ''
            team.save(update_fields=['pitch_pdf', 'pitch_pdf_media_id', 'pitch_pdf_filename'])
        return Response({'success': True, 'team_pk': team_pk, 'language': language})


# ─── ElevenLabs / Transcription ───────────────────────────────────────────────

ELEVENLABS_KEY = 'elevenlabs_api_key'
KEYWORDS_KEY_EN = 'stt_keywords_en'
KEYWORDS_KEY_KA = 'stt_keywords_ka'
AUTO_TRANSCRIBE_KEY = 'transcription_auto_enabled'
ANTHROPIC_KEY = 'anthropic_api_key'
AI_AUTO_KEY = 'ai_analysis_auto_enabled'
AI_DEFAULT_DAYS_KEY = 'ai_activity_default_days'


class ElevenLabsConfigAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.user_settings.models.general import SystemConfiguration
        current_key = SystemConfiguration.get_setting(ELEVENLABS_KEY) or ''
        auto_transcribe = SystemConfiguration.get_setting(AUTO_TRANSCRIBE_KEY, False)
        return Response({
            'api_key_set': bool(current_key),
            'auto_transcribe': bool(auto_transcribe),
        })

    def patch(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.user_settings.models.general import SystemConfiguration
        action = request.data.get('action', 'save_key')

        if action == 'clear_key':
            SystemConfiguration.objects.filter(key=ELEVENLABS_KEY).delete()
            return Response({'api_key_set': False, 'auto_transcribe': bool(SystemConfiguration.get_setting(AUTO_TRANSCRIBE_KEY, False))})

        if action == 'save_key':
            raw = request.data.get('api_key', '').strip()
            if not raw:
                return Response({'api_key': 'API key cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)
            SystemConfiguration.set_setting(
                key=ELEVENLABS_KEY,
                value=raw,
                description='ElevenLabs API key for Speech-to-Text (Scribe)',
                data_type='string',
                user=request.user,
            )
            return Response({'api_key_set': True, 'auto_transcribe': bool(SystemConfiguration.get_setting(AUTO_TRANSCRIBE_KEY, False))})

        if action == 'save_auto_transcribe':
            enabled = bool(request.data.get('auto_transcribe', False))
            SystemConfiguration.set_setting(
                key=AUTO_TRANSCRIBE_KEY,
                value='true' if enabled else 'false',
                description='Automatically transcribe calls after recording is processed',
                data_type='boolean',
                user=request.user,
            )
            current_key = SystemConfiguration.get_setting(ELEVENLABS_KEY) or ''
            return Response({'api_key_set': bool(current_key), 'auto_transcribe': enabled})

        return Response({'action': f'Unknown action: {action}'}, status=status.HTTP_400_BAD_REQUEST)


class VocabularyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.user_settings.models.general import SystemConfiguration
        return Response({
            'en_keywords': SystemConfiguration.get_setting(KEYWORDS_KEY_EN) or '',
            'ka_keywords': SystemConfiguration.get_setting(KEYWORDS_KEY_KA) or '',
        })

    def patch(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.user_settings.models.general import SystemConfiguration
        SystemConfiguration.set_setting(
            key=KEYWORDS_KEY_EN,
            value=request.data.get('en_keywords', '').strip(),
            description='Default English custom vocabulary keywords for ElevenLabs STT',
            data_type='string',
            user=request.user,
        )
        SystemConfiguration.set_setting(
            key=KEYWORDS_KEY_KA,
            value=request.data.get('ka_keywords', '').strip(),
            description='Default Georgian custom vocabulary keywords for ElevenLabs STT',
            data_type='string',
            user=request.user,
        )
        return Response({
            'en_keywords': SystemConfiguration.get_setting(KEYWORDS_KEY_EN) or '',
            'ka_keywords': SystemConfiguration.get_setting(KEYWORDS_KEY_KA) or '',
        })


class AiConfigAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.user_settings.models.general import SystemConfiguration
        current_key = SystemConfiguration.get_setting(ANTHROPIC_KEY) or ''
        auto_enabled = SystemConfiguration.get_setting(AI_AUTO_KEY, False)
        default_days = int(SystemConfiguration.get_setting(AI_DEFAULT_DAYS_KEY, 1) or 1)
        return Response({
            'api_key_set': bool(current_key),
            'auto_analysis_enabled': bool(auto_enabled),
            'default_days': default_days,
        })

    def patch(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.user_settings.models.general import SystemConfiguration
        action = request.data.get('action', 'save_key')

        if action == 'clear_key':
            SystemConfiguration.objects.filter(key=ANTHROPIC_KEY).delete()
            auto_enabled = SystemConfiguration.get_setting(AI_AUTO_KEY, False)
            default_days = int(SystemConfiguration.get_setting(AI_DEFAULT_DAYS_KEY, 1) or 1)
            return Response({'api_key_set': False, 'auto_analysis_enabled': bool(auto_enabled), 'default_days': default_days})

        if action == 'save_key':
            raw = request.data.get('api_key', '').strip()
            if not raw:
                return Response({'api_key': 'API key cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)
            SystemConfiguration.set_setting(
                key=ANTHROPIC_KEY,
                value=raw,
                description='Anthropic API key for Claude AI call analysis',
                data_type='string',
                user=request.user,
            )
            auto_enabled = SystemConfiguration.get_setting(AI_AUTO_KEY, False)
            default_days = int(SystemConfiguration.get_setting(AI_DEFAULT_DAYS_KEY, 1) or 1)
            return Response({'api_key_set': True, 'auto_analysis_enabled': bool(auto_enabled), 'default_days': default_days})

        if action == 'save_auto_enabled':
            enabled = bool(request.data.get('auto_analysis_enabled', False))
            SystemConfiguration.set_setting(
                key=AI_AUTO_KEY,
                value='true' if enabled else 'false',
                description='Automatically run Claude AI analysis after transcription completes',
                data_type='boolean',
                user=request.user,
            )
            current_key = SystemConfiguration.get_setting(ANTHROPIC_KEY) or ''
            default_days = int(SystemConfiguration.get_setting(AI_DEFAULT_DAYS_KEY, 1) or 1)
            return Response({'api_key_set': bool(current_key), 'auto_analysis_enabled': enabled, 'default_days': default_days})

        if action == 'save_default_days':
            try:
                days = max(0, int(request.data.get('default_days', 1)))
            except (ValueError, TypeError):
                days = 1
            SystemConfiguration.set_setting(
                key=AI_DEFAULT_DAYS_KEY,
                value=str(days),
                description='Default scheduled interval (days from today) for AI-created activities',
                data_type='integer',
                user=request.user,
            )
            current_key = SystemConfiguration.get_setting(ANTHROPIC_KEY) or ''
            auto_enabled = SystemConfiguration.get_setting(AI_AUTO_KEY, False)
            return Response({'api_key_set': bool(current_key), 'auto_analysis_enabled': bool(auto_enabled), 'default_days': days})

        return Response({'action': f'Unknown action: {action}'}, status=status.HTTP_400_BAD_REQUEST)


class TeamProductsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.crm.models.sales_team import SalesTeam
        teams = SalesTeam.objects.filter(is_active=True).order_by('name').values('id', 'name', 'product_description')
        return Response({'teams': list(teams)})

    def patch(self, request):
        if not _is_admin(request.user):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

        from apps.crm.models.sales_team import SalesTeam
        team_id = request.data.get('team_id')
        if not team_id:
            return Response({'team_id': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        team = get_object_or_404(SalesTeam, pk=team_id)
        team.product_description = request.data.get('product_description', '').strip()
        team.save(update_fields=['product_description', 'updated_at'])
        return Response({'id': team.id, 'name': team.name, 'product_description': team.product_description})


# ─── URL patterns ─────────────────────────────────────────────────────────────

api_urlpatterns = [
    # Profile
    path('profile/', ProfileAPIView.as_view(), name='api_profile'),
    path('profile/change-password/', ChangePasswordAPIView.as_view(), name='api_change_password'),
    # Users
    path('users/', UserListAPIView.as_view(), name='api_users'),
    path('users/<int:pk>/', UserDetailAPIView.as_view(), name='api_user_detail'),
    path('users/<int:pk>/toggle-active/', UserToggleActiveAPIView.as_view(), name='api_user_toggle'),
    path('roles/', RoleListAPIView.as_view(), name='api_roles'),
    # General
    path('general/language/', LanguageSettingAPIView.as_view(), name='api_language'),
    # SIP/VoIP
    path('sip/', SipSettingsAPIView.as_view(), name='api_sip'),
    path('voip/config/', VoipConfigAPIView.as_view(), name='api_voip_config'),
    path('voip/working-hours/', WorkingHoursAPIView.as_view(), name='api_voip_working_hours'),
    path('voip/sounds/', VoipSoundsListAPIView.as_view(), name='api_voip_sounds'),
    path('voip/sounds/<int:pk>/', VoipSoundDeleteAPIView.as_view(), name='api_voip_sound_delete'),
    # WhatsApp
    path('whatsapp/credentials/', WhatsAppCredentialsAPIView.as_view(), name='api_whatsapp_credentials'),
    path('whatsapp/templates/', WhatsAppTemplateListCreateAPIView.as_view(), name='api_whatsapp_templates'),
    path('whatsapp/templates/refresh/', WhatsAppTemplateRefreshAPIView.as_view(), name='api_whatsapp_refresh'),
    path('whatsapp/templates/<int:pk>/', WhatsAppTemplateDetailAPIView.as_view(), name='api_whatsapp_template_detail'),
    path('whatsapp/templates/<int:pk>/submit/', WhatsAppTemplateSubmitAPIView.as_view(), name='api_whatsapp_submit'),
    path('whatsapp/templates/<int:pk>/delete-from-meta/', WhatsAppTemplateDeleteFromMetaAPIView.as_view(), name='api_whatsapp_delete_meta'),
    path('whatsapp/pitch/default/upload/', WhatsAppPitchDefaultUploadAPIView.as_view(), name='api_whatsapp_pitch_default'),
    path('whatsapp/pitch/teams/<int:team_pk>/upload/', WhatsAppTeamPitchUploadAPIView.as_view(), name='api_whatsapp_pitch_team'),
    # ElevenLabs
    path('elevenlabs/config/', ElevenLabsConfigAPIView.as_view(), name='api_elevenlabs_config'),
    path('elevenlabs/vocabulary/', VocabularyAPIView.as_view(), name='api_elevenlabs_vocabulary'),
    path('elevenlabs/ai/', AiConfigAPIView.as_view(), name='api_elevenlabs_ai'),
    path('elevenlabs/team-products/', TeamProductsAPIView.as_view(), name='api_elevenlabs_products'),
]
