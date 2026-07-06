"""Dashboard-specific models: the admin audit trail (Section 5.2.16 / 11.11)."""
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """A record of a significant admin action for accountability."""
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="audit_events")
    action = models.CharField(max_length=80)
    target = models.CharField(max_length=200, blank=True)
    detail = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        who = self.actor or "system"
        return f"{who}: {self.action} — {self.target}"


def log_action(actor, action, target="", detail=""):
    """Convenience helper used by dashboard views to record admin actions."""
    try:
        AuditLog.objects.create(
            actor=actor if getattr(actor, "pk", None) else None,
            action=action, target=str(target)[:200], detail=str(detail)[:300],
        )
    except Exception:  # pragma: no cover - audit must never break a request
        pass
