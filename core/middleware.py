from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class RoleBasedAccessMiddleware:
    """Middleware to handle role-based access control"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs that don't require authentication
        self.public_urls = [
            reverse('login'),
            reverse('logout'),
            reverse('admin:login'),
            '/admin/login/',
            '/messaging/webhook/',
        ]
    
    def __call__(self, request):
        # Skip middleware for static files and media
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)
        
        # Skip middleware for public URLs
        if request.path in self.public_urls:
            return self.get_response(request)
        
        # Skip middleware for admin URLs (Django admin handles its own auth)
        if request.path.startswith('/admin/'):
            return self.get_response(request)
        
        # Check if user is authenticated
        if not request.user.is_authenticated:
            if request.path != reverse('login'):
                return redirect('login')
        
        response = self.get_response(request)
        return response