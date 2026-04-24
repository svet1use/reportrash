from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from waste_management.models import Announcement, Notification

class Command(BaseCommand):
    help = 'Send notifications for new announcements'

    def add_arguments(self, parser):
        parser.add_argument('announcement_id', type=int)

    def handle(self, *args, **options):
        announcement_id = options['announcement_id']
        
        try:
            announcement = Announcement.objects.get(id=announcement_id)
            
            users = User.objects.filter(is_active=True)
            
            if announcement.target_barangay:
                users = users.filter(barangay_profile__barangay_name=announcement.target_barangay)
            
            notification_count = 0
            for user in users:
                Notification.objects.create(
                    user=user,
                    announcement=announcement,
                    title=announcement.title,
                    message=announcement.content[:100] + ('...' if len(announcement.content) > 100 else ''),
                    notification_type='announcement'
                )
                notification_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully sent {notification_count} notifications for "{announcement.title}"')
            )
            
        except Announcement.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Announcement with id {announcement_id} does not exist'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))