from .models import Notification


def notifications(request):
    """Add notifications (with url) to all templates."""
    if request.user.is_authenticated:
        notif_qs = Notification.objects.filter(
            user=request.user
        ).select_related('actor', 'related_report', 'related_post')[:10]

        unread_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()

        return {
            'notifications': notif_qs,
            'unread_notifications_count': unread_count,
        }
    return {
        'notifications': [],
        'unread_notifications_count': 0,
    }