"""Capability-based access control helpers (role compliance)."""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def capability_required(capability):
    """Decorator: require the logged-in user's role to grant `capability`."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not request.user.can(capability):
                raise PermissionDenied(
                    f"Your role ({request.user.role_badge}) cannot access this."
                )
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator
