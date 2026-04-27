from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from waste_management import views



urlpatterns = [
    # ========== CUSTOM ADMIN ROUTES (BEFORE Django admin) ==========
    path('dashboard/admin-chats/', views.admin_chat_page, name='admin_chat'),
    path('chat/', views.user_chat_page, name='user_chat'),

    # Dashboard admin routes
    path('dashboard/admin/reports/', views.admin_reports, name='admin_reports'),
    path('dashboard/admin/announcements/', views.admin_announcements, name='admin_announcements'),
    path('dashboard/admin/announcements/create/', views.create_announcement, name='create_announcement'),
    path('dashboard/admin/announcements/<int:announcement_id>/delete/', views.delete_announcement, name='delete_announcement'),
    path('dashboard/admin/announcements/<int:announcement_id>/edit/', views.edit_announcement, name='edit_announcement'),
    path('dashboard/admin/reports/bulk-update/', views.bulk_update_reports, name='bulk_update_reports'),
    path('dashboard/admin/reports/add-note/', views.add_admin_note, name='add_admin_note'),
    path('dashboard/admin/analytics/', views.admin_analytics, name='admin_analytics'),
    path('dashboard/admin/reports/<int:report_id>/delete/', views.admin_delete_report, name='admin_delete_report'),
    path('dashboard/admin/archive/', views.admin_archive, name='admin_archive'),
    path('dashboard/admin/reports/flag/', views.flag_report, name='flag_report'),
    path('dashboard/admin/reports/unflag/', views.unflag_report, name='unflag_report'),
    

    # Admin pending users
    path('dashboard/admin/pending-users/', views.admin_pending_users_view, name='admin_pending_users'),
    path('dashboard/admin/users/<int:user_id>/approve/', views.approve_user_view, name='approve_user'),
    path('dashboard/admin/users/<int:user_id>/reject/', views.reject_user_view, name='reject_user'),
    
    # ========== USER CHAT APIs ==========
    # User chat routes
    path('api/chat/user-history/', views.user_chat_history_api, name='user_chat_history'),
    path('api/chat/user-send/', views.user_chat_send_api, name='user_chat_send'),
    path('api/chat/request-human/', views.request_human_api, name='request_human_api'),
    path('api/chat/delete-conversation/', views.user_delete_conversation_api, name='user_delete_conversation'),
    
    # Legacy chat APIs (redirect or keep for compatibility)
    path('api/chat/send/', views.user_chat_send_api, name='chat_api'),
    path('api/chat/history/', views.user_chat_history_api, name='chat_history_api'),
    path('api/chat/clear/', views.user_delete_conversation_api, name='clear_chat_api'),
    
    # ========== ADMIN CHAT APIs ==========
    # Admin support chat routes
    path('api/admin/support-users/', views.admin_support_users_api, name='admin_support_users'),
    path('api/admin/support-messages/<int:user_id>/', views.admin_support_messages_api, name='admin_support_messages'),
    path('api/admin/support-reply/', views.admin_support_reply_api, name='admin_support_reply'),
    path('api/admin/close-chat/<int:user_id>/', views.admin_close_chat_api, name='admin_close_chat'),
    path('api/admin/delete-conversation/<int:user_id>/', views.admin_delete_conversation_api, name='admin_delete_conversation'),
    
    # ========== USER MANAGEMENT APIs ==========
    # Admin user management APIs
    path('api/admin/users/', views.admin_users_api, name='admin_users_api'),
    path('api/admin/users/save/', views.admin_user_save_api, name='admin_user_save_api'),
    path('api/admin/users/delete/', views.admin_user_delete_api, name='admin_user_delete_api'),
    path('api/admin/users/status/', views.admin_user_status_api, name='admin_user_status_api'),
    path('api/admin/user-detail/<int:user_id>/', views.admin_user_detail_api, name='admin_user_detail_api'),
    
    # ========== OTHER APIs ==========
    path('api/check-username/', views.check_username_exists, name='check_username'),
    path('api/forgot-password/', views.forgot_password_api, name='forgot_password'),
    path('api/stats/', views.api_stats, name='api_stats'),
    path('api/report/<int:report_id>/', views.get_report_details, name='get_report_details'),
    path('api/verify-image/', views.verify_image, name='verify_image'),
    path('api/mention-search/', views.mention_search, name='mention_search'),
    path('api/notifications/unread-count/', views.unread_notifications_count_api, name='unread_notifications_api'),
    
    # ========== CHATBOT APIs (Legacy/Backup) ==========
    path('api/chatbot/', views.chatbot_api, name='chatbot_api'),
    path('api/chatbot/history/', views.chatbot_history, name='chatbot_history'),
    
    # ========== DJANGO ADMIN (LAST - catch-all for admin/*) ==========
    path('admin/', admin.site.urls),
    
    # ========== AUTHENTICATION ==========
    path('', views.landing, name='landing'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('signup/', views.register_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    
    # ========== MAIN APP ROUTES ==========
    path('dashboard/', views.dashboard, name='dashboard'),
    path('report/', views.report_waste, name='report'),
    path('report/<int:report_id>/', views.view_report, name='view_report'),
    path('report/edit/<int:report_id>/', views.edit_report, name='edit_report'),
    path('report/delete/<int:report_id>/', views.delete_report, name='delete_report'),
    path('report/save-draft/', views.save_draft, name='save_draft'),
    path('report/draft/<int:report_id>/submit/', views.submit_draft, name='submit_draft'),
    path('report/<int:report_id>/status/', views.update_report_status, name='update_status'),
    path('history/', views.history, name='history'),
    
    # Community
    path('community/', views.community, name='community'),
    path('community/like/<int:post_id>/', views.toggle_like, name='toggle_like'),
    path('community/reply/<int:post_id>/', views.community_reply, name='community_reply'),
    path('community/post/<int:post_id>/edit/', views.edit_community_post, name='edit_community_post'),
    path('community/post/<int:post_id>/delete/', views.delete_community_post, name='delete_community_post'),
    path('community/reply/<int:reply_id>/edit/', views.edit_community_reply, name='edit_community_reply'),
    path('community/reply/<int:reply_id>/delete/', views.delete_community_reply, name='delete_community_reply'),
    path('community/reply/<int:reply_id>/like/', views.toggle_reply_like, name='toggle_reply_like'),
    path('community/post/<int:post_id>/share/', views.share_post, name='share_post'),
    path('community/report/', views.report_content, name='report_content'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/<str:username>/', views.user_profile, name='user_profile'),
    path('profile/<str:username>/follow/', views.toggle_follow, name='toggle_follow'),
    
    # Admin Profile
    path('admin-profile/', views.admin_profile_view, name='admin_profile'),
    path('admin-settings/', views.admin_settings_view, name='admin_settings'),
    
    # Settings
    path('settings/', views.settings_view, name='settings'),
    
    # Schedules
    path('schedules/', views.schedules, name='schedules'),
    
    # Notifications
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # Announcements
    path('announcements/', views.announcements, name='announcements'),
    
    # User following
    path('user/<str:username>/reports/', views.user_reports, name='user_reports'),
    path('my-following/', views.my_following, name='my_following'),
    path('my-followers/', views.my_followers, name='my_followers'),
    
    # Pending approval
    path('pending-approval/', views.pending_approval_view, name='pending_approval'),
    path('disabled-account/', views.disabled_account_view, name='disabled_account'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)