from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from ..models import SettingsCategory, SettingsPage

User = get_user_model()


class SettingsBaseMixin(LoginRequiredMixin):
    """Base mixin for all settings views"""
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings_categories'] = self.get_settings_navigation()
        context['current_section'] = self.get_current_section()
        context['current_page'] = self.get_current_page()
        return context
    
    def get_settings_navigation(self):
        """Get the settings navigation structure"""
        categories = SettingsCategory.objects.filter(is_active=True).prefetch_related('pages')
        nav_structure = []
        
        for category in categories:
            if self.user_has_category_access(category):
                pages = [page for page in category.pages.filter(is_active=True) 
                        if self.user_has_page_access(page)]
                if pages:
                    nav_structure.append({
                        'category': category,
                        'pages': pages
                    })
        
        return nav_structure
    
    def user_has_category_access(self, category):
        """Check if user has access to a category"""
        if category.name == 'general':
            return self.request.user.has_role('Owner') or self.request.user.has_role('IT Admin') or self.request.user.is_staff
        return True
    
    def user_has_page_access(self, page):
        """Check if user has access to a specific page"""
        if page.category.name == 'general':
            return self.request.user.has_role('Owner') or self.request.user.has_role('IT Admin') or self.request.user.is_staff
        return True
    
    def get_current_section(self):
        """Get the current settings section"""
        return getattr(self, 'settings_section', 'dashboard')
    
    def get_current_page(self):
        """Get the current settings page"""
        return getattr(self, 'settings_page', None)


