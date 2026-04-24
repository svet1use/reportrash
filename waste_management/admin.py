from django.contrib import admin
from django.contrib import messages
from django.utils import timezone
from .models import BarangayProfile, WasteReport, CollectionSchedule, Announcement, CommunityPost, CommunityReply, Notification

class WasteReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'category', 'status', 'reporter', 'reported_at', 'points_awarded', 'is_duplicate']
    list_display_links = ['id', 'title']
    list_filter = ['category', 'status', 'is_duplicate', 'reported_at']
    search_fields = ['title', 'location', 'description', 'reporter__username']
    readonly_fields = ['points_awarded', 'reported_at', 'collected_at', 'image_preview']
    list_per_page = 25
    date_hierarchy = 'reported_at'
    actions = ['mark_as_pending', 'mark_as_collected', 'mark_as_processed', 'mark_as_disposed', 'clear_duplicate_flag']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('reporter', 'title', 'category', 'description')
        }),
        ('Location Details', {
            'fields': ('location', 'purok')
        }),
        ('Status & Points', {
            'fields': ('status', 'points_awarded', 'reported_at', 'collected_at')
        }),
        ('Duplicate Detection', {
            'fields': ('is_duplicate', 'duplicate_of'),
            'classes': ('collapse',),
        }),
        ('Photo Evidence', {
            'fields': ('image', 'image_preview'),
            'classes': ('collapse',)
        }),
        ('Additional Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" style="max-height: 100px; max-width: 100px; border-radius: 8px;" />'
        return "No image"
    image_preview.allow_tags = True
    image_preview.short_description = 'Preview'
    
    def mark_as_pending(self, request, queryset):
        queryset.update(status='pending')
        self.message_user(request, f"{queryset.count()} reports marked as pending.")
    mark_as_pending.short_description = "Mark selected as Pending"
    
    def mark_as_collected(self, request, queryset):
        queryset.update(status='collected', collected_at=timezone.now())
        self.message_user(request, f"{queryset.count()} reports marked as collected.")
    mark_as_collected.short_description = "Mark selected as Collected"
    
    def mark_as_processed(self, request, queryset):
        queryset.update(status='processed')
        self.message_user(request, f"{queryset.count()} reports marked as processed.")
    mark_as_processed.short_description = "Mark selected as Processed"
    
    def mark_as_disposed(self, request, queryset):
        queryset.update(status='disposed')
        self.message_user(request, f"{queryset.count()} reports marked as disposed.")
    mark_as_disposed.short_description = "Mark selected as Disposed"

    def clear_duplicate_flag(self, request, queryset):
        updated = queryset.update(is_duplicate=False, duplicate_of=None)
        self.message_user(request, f"{updated} reports cleared of duplicate flag.")
    clear_duplicate_flag.short_description = "Clear duplicate flag from selected"

admin.site.register(WasteReport, WasteReportAdmin)

@admin.register(CollectionSchedule)
class CollectionScheduleAdmin(admin.ModelAdmin):
    list_display = ['day_of_week', 'waste_category', 'time_start', 'time_end', 'purok', 'is_active']
    list_display_links = ['day_of_week', 'waste_category']
    list_filter = ['day_of_week', 'waste_category', 'is_active', 'purok']
    search_fields = ['purok', 'notes', 'collector_name']
    list_editable = ['is_active']
    list_per_page = 25
    
    fieldsets = (
        ('Schedule Details', {
            'fields': ('day_of_week', 'waste_category', 'time_start', 'time_end')
        }),
        ('Location & Personnel', {
            'fields': ('purok', 'collector_name')
        }),
        ('Status', {
            'fields': ('is_active', 'notes')
        }),
    )


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority', 'created_by', 'created_at', 'is_active', 'target_barangay', 'notification_sent']
    list_display_links = ['title']
    list_filter = ['priority', 'is_active', 'target_barangay', 'created_at']
    search_fields = ['title', 'content', 'created_by__username']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
    list_per_page = 25
    date_hierarchy = 'created_at'
    actions = ['send_notification_again']
    
    fieldsets = (
        ('Announcement Details', {
            'fields': ('title', 'content', 'priority', 'emoji')
        }),
        ('Target Audience', {
            'fields': ('target_barangay', 'send_notification'),
        }),
        ('Author & Status', {
            'fields': ('created_by', 'is_active', 'created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        
        if not change and obj.send_notification:
            from django.contrib.auth.models import User
            
            existing_count = Notification.objects.filter(announcement=obj).count()
            if existing_count == 0:
                users = User.objects.filter(is_active=True)
                if obj.target_barangay:
                    users = users.filter(barangay_profile__barangay_name=obj.target_barangay)
                
                for user in users:
                    Notification.objects.create(
                        user=user,
                        announcement=obj,
                        title=obj.title,
                        message=obj.content[:100] + ('...' if len(obj.content) > 100 else ''),
                        notification_type='announcement'
                    )
    
    def notification_sent(self, obj):
        return obj.send_notification
    notification_sent.short_description = 'Notification'
    notification_sent.boolean = True
    
    def send_notification_again(self, request, queryset):
        from django.core.management import call_command
        count = 0
        for announcement in queryset:
            try:
                call_command('send_notifications', str(announcement.id))
                count += 1
            except:
                pass
        self.message_user(request, f"Notifications resent for {count} announcements.")
    send_notification_again.short_description = "Send notification again"


@admin.register(BarangayProfile)
class BarangayProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'barangay_name', 'purok', 'points', 'level']
    list_display_links = ['user', 'barangay_name']
    list_filter = ['level', 'barangay_name', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'barangay_name', 'purok', 'contact_number']
    readonly_fields = ['points', 'level', 'created_at']
    list_per_page = 25
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'barangay_name', 'purok')
        }),
        ('Contact Details', {
            'fields': ('address', 'contact_number')
        }),
        ('Profile Picture', {
            'fields': ('profile_picture', 'avatar_color'),
            'classes': ('collapse',)
        }),
        ('Gamification', {
            'fields': ('points', 'level', 'created_at')
        }),
    )


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'content_preview', 'is_tip', 'like_count', 'created_at', 'image_status']
    list_display_links = ['id', 'content_preview']
    list_filter = ['is_tip', 'tip_category', 'created_at']
    search_fields = ['content', 'author__username', 'author__first_name', 'author__last_name']
    readonly_fields = ['created_at', 'like_count', 'image_preview']
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Post Content', {
            'fields': ('author', 'content', 'is_tip', 'tip_category')
        }),
        ('Media', {
            'fields': ('image', 'image_preview'),
            'classes': ('collapse',)
        }),
        ('Engagement', {
            'fields': ('likes', 'like_count', 'created_at')
        }),
    )
    filter_horizontal = ['likes']
    
    def content_preview(self, obj):
        return obj.content[:75] + '...' if len(obj.content) > 75 else obj.content
    content_preview.short_description = 'Content'
    
    def image_status(self, obj):
        if obj.image:
            return 'Yes'
        return 'No'
    image_status.short_description = 'Has Image'
    
    def image_preview(self, obj):
        if obj.image:
            return f'<img src="{obj.image.url}" style="max-height: 150px; max-width: 100%; border-radius: 8px;" />'
        return "No image uploaded"
    image_preview.allow_tags = True
    image_preview.short_description = 'Preview'


@admin.register(CommunityReply)
class CommunityReplyAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'content_preview', 'post_link', 'created_at']
    list_display_links = ['id', 'content_preview']
    search_fields = ['content', 'author__username', 'post__content']
    readonly_fields = ['created_at']
    list_per_page = 25
    list_filter = ['created_at']
    
    fieldsets = (
        ('Reply Details', {
            'fields': ('post', 'author', 'content')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Reply'
    
    def post_link(self, obj):
        return f'Post #{obj.post.id}'
    post_link.short_description = 'Post'
    post_link.admin_order_field = 'post'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'is_read', 'created_at']
    list_filter = ['is_read', 'notification_type', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['created_at']
    list_per_page = 25


admin.site.site_header = 'ReporTrash Administration'
admin.site.site_title = 'ReporTrash Admin'
admin.site.index_title = 'Dashboard'