from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class BarangayProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='barangay_profile')
    barangay_name = models.CharField(max_length=100, default='Barangay 1')
    purok = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    avatar_color = models.CharField(max_length=7, default='#22c55e')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    points = models.IntegerField(default=0)
    level = models.CharField(max_length=50, default='Eco Starter')
    created_at = models.DateTimeField(auto_now_add=True)
    chat_mode = models.CharField(max_length=10, default='ai', choices=[('ai', 'AI Mode'), ('human', 'Human Mode')])
    chat_session_active = models.BooleanField(default=False)
    

    # Approval fields
    APPROVAL_PENDING  = 'pending'
    APPROVAL_APPROVED = 'approved'
    APPROVAL_REJECTED = 'rejected'
    APPROVAL_STATUS_CHOICES = [
        (APPROVAL_PENDING,  'Pending'),
        (APPROVAL_APPROVED, 'Approved'),
        (APPROVAL_REJECTED, 'Rejected'),
    ]
    approval_status = models.CharField(
        max_length=10,
        choices=APPROVAL_STATUS_CHOICES,
        default=APPROVAL_PENDING,
    )
    rejection_reason = models.TextField(blank=True, default='')

    # Settings fields
    notification_settings = models.JSONField(default=dict, blank=True)
    is_profile_public = models.BooleanField(default=True)
    show_email = models.BooleanField(default=False)
    show_location = models.BooleanField(default=True)
    allow_messages = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.barangay_name}"

    def update_level(self):
        if self.points >= 500:
            self.level = 'Eco Champion'
        elif self.points >= 200:
            self.level = 'Green Guardian'
        elif self.points >= 100:
            self.level = 'Eco Warrior'
        elif self.points >= 50:
            self.level = 'Eco Starter'
        else:
            self.level = 'Newcomer'
        self.save()

WASTE_CATEGORIES = [
    ('biodegradable', 'Biodegradable'),
    ('recyclable', 'Recyclable'),
    ('residual', 'Residual'),
    ('special', 'Special Waste'),
    ('hazardous', 'Hazardous'),
    ('electronic', 'E-Waste'),
]

STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('collected', 'Collected'),
    ('processed', 'Processed'),
    ('disposed', 'Disposed'),
]

CATEGORY_POINTS = {
    'biodegradable': 5,
    'recyclable': 10,
    'residual': 3,
    'special': 15,
    'hazardous': 20,
    'electronic': 25,
}


class WasteReport(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='waste_reports')
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=WASTE_CATEGORIES)
    location = models.CharField(max_length=200)
    purok = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    image = models.ImageField(upload_to='waste_reports/', blank=True, null=True)
    reported_at = models.DateTimeField(default=timezone.now)
    collected_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    points_awarded = models.IntegerField(default=0)
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin notes visible to the user")
    admin_notes_updated_at = models.DateTimeField(blank=True, null=True) 
    is_archived = models.BooleanField(default=False, db_index=True)
    is_draft = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)
  
    
    # Google Maps / Location fields
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    
    # Verification fields
    image_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    verification_passed = models.BooleanField(default=False)
    verification_data = models.JSONField(default=dict, blank=True)

    # Duplicate detection fields
    is_duplicate = models.BooleanField(default=False, db_index=True)
    duplicate_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='duplicate_reports',
    )

    class Meta:
        ordering = ['-reported_at']
        indexes = [
            models.Index(fields=['image_hash']),
            models.Index(fields=['verification_passed']),
            models.Index(fields=['status', 'reported_at']),
        ]

    def __str__(self):
        return f"{self.title} - {self.category} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            self.points_awarded = CATEGORY_POINTS.get(self.category, 5)
        super().save(*args, **kwargs)

    def has_flags(self):
     return self.flags.exists()

