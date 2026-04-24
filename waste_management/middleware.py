# middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class DisabledAccountMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                profile = request.user.barangay_profile
                # Check if user is disabled
                if profile.approval_status == 'disabled':
                    # Skip redirect for the disabled account page itself and logout
                    if not request.path.startswith('/disabled-account/') and not request.path.startswith('/logout/'):
                        return redirect('disabled_account')
            except Exception:
                pass
        return self.get_response(request)