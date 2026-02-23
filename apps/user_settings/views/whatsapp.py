from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import path
from django.views import View
from django.views.generic import FormView, ListView, TemplateView

from .base import SettingsBaseMixin


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.has_role("Owner") or self.request.user.is_staff


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
        context["template_obj"] = self._get_template()
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
        from apps.messaging.meta_client import fetch_template_statuses, _LANGUAGE_TO_LOCALE

        config = WhatsAppConfig.get_config()
        if not config or not config.can_submit_templates():
            messages.error(request, "WABA ID not configured. Set it in WhatsApp → Configuration.")
            return redirect("settings:whatsapp:templates_list")

        try:
            statuses = fetch_template_statuses(config.waba_id)
        except Exception as exc:
            messages.error(request, f"Failed to fetch statuses from Meta: {exc}")
            return redirect("settings:whatsapp:templates_list")

        # Reverse map: locale → short code (e.g. "en_US" → "en")
        locale_to_lang = {v: k for k, v in _LANGUAGE_TO_LOCALE.items()}

        updated = 0
        valid = {c[0] for c in WhatsAppTemplate._meta.get_field("approval_status").choices}
        for tmpl in WhatsAppTemplate.objects.all():
            locale = _LANGUAGE_TO_LOCALE.get(tmpl.language, tmpl.language)
            meta_status = statuses.get((tmpl.name, locale), "")
            if meta_status:
                new_status = meta_status.lower()
            else:
                # Template not found on Meta (deleted/never submitted) → reset to draft
                new_status = "draft"
            if new_status in valid and new_status != tmpl.approval_status:
                tmpl.approval_status = new_status
                tmpl.save(update_fields=["approval_status"])
                updated += 1

        messages.success(request, f"Statuses refreshed from Meta. {updated} template(s) updated.")
        return redirect("settings:whatsapp:templates_list")


class SubmitTemplateApprovalView(AdminRequiredMixin, View):
    def post(self, request, pk):
        from apps.messaging.models import WhatsAppTemplate, WhatsAppConfig
        from apps.messaging.meta_client import submit_template_for_approval
        from apps.crm.models import SalesTeam

        template = get_object_or_404(WhatsAppTemplate, pk=pk)
        config = WhatsAppConfig.get_config()
        if not config or not config.can_submit_templates():
            messages.error(request, "WABA ID not configured. Set it in WhatsApp → Configuration.")
            return redirect("settings:whatsapp:templates_list")

        # Use a team's pitch PDF for this language as the sample HEADER example
        if template.language == 'ka':
            team = SalesTeam.objects.filter(is_active=True).exclude(pitch_pdf_ka='').first()
            pdf_field = 'pitch_pdf_ka'
            filename_field = 'pitch_pdf_filename_ka'
        else:
            team = SalesTeam.objects.filter(is_active=True).exclude(pitch_pdf='').first()
            pdf_field = 'pitch_pdf'
            filename_field = 'pitch_pdf_filename'

        header_file_path = ""
        header_filename = ""
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


whatsapp_urls = [
    path("", WhatsAppSettingsView.as_view(), name="config"),
    path("templates/", WhatsAppTemplateListView.as_view(), name="templates_list"),
    path("templates/refresh-statuses/", RefreshTemplateStatusesView.as_view(), name="refresh_statuses"),
    path("templates/add/", WhatsAppTemplateCreateView.as_view(), name="template_create"),
    path("templates/<int:pk>/edit/", WhatsAppTemplateEditView.as_view(), name="template_edit"),
    path("templates/<int:pk>/delete/", WhatsAppTemplateDeleteView.as_view(), name="template_delete"),
    path("templates/<int:pk>/submit-approval/", SubmitTemplateApprovalView.as_view(), name="template_submit_approval"),
]
