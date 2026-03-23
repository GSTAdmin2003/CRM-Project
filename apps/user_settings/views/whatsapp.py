import json

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.shortcuts import get_object_or_404, redirect
from django.urls import path
from django.views import View
from django.views.generic import FormView, ListView, TemplateView

from .base import SettingsBaseMixin


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.has_role("Owner") or self.request.user.has_role("IT Admin") or self.request.user.is_staff


class WhatsAppSettingsView(SettingsBaseMixin, AdminRequiredMixin, FormView):
    template_name = "settings/whatsapp/index.html"
    settings_section = "whatsapp"
    settings_page = "whatsapp_config"

    def _get_config(self):
        from apps.messaging.models import WhatsAppConfig

        return WhatsAppConfig.get_or_create_config()

    def get_form_class(self):
        from apps.user_settings.forms import get_whatsapp_config_form

        return get_whatsapp_config_form()

    def get_form(self, form_class=None):
        form_class = self.get_form_class()
        config = self._get_config()
        if self.request.method == "POST":
            return form_class(self.request.POST, instance=config)
        return form_class(instance=config)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["config"] = self._get_config()
        context["init_data_json"] = json.dumps({
            "apiUrls": {"credentials": "/settings/api/whatsapp/credentials/"}
        }, cls=DjangoJSONEncoder)
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "WhatsApp configuration saved successfully.")
        return redirect("settings:whatsapp:config")

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return self.render_to_response(self.get_context_data(form=form))


class WhatsAppTemplateListView(SettingsBaseMixin, AdminRequiredMixin, ListView):
    template_name = "settings/whatsapp/templates_list.html"
    settings_section = "whatsapp"
    settings_page = "whatsapp_templates"
    context_object_name = "templates"

    def get_queryset(self):
        from apps.messaging.models import WhatsAppTemplate

        return WhatsAppTemplate.objects.order_by("name", "language")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.messaging.models import WhatsAppConfig
        from itertools import groupby
        ctx['config'] = WhatsAppConfig.get_or_create_config()
        # Group templates by name so each template name is one table row
        grouped = []
        for _name, group in groupby(ctx['templates'], key=lambda t: t.name):
            grouped.append(list(group))
        ctx['template_groups'] = grouped
        ctx["init_data_json"] = json.dumps({
            "apiUrls": {
                "templates": "/settings/api/whatsapp/templates/",
                "refresh": "/settings/api/whatsapp/templates/refresh/",
                "templateDetail": "/settings/api/whatsapp/templates/{id}/",
                "submit": "/settings/api/whatsapp/templates/{id}/submit/",
                "deleteFromMeta": "/settings/api/whatsapp/templates/{id}/delete-from-meta/",
                "createUrl": "/settings/whatsapp/templates/add/",
            }
        }, cls=DjangoJSONEncoder)
        return ctx


class WhatsAppTemplateCreateView(SettingsBaseMixin, AdminRequiredMixin, FormView):
    template_name = "settings/whatsapp/template_form.html"
    settings_section = "whatsapp"
    settings_page = "whatsapp_templates"

    def get_form_class(self):
        from apps.user_settings.forms import get_whatsapp_template_form

        return get_whatsapp_template_form()

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Template created successfully.")
        return redirect("settings:whatsapp:templates_list")

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edit_mode"] = False
        context["init_data_json"] = json.dumps({
            "template": None,
            "apiUrls": {
                "templates": "/settings/api/whatsapp/templates/",
                "listUrl": "/settings/whatsapp/templates/",
            }
        }, cls=DjangoJSONEncoder)
        return context


class WhatsAppTemplateEditView(SettingsBaseMixin, AdminRequiredMixin, FormView):
    template_name = "settings/whatsapp/template_form.html"
    settings_section = "whatsapp"
    settings_page = "whatsapp_templates"

    def _get_template(self):
        from apps.messaging.models import WhatsAppTemplate

        return get_object_or_404(WhatsAppTemplate, pk=self.kwargs["pk"])

    def get_form_class(self):
        from apps.user_settings.forms import get_whatsapp_template_form

        return get_whatsapp_template_form()

    def get_form(self, form_class=None):
        form_class = self.get_form_class()
        instance = self._get_template()
        if self.request.method == "POST":
            return form_class(self.request.POST, instance=instance)
        return form_class(instance=instance)

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Template updated successfully.")
        return redirect("settings:whatsapp:templates_list")

    def form_invalid(self, form):
        messages.error(self.request, "Please correct the errors below.")
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["edit_mode"] = True
        t = self._get_template()
        context["template_obj"] = t
        context["init_data_json"] = json.dumps({
            "template": {
                "id": t.pk,
                "name": t.name,
                "display_name": t.display_name,
                "language": t.language,
                "body_preview": t.body_preview,
                "variable_names": t.variable_names,
                "is_active": t.is_active,
                "approval_status": t.approval_status,
            },
            "apiUrls": {
                "templates": "/settings/api/whatsapp/templates/",
                "templateDetail": f"/settings/api/whatsapp/templates/{t.pk}/",
                "listUrl": "/settings/whatsapp/templates/",
            }
        }, cls=DjangoJSONEncoder)
        return context


class WhatsAppTemplateDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        from apps.messaging.models import WhatsAppTemplate

        template = get_object_or_404(WhatsAppTemplate, pk=pk)
        template.delete()
        messages.success(request, "Template deleted.")
        return redirect("settings:whatsapp:templates_list")


class RefreshTemplateStatusesView(AdminRequiredMixin, View):
    def post(self, request):
        from apps.messaging.models import WhatsAppConfig, WhatsAppTemplate
        from apps.messaging.meta_client import fetch_template_details, _LANGUAGE_TO_LOCALE

        config = WhatsAppConfig.get_config()
        if not config or not config.can_submit_templates():
            messages.error(request, "WABA ID not configured. Set it in WhatsApp → Configuration.")
            return redirect("settings:whatsapp:templates_list")

        try:
            details = fetch_template_details(config.waba_id)
        except Exception as exc:
            messages.error(request, f"Failed to fetch statuses from Meta: {exc}")
            return redirect("settings:whatsapp:templates_list")

        updated = 0
        valid = {c[0] for c in WhatsAppTemplate._meta.get_field("approval_status").choices}
        for tmpl in WhatsAppTemplate.objects.all():
            locale = _LANGUAGE_TO_LOCALE.get(tmpl.language, tmpl.language)
            # Try mapped locale first (e.g. en_US), then bare language code (e.g. en)
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
                # Save the exact locale Meta uses so we can send with the correct code
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

        messages.success(request, f"Statuses refreshed from Meta. {updated} template(s) updated.")
        return redirect("settings:whatsapp:templates_list")


class SubmitTemplateApprovalView(AdminRequiredMixin, View):
    def post(self, request, pk):
        from apps.messaging.models import WhatsAppTemplate, WhatsAppConfig
        from apps.messaging.meta_client import submit_template_for_approval

        template = get_object_or_404(WhatsAppTemplate, pk=pk)
        config = WhatsAppConfig.get_config()
        if not config or not config.can_submit_templates():
            messages.error(request, "WABA ID not configured. Set it in WhatsApp → Configuration.")
            return redirect("settings:whatsapp:templates_list")

        # Only sales_pitch_* templates include a document header example
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
                        pass  # File missing on disk — submit body-only

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
            messages.success(request, f"'{template.display_name}' submitted for approval.")
        except Exception as exc:
            messages.error(request, f"Submission failed: {exc}")
        return redirect("settings:whatsapp:templates_list")


class DeleteFromMetaView(AdminRequiredMixin, View):
    """Delete a template from Meta (but keep the local DB record) and reset status to draft."""

    def post(self, request, pk):
        from apps.messaging.models import WhatsAppTemplate, WhatsAppConfig
        from apps.messaging.meta_client import delete_meta_template_by_name

        template = get_object_or_404(WhatsAppTemplate, pk=pk)
        config = WhatsAppConfig.get_config()
        if not config or not config.can_submit_templates():
            messages.error(request, "WABA ID not configured.")
            return redirect("settings:whatsapp:templates_list")

        try:
            found = delete_meta_template_by_name(config.waba_id, template.name)
            if found:
                messages.success(
                    request,
                    f"'{template.display_name}' deleted from Meta. "
                    "⏳ Wait 2–3 minutes before clicking Send for Approval — Meta needs time to process the deletion."
                )
            else:
                messages.success(request, f"'{template.display_name}' was already removed from Meta. Status reset to Draft.")
        except Exception as exc:
            messages.error(request, f"Delete failed: {exc}")
            return redirect("settings:whatsapp:templates_list")

        template.approval_status = "draft"
        template.meta_locale = ""
        template.save(update_fields=["approval_status", "meta_locale"])
        return redirect("settings:whatsapp:templates_list")


whatsapp_urls = [
    path("", WhatsAppSettingsView.as_view(), name="config"),
    path("templates/", WhatsAppTemplateListView.as_view(), name="templates_list"),
    path("templates/refresh-statuses/", RefreshTemplateStatusesView.as_view(), name="refresh_statuses"),
    path("templates/add/", WhatsAppTemplateCreateView.as_view(), name="template_create"),
    path("templates/<int:pk>/edit/", WhatsAppTemplateEditView.as_view(), name="template_edit"),
    path("templates/<int:pk>/delete/", WhatsAppTemplateDeleteView.as_view(), name="template_delete"),
    path("templates/<int:pk>/delete-from-meta/", DeleteFromMetaView.as_view(), name="template_delete_from_meta"),
    path("templates/<int:pk>/submit-approval/", SubmitTemplateApprovalView.as_view(), name="template_submit_approval"),
]