class CollectionSchedule(models.Model):
    DAYS = [
        ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    day_of_week = models.CharField(max_length=20, choices=DAYS)
    waste_category = models.CharField(max_length=50, choices=WASTE_CATEGORIES)
    time_start = models.TimeField()
    time_end = models.TimeField()
    purok = models.CharField(max_length=50, default='All')
    collector_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['day_of_week', 'time_start']

    def __str__(self):
        return f"{self.day_of_week} - {self.waste_category}"


class Announcement(models.Model):
    PRIORITY = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')]
    title = models.CharField(max_length=200)
    content = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY, default='medium')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    emoji = models.CharField(max_length=10, default='')
    target_barangay = models.CharField(max_length=100, blank=True, help_text="Leave blank for all barangays")
    send_notification = models.BooleanField(default=True, help_text="Send notification to all users")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and self.send_notification:
            from django.core.management import call_command
            try:
                call_command('send_notifications', str(self.id))
            except:
                pass


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('announcement', 'Announcement'),
        ('report', 'Report Update'),
        ('level_up', 'Level Up'),
        ('collection', 'Collection Reminder'),
        ('system', 'System'),
        ('like', 'Post Liked'),
        ('reply', 'New Reply'),
        ('share', 'Post Shared'),
        ('mention', 'Mentioned'),
        ('tag', 'Tagged in Post'),
        ('registration', 'New Registration'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, null=True, blank=True)
    related_report = models.ForeignKey('WasteReport', on_delete=models.SET_NULL, null=True, blank=True)
    related_post = models.ForeignKey('CommunityPost', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='triggered_notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='announcement')
    # URL to navigate to when the notification is clicked
    url = models.CharField(max_length=500, blank=True, default='')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"


class CommunityPost(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_posts')
    content = models.TextField()
    image = models.ImageField(upload_to='community/', blank=True, null=True)
    video = models.FileField(upload_to='community/videos/', blank=True, null=True)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_tip = models.BooleanField(default=False)
    tip_category = models.CharField(max_length=50, blank=True)
    tagged_users = models.ManyToManyField(
        User,
        through='PostTag',
        related_name='tagged_in_posts',
        blank=True,
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.author.username}: {self.content[:50]}"

    @property
    def like_count(self):
        return self.likes.count()


class PostTag(models.Model):
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='tags')
    tagged_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_tags')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'tagged_user']

    def __str__(self):
        return f"{self.post.id} -> {self.tagged_user.username}"


class CommunityReply(models.Model):
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='liked_replies', blank=True)
    parent_reply = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='child_replies')

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username}: {self.content[:30]}"
    
    @property
    def like_count(self):
        return self.likes.count()

class WasteStats(models.Model):
    month = models.DateField()
    total_biodegradable_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_recyclable_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_residual_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_special_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_hazardous_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_electronic_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_reports = models.IntegerField(default=0)
    collection_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        ordering = ['-month']

    def __str__(self):
        return f"Stats - {self.month.strftime('%B %Y')}"
    
class UserFollow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_set')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers_set')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['follower', 'following']

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


# ==================== TRASHBOT AI CHATBOT ====================

class ChatbotSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chatbot_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Session #{self.pk} - {self.user.username}"


class ChatbotMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    session = models.ForeignKey(ChatbotSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"
    
class DeletedReport(models.Model):
    """Archive table for deleted waste reports"""
    original_id = models.IntegerField(null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=50)
    status = models.CharField(max_length=30, null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    purok = models.CharField(max_length=100, blank=True, null=True)
    image = models.CharField(max_length=500, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    points_awarded = models.IntegerField(default=0, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    reporter_id = models.IntegerField(null=True, blank=True)
    reporter_username = models.CharField(max_length=150, blank=True, null=True)
    reporter_full_name = models.CharField(max_length=300, blank=True, null=True)
    reported_at = models.DateTimeField(null=True, blank=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(auto_now_add=True)
    deleted_by_id = models.IntegerField(null=True, blank=True)
    deleted_by_username = models.CharField(max_length=150, blank=True, null=True)
    deleted_by_role = models.CharField(max_length=10, default='user')

    class Meta:
        db_table = 'waste_management_deletedreport'
        managed = False
        ordering = ['-deleted_at']

    def __str__(self):
        return f"[DELETED] {self.title}"

# Add this to models.py after the DeletedReport model

class ReportFlag(models.Model):
    
    FLAG_TYPES = [
        ('duplicate', 'Duplicate Report'),
        ('suspicious', 'Suspicious / Unverified'),
        ('spam', 'Spam / Irrelevant'),
        ('incomplete', 'Incomplete Information'),
        ('invalid_location', 'Invalid Location'),
        ('invalid_image', 'Blurry / Invalid Image'),
        ('wrong_category', 'Wrong Category'),
        ('false_report', 'False Report (Confirmed)'),
        ('abusive', 'Abusive / Inappropriate Content'),
    ]
    
    report = models.ForeignKey(WasteReport, on_delete=models.CASCADE, related_name='flags')
    flagged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='flagged_reports')
    flag_type = models.CharField(max_length=50, choices=FLAG_TYPES)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['report', 'flag_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Flag {self.flag_type} on Report #{self.report.id}"
    
    def get_flag_display(self):
        return dict(self.FLAG_TYPES).get(self.flag_type, self.flag_type)
    
class ChatMessage(models.Model):
    """Chat messages between users and admins - Combined AI + Human support"""
    SENDER_CHOICES = [
        ('ai', 'AI Bot'),
        ('user', 'User'),
        ('admin', 'Admin'),
    ]
    STATUS_CHOICES = [
        ('ai_only', 'AI Only'),
        ('pending_human', 'Pending Human Admin'),
        ('human_active', 'Human Admin Active'),
        ('closed', 'Closed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    admin_reply_to = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    message = models.TextField()
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES, default='ai')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='ai_only')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_read']),
        ]
    
    def __str__(self):
        return f"Chat from {self.user.username}: {self.message[:50]}"