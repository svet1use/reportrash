from unittest import result

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from datetime import timedelta, date, datetime as dt
from PIL import Image
import json
import hashlib
import exifread
import numpy as np
import requests
import base64
from io import BytesIO
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings
from .models import UserFollow
from django.db.models import Q
import re
import json as _json
from django.db.models import Count, Q, Avg
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.core.mail import send_mail
from .models import ChatMessage

from .models import (
    BarangayProfile, WasteReport, CollectionSchedule, Announcement, 
    CommunityPost, CommunityReply, WasteStats, Notification, PostTag,
    ChatbotSession, ChatbotMessage, ReportFlag, DeletedReport,ChatMessage,
)


# ==================== HIVE AI DETECTION ====================

def check_ai_with_hive(image_file):
    """Check if image is AI-generated using Hive AI API"""
    try:
        HIVE_API_KEY = getattr(settings, 'HIVE_AI_API_KEY', None)
        
        if not HIVE_API_KEY:
            print("Hive AI API key not configured - skipping AI detection")
            return False, 0
        
        image_file.seek(0)
        image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        url = "https://api.thehive.ai/api/v2/task/sync"
        
        headers = {
            "Authorization": f"Token {HIVE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "media": image_data,
            "model": "general",
            "response_format": "json"
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            ai_scores = result.get('status', {}).get('ai_scores', {})
            
            is_ai_generated = False
            confidence = 0
            
            if 'ai_generated' in ai_scores:
                is_ai_generated = ai_scores['ai_generated'] > 0.5
                confidence = ai_scores['ai_generated']
            elif 'midjourney' in ai_scores:
                is_ai_generated = ai_scores['midjourney'] > 0.5
                confidence = ai_scores['midjourney']
            elif 'dalle' in ai_scores:
                is_ai_generated = ai_scores['dalle'] > 0.5
                confidence = ai_scores['dalle']
            elif 'stable_diffusion' in ai_scores:
                is_ai_generated = ai_scores['stable_diffusion'] > 0.5
                confidence = ai_scores['stable_diffusion']
            
            return is_ai_generated, confidence
        else:
            print(f"Hive AI API error: {response.status_code}")
            return False, 0
            
    except requests.exceptions.Timeout:
        print("Hive AI timeout - skipping")
        return False, 0
    except Exception as e:
        print(f"Hive AI error: {e}")
        return False, 0


# ==================== HELPER FUNCTIONS ====================

def create_notification(user, title, message, notification_type='system'):
    """Helper function to create a notification"""
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type
    )


# ==================== AUTHENTICATION VIEWS ====================

@ensure_csrf_cookie
def login_page(request):
    return render(request, 'login.html')

def landing(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'waste_management/landing.html')


def login_view(request):
    if request.user.is_authenticated:
        try:
            profile = request.user.barangay_profile
            # Check if account is disabled
            if profile.approval_status == 'disabled':
                return redirect('disabled_account')
            if profile.approval_status in ('pending', 'rejected'):
                return redirect('pending_approval')
        except Exception:
            pass
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # First, try to find the user by username or email
        user_obj = None
        try:
            # Try to find user by username
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                # Try to find user by email
                user_obj = User.objects.get(email=username)
            except User.DoesNotExist:
                pass
        
        # If user exists, check if they are disabled BEFORE authenticating
        if user_obj:
            try:
                profile = user_obj.barangay_profile
                if profile.approval_status == 'disabled':
                    # Return a specific error message for disabled accounts
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False, 
                            'error': 'Your account has been disabled. Please contact your barangay admin for assistance.',
                            'redirect': '/disabled-account/'
                        })
                    messages.error(request, 'Your account has been disabled. Please contact your barangay admin for assistance.')
                    return redirect('/login/')
            except BarangayProfile.DoesNotExist:
                pass
        
        # Now authenticate normally
        user = authenticate(request, username=username, password=password)

        if user:
            try:
                profile = BarangayProfile.objects.get(user=user)
                # Check if account is disabled first
                if profile.approval_status == 'disabled':
                    login(request, user)
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': True, 'redirect': '/disabled-account/'})
                    return redirect('disabled_account')
                if profile.approval_status in ('pending', 'rejected'):
                    login(request, user)
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'success': True, 'redirect': '/pending-approval/'})
                    return redirect('pending_approval')
            except BarangayProfile.DoesNotExist:
                BarangayProfile.objects.create(user=user, approval_status='pending')
                login(request, user)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'redirect': '/pending-approval/'})
                return redirect('pending_approval')

            login(request, user)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'redirect': '/dashboard/'})
            return redirect('/dashboard/')

        # Authentication failed
        error_message = 'Invalid credentials. Please try again.'
        
        # Check if user exists but password is wrong
        if user_obj:
            error_message = 'Invalid password. Please try again.'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': error_message})
        messages.error(request, error_message)
        return redirect('/login/')

    return render(request, 'waste_management/login.html')


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        barangay_name = request.POST.get('barangay_name', 'Barangay 1')
        purok = request.POST.get('purok', '')
 
        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': 'Username already taken.'})
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Email already registered.'})
 
        user = User.objects.create_user(
            username=username, email=email, password=password,
            first_name=first_name, last_name=last_name
        )
        BarangayProfile.objects.create(
            user=user,
            barangay_name=barangay_name,
            purok=purok,
            approval_status='pending',
        )
        login(request, user)
 
        full_name = f'{first_name} {last_name}'.strip() or username
        for admin_user in User.objects.filter(is_superuser=True):
            Notification.objects.create(
                user=admin_user,
                title='New Resident Registration',
                message=(
                    f'{full_name} (@{username}) has registered and is awaiting '
                    f'residency verification for {barangay_name}.'
                ),
                notification_type='registration',
                url='/dashboard/admin/pending-users/',
            )
 
        return JsonResponse({'success': True, 'redirect': '/pending-approval/'})
    return render(request, 'waste_management/login.html')

def logout_view(request):
    logout(request)
    return redirect('landing')


# ==================== DASHBOARD VIEWS ====================
@login_required
def disabled_account_view(request):
    """View for disabled account page"""
    try:
        profile = request.user.barangay_profile
        if profile.approval_status != 'disabled':
            # If user is not disabled, redirect to appropriate page
            if profile.approval_status == 'pending':
                return redirect('pending_approval')
            elif profile.approval_status == 'rejected':
                return redirect('pending_approval')
            else:
                return redirect('dashboard')
    except Exception:
        return redirect('login')
    
    return render(request, 'waste_management/disabled_account.html')

@login_required
def dashboard(request):
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    reports = WasteReport.objects.filter(reporter=request.user, is_draft=False)
    total_reports = reports.count()
    pending = reports.filter(status='pending').count()
    collected = reports.filter(status='collected').count()

    waste_by_cat = reports.values('category').annotate(total=Count('id'))
    cat_data = {item['category']: item['total'] for item in waste_by_cat}

    week_ago = timezone.now() - timedelta(days=7)
    recent = reports.filter(reported_at__gte=week_ago).count()

    _ann_qs = Announcement.objects.filter(is_active=True)
    if profile.purok:
        _ann_qs = _ann_qs.filter(
            Q(target_barangay__iexact=profile.purok) |
            Q(target_barangay='') |
            Q(target_barangay__isnull=True)
        )
    else:
        _ann_qs = _ann_qs.filter(
            Q(target_barangay='') | Q(target_barangay__isnull=True)
        )
    announcements = _ann_qs.order_by('-created_at')[:5]
    for ann in announcements:
        ann.content = mark_safe(ann.content)

    monthly_data = []
    for i in range(5, -1, -1):
        month_start = (timezone.now().replace(day=1) - timedelta(days=30*i))
        count = reports.filter(
            reported_at__year=month_start.year,
            reported_at__month=month_start.month
        ).count()
        monthly_data.append({'month': month_start.strftime('%b'), 'count': count})

    today = timezone.now().strftime('%A').lower()
    schedules_today = CollectionSchedule.objects.filter(day_of_week=today, is_active=True)

    context = {
        'profile': profile,
        'total_reports': total_reports,
        'pending': pending,
        'collected': collected,
        'recent': recent,
        'cat_data': json.dumps(cat_data),
        'monthly_data': json.dumps(monthly_data),
        'announcements': announcements,
        'schedules_today': schedules_today,
        'recent_reports': reports[:5],
    }
    
    if request.user.is_superuser:
        all_reports = WasteReport.objects.all()
        total_reports_all = all_reports.count()
        total_points = BarangayProfile.objects.aggregate(t=Sum('points'))['t'] or 0
        total_users = User.objects.count()
        
        recent_activities = []
        
        recent_users = User.objects.order_by('-date_joined')[:3]
        for user in recent_users:
            from django.utils.timesince import timesince
            time_ago = timesince(user.date_joined, timezone.now())
            recent_activities.append({
                'type': 'user',
                'title': f'New user registered: {user.username}',
                'time': f'{time_ago} ago'
            })
        
        recent_reports_all = WasteReport.objects.order_by('-reported_at')[:3]
        for report in recent_reports_all:
            from django.utils.timesince import timesince
            time_ago = timesince(report.reported_at, timezone.now())
            recent_activities.append({
                'type': 'report',
                'title': f'Report submitted: {report.title}',
                'time': f'{time_ago} ago'
            })
        
        recent_announcements = Announcement.objects.order_by('-created_at')[:2]
        for ann in recent_announcements:
            from django.utils.timesince import timesince
            time_ago = timesince(ann.created_at, timezone.now())
            recent_activities.append({
                'type': 'announcement',
                'title': f'Announcement: {ann.title}',
                'time': f'{time_ago} ago'
            })
        
        recent_community_posts_obj = CommunityPost.objects.order_by('-created_at')[:3]
        for post in recent_community_posts_obj:
            from django.utils.timesince import timesince
            time_ago = timesince(post.created_at, timezone.now())
            post_type = 'Eco Tip' if post.is_tip else 'Post'
            truncated_content = post.content[:50] + '...' if len(post.content) > 50 else post.content
            recent_activities.append({
                'type': 'community',
                'title': f'New {post_type}: {truncated_content} by {post.author.username}',
                'time': f'{time_ago} ago'
            })
        
        community_posts_count = CommunityPost.objects.count()
        community_replies_count = CommunityReply.objects.count()
        eco_tips_count = CommunityPost.objects.filter(is_tip=True).count()
        
        total_likes_count = 0
        for post in CommunityPost.objects.all():
            total_likes_count += post.like_count
        for reply in CommunityReply.objects.all():
            total_likes_count += reply.likes.count()
        
        recent_community_posts = CommunityPost.objects.all().order_by('-created_at')[:10]
        eco_tips_list = CommunityPost.objects.filter(is_tip=True).order_by('-created_at')[:10]
        recent_replies_list = CommunityReply.objects.all().order_by('-created_at')[:10]
        
        recent_notifications = Notification.objects.order_by('-created_at')[:5]
        notification_count = Notification.objects.count()
        
        weekly_labels = []
        weekly_data = []
        for i in range(6, -1, -1):
            day = timezone.now() - timedelta(days=i)
            weekly_labels.append(day.strftime('%a'))
            day_reports = WasteReport.objects.filter(
                reported_at__date=day.date()
            ).count()
            weekly_data.append(day_reports)
        
        waste_categories = ['biodegradable', 'recyclable', 'residual', 'special', 'hazardous', 'electronic']
        waste_labels = ['Biodegradable', 'Recyclable', 'Residual', 'Special', 'Hazardous', 'E-Waste']
        waste_colors = ['#22c55e', '#3b82f6', '#94a3b8', '#f59e0b', '#ef4444', '#a855f7']
        waste_data = []
        for cat in waste_categories:
            count = WasteReport.objects.filter(category=cat).count()
            waste_data.append(count)
        
        recent_users_qs = User.objects.order_by('-date_joined')[:10]
        recent_reports_qs = WasteReport.objects.select_related('reporter').order_by('-reported_at')[:10]

        context.update({
            'is_admin': True,
            'total_reports_all': total_reports_all,
            'total_users': total_users,
            'total_points': total_points,
            'recent_activities': recent_activities,
            'notification_count': notification_count,
            'recent_notifications': recent_notifications,
            'community_posts_count': community_posts_count,
            'community_replies_count': community_replies_count,
            'eco_tips_count': eco_tips_count,
            'total_likes_count': total_likes_count,
            'recent_community_posts': recent_community_posts,
            'eco_tips_list': eco_tips_list,
            'recent_replies_list': recent_replies_list,
            'weekly_labels': json.dumps(weekly_labels),
            'weekly_data': json.dumps(weekly_data),
            'waste_labels': json.dumps(waste_labels),
            'waste_data': json.dumps(waste_data),
            'waste_colors': json.dumps(waste_colors),
            'recent_reports': recent_reports_qs,
            'recent_users': recent_users_qs,
            'pending_count': BarangayProfile.objects.filter(approval_status='pending').count(),
            'pending_profiles_qs_temp': BarangayProfile.objects.filter(approval_status='pending').select_related('user')[:5],
        })
        return render(request, 'waste_management/admin_dashboard.html', context)
    
    notifications = Notification.objects.filter(user=request.user)[:10]
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    context.update({
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    })
    
    return render(request, 'waste_management/dashboard.html', context)


# ==================== REPORT VIEWS ====================

def get_points_for_category(category):
    points_map = {
        'biodegradable': 5,
        'recyclable': 10,
        'residual': 3,
        'special': 15,
        'hazardous': 20,
        'electronic': 25,
    }
    return points_map.get(category, 5)


def compute_image_hash(image_file):
    try:
        img = Image.open(image_file)
        img = img.resize((8, 8), Image.Resampling.LANCZOS).convert('L')
        pixels = list(img.getdata())
        avg = sum(pixels) / len(pixels)
        hash_bits = ''.join('1' if p > avg else '0' for p in pixels)
        return hex(int(hash_bits, 2))[2:].zfill(16)
    except Exception as e:
        return None


def check_duplicate_image(image_hash, user=None):
    if not image_hash:
        return False
    
    query = Q(image_hash=image_hash)
    if user:
        query &= Q(reported_at__gte=timezone.now() - timedelta(days=7))
    
    return WasteReport.objects.filter(query).exists()


def check_duplicate_report(location, category, purok='', within_hours=24):
    if not location or not category:
        return False, None

    cutoff = timezone.now() - timedelta(hours=within_hours)
    location_clean = location.strip().lower()

    candidates = WasteReport.objects.filter(
        category=category,
        reported_at__gte=cutoff,
        is_duplicate=False,
        is_draft=False,
    ).exclude(status='disposed')

    for report in candidates:
        if report.location.strip().lower() == location_clean:
            if purok and report.purok:
                if purok.strip().lower() != report.purok.strip().lower():
                    continue
            return True, report

    return False, None


def validate_waste_image(image_file):
    try:
        img = Image.open(image_file)
        
        width, height = img.size
        
        if width < 300 or height < 300:
            return False, "Image is too small or blurry. Please upload a clearer photo (minimum 300x300 pixels)."
        
        if width > 4000 or height > 4000:
            return False, "Image dimensions too large. Maximum size is 4000x4000 pixels."
        
        aspect_ratio = width / height
        if aspect_ratio > 3 or aspect_ratio < 0.33:
            return False, "Image has unusual dimensions. Please upload a normal photo."
        
        if image_file.size > 5 * 1024 * 1024:
            return False, "File size too large (max 5MB). Please compress your image."
        
        return True, "OK"
        
    except Exception as e:
        return False, f"Could not process image: {str(e)}"


# ==================== SAVE DRAFT VIEW ====================

@login_required
def save_draft(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    title = request.POST.get('title', '').strip()
    category = request.POST.get('category', '')
    location = request.POST.get('location', '').strip()
    purok = request.POST.get('purok', '')
    description = request.POST.get('description', '')
    image = request.FILES.get('image')
    latitude = request.POST.get('latitude')
    longitude = request.POST.get('longitude')
    address = request.POST.get('address', '')
    
    if not title:
        return JsonResponse({'success': False, 'error': 'Title is required to save a draft.'})
    
    report = WasteReport.objects.create(
        reporter=request.user,
        title=title,
        category=category or 'residual',
        location=location or 'Draft - location not set',
        purok=purok,
        description=description,
        image=image,
        points_awarded=0,
        latitude=float(latitude) if latitude else None,
        longitude=float(longitude) if longitude else None,
        address=address,
        status='pending',
        is_draft=True,
    )
    
    return JsonResponse({
        'success': True,
        'draft_id': report.id,
        'message': 'Draft saved! You can submit it later from History.'
    })


@login_required
def submit_draft(request, report_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    report = get_object_or_404(WasteReport, id=report_id, reporter=request.user, is_draft=True)
    
    report.is_draft = False
    points = get_points_for_category(report.category)
    report.points_awarded = points
    report.save()
    
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    profile.points += points
    profile.update_level()
    
    Notification.objects.create(
        user=request.user,
        title='Draft Report Submitted!',
        message=f'Your draft report "{report.title}" has been submitted. +{points} points earned.',
        notification_type='report',
        related_report=report,
    )
    
    return JsonResponse({
        'success': True,
        'message': f'Report submitted! +{points} points earned!',
        'points': points,
    })


@login_required
def report_waste(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        category = request.POST.get('category')
        location = request.POST.get('location')
        purok = request.POST.get('purok', '')
        description = request.POST.get('description', '')
        image = request.FILES.get('image')
        
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        address = request.POST.get('address', '')
        
        exif_passed = request.POST.get('exif_passed') == 'true'
        ai_passed = request.POST.get('ai_passed') == 'true'
        hash_passed = request.POST.get('hash_passed') == 'true'
        verification_data = request.POST.get('verification_data', '{}')
        requires_manual_review = request.POST.get('requires_manual_review') == 'true'
        verification_attempts = int(request.POST.get('verification_attempts', 0))
        
        try:
            verification_data = json.loads(verification_data)
        except:
            verification_data = {}
        
        verification_data['requires_manual_review'] = requires_manual_review
        verification_data['verification_attempts'] = verification_attempts

        profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
        points = get_points_for_category(category)
        
        image_hash = None
        duplicate_check = False
        
        if image:
            is_valid, validation_message = validate_waste_image(image)
            if not is_valid:
                return JsonResponse({
                    'success': False, 
                    'error': validation_message
                })
            
            image_hash = compute_image_hash(image)
            duplicate_check = check_duplicate_image(image_hash, request.user)
            
            if duplicate_check:
                return JsonResponse({
                    'success': False, 
                    'error': 'Duplicate image detected. This image has been submitted before.'
                })
        
        verification_passed = (exif_passed and ai_passed and hash_passed and not duplicate_check)

        is_content_duplicate, original_report = check_duplicate_report(
            location=location,
            category=category,
            purok=purok,
            within_hours=24,
        )

        if is_content_duplicate and original_report:
            report = WasteReport.objects.create(
                reporter=request.user,
                title=title,
                category=category,
                location=location,
                purok=purok,
                description=description,
                image=image,
                points_awarded=0,
                latitude=float(latitude) if latitude else None,
                longitude=float(longitude) if longitude else None,
                address=address,
                image_hash=image_hash,
                verification_passed=verification_passed,
                verification_data=verification_data,
                is_duplicate=True,
                duplicate_of=original_report,
                is_draft=False,
            )

            Notification.objects.create(
                user=request.user,
                title='Duplicate Report Detected',
                message=(
                    f'Your report "{title}" appears to already have been reported '
                    f'at {location}. It has been recorded and linked to the '
                    f'existing report (#{original_report.id}). No points were '
                    f'awarded to avoid duplicate rewards.'
                ),
                notification_type='report',
                related_report=report,
                url=f'/report/{original_report.id}/',
            )

            return JsonResponse({
                'success': True,
                'duplicate': True,
                'message': (
                    f'⚠️ This issue at "{location}" has already been reported '
                    f'(Report #{original_report.id}). Your report has been '
                    f'recorded but no points were awarded.'
                ),
                'original_report_id': original_report.id,
                'points': 0,
            })

        report = WasteReport.objects.create(
            reporter=request.user,
            title=title,
            category=category,
            location=location,
            purok=purok,
            description=description,
            image=image,
            points_awarded=points,
            latitude=float(latitude) if latitude else None,
            longitude=float(longitude) if longitude else None,
            address=address,
            image_hash=image_hash,
            verification_passed=verification_passed,
            verification_data=verification_data,
            is_duplicate=False,
            duplicate_of=None,
            is_draft=False,
        )

        profile.points += points
        profile.update_level()
        
        Notification.objects.create(
            user=request.user,
            title='Report Submitted!',
            message=f'Your report "{title}" has been submitted successfully! +{points} points earned.',
            notification_type='report',
            related_report=report,
        )

        category_display = dict([
            ('biodegradable', 'Biodegradable'), ('recyclable', 'Recyclable'),
            ('residual', 'Residual'), ('special', 'Special Waste'),
            ('hazardous', 'Hazardous'), ('electronic', 'E-Waste'),
        ]).get(category, category.title())

        for admin_user in User.objects.filter(is_superuser=True):
            Notification.objects.create(
                user=admin_user,
                title=f'New {category_display} Report',
                message=f'{request.user.username} submitted "{title}" at {location}.',
                notification_type='report',
            )

        return JsonResponse({
            'success': True,
            'message': f'Report submitted! +{points} points earned!',
            'points': points,
            'verification_passed': verification_passed
        })

    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    schedules = CollectionSchedule.objects.filter(is_active=True)
    return render(request, 'waste_management/report.html', {'profile': profile, 'schedules': schedules})


@login_required
def history(request):
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    # Show all reports including drafts
    reports = WasteReport.objects.filter(reporter=request.user)

    category_filter = request.GET.get('category', '')
    status_filter = request.GET.get('status', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'newest')
    draft_filter = request.GET.get('draft', '')

    if category_filter:
        reports = reports.filter(category=category_filter)
    if status_filter:
        reports = reports.filter(status=status_filter)
    if draft_filter == 'true':
        reports = reports.filter(is_draft=True)
    elif draft_filter == 'false':
        reports = reports.filter(is_draft=False)
    if start_date:
        try:
            reports = reports.filter(reported_at__date__gte=date.fromisoformat(start_date))
        except Exception:
            pass
    if end_date:
        try:
            reports = reports.filter(reported_at__date__lte=date.fromisoformat(end_date))
        except Exception:
            pass
    if search_query:
        reports = reports.filter(
            Q(title__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__icontains=search_query)
        )

    if sort_by == 'oldest':
        reports = reports.order_by('reported_at')
    elif sort_by == 'points_high':
        reports = reports.order_by('-points_awarded')
    elif sort_by == 'points_low':
        reports = reports.order_by('points_awarded')
    elif sort_by == 'category':
        reports = reports.order_by('category', '-reported_at')
    else:
        reports = reports.order_by('-reported_at')

    total_points = reports.filter(is_draft=False).aggregate(t=Sum('points_awarded'))['t'] or 0
    draft_count = reports.filter(is_draft=True).count()
    submitted_count = reports.filter(is_draft=False).count()

    week_ago = timezone.now() - timedelta(days=7)
    week_count = reports.filter(is_draft=False, reported_at__gte=week_ago).count()

    category_counts = reports.filter(is_draft=False).values('category').annotate(count=Count('id')).order_by('-count')
    best_category = category_counts[0]['category'] if category_counts else 'Recyclable'

    all_profiles = BarangayProfile.objects.select_related('user').order_by('-points')
    user_rank = 0
    for index, prof in enumerate(all_profiles):
        if prof.user == request.user:
            user_rank = index + 1
            break
    total_users = all_profiles.count()

    context = {
        'profile': profile,
        'reports': reports,
        'total_points': total_points or 0,
        'draft_count': draft_count,
        'submitted_count': submitted_count,
        'category_filter': category_filter,
        'status_filter': status_filter,
        'start_date': start_date,
        'end_date': end_date,
        'search_query': search_query,
        'sort_by': sort_by,
        'week_count': week_count,
        'best_category': best_category.capitalize(),
        'community_rank': user_rank,
        'total_users': total_users,
        'weekly_growth': 12,
        'user_level': profile.level,
        'has_more': reports.count() > 20,
    }
    return render(request, 'waste_management/history.html', context)


@login_required
def edit_report(request, report_id):
    report = get_object_or_404(WasteReport, id=report_id, reporter=request.user)
    
    if request.method == 'POST':
        old_title = report.title
        report.title = request.POST.get('title')
        report.description = request.POST.get('description')
        report.category = request.POST.get('category')
        report.location = request.POST.get('location')
        report.purok = request.POST.get('purok')
        
        report.save()
        
        create_notification(
            request.user,
            'Report Updated',
            f'Your report "{old_title}" has been updated successfully.',
            'report'
        )
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Report updated successfully!'})
        messages.success(request, 'Report updated successfully!')
        return redirect('history')
    
    categories = [
        ('biodegradable', 'Biodegradable'),
        ('recyclable', 'Recyclable'),
        ('residual', 'Residual'),
        ('special', 'Special'),
        ('hazardous', 'Hazardous'),
        ('electronic', 'E-Waste'),
    ]
    
    context = {
        'report': report,
        'categories': categories,
    }
    return render(request, 'waste_management/edit_report.html', context)


@login_required
def delete_report(request, report_id):
    report = get_object_or_404(WasteReport, id=report_id, reporter=request.user)

    if request.method == 'POST':
        title = report.title
        points_lost = report.points_awarded if not report.is_draft else 0
        
        try:
            from .models import DeletedReport
            DeletedReport.objects.create(
                original_id=report.id,
                title=report.title,
                description=report.description or '',
                category=report.category,
                status=report.status,
                location=report.location or '',
                purok=report.purok or '',
                image=report.image.url if report.image else '',
                notes=report.notes or '',
                points_awarded=report.points_awarded or 0,
                latitude=getattr(report, 'latitude', None),
                longitude=getattr(report, 'longitude', None),
                reporter_id=report.reporter.id,
                reporter_username=report.reporter.username,
                reporter_full_name=report.reporter.get_full_name(),
                reported_at=report.reported_at,
                collected_at=getattr(report, 'collected_at', None),
                deleted_by_id=request.user.id,
                deleted_by_username=request.user.username,
                deleted_by_role='user',
            )
        except Exception as e:
            print(f"Archive error: {e}")
        
        if points_lost > 0:
            profile = BarangayProfile.objects.get(user=request.user)
            profile.points -= points_lost
            if profile.points < 0:
                profile.points = 0
            profile.update_level()
        
        report.delete()
        
        create_notification(request.user, 'Report Deleted', f'Your report "{title}" has been deleted.', 'system')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Report deleted successfully!'})
        messages.success(request, 'Report deleted successfully!')
        return redirect('history')
    
    context = {'report': report}
    return render(request, 'waste_management/confirm_delete.html', context)


@login_required
def update_report_status(request, report_id):
    if request.method == 'POST':
        report = get_object_or_404(WasteReport, id=report_id)
        new_status = request.POST.get('status')
        old_status = report.status
        is_restore = request.POST.get('restore') == 'true'
        
        # Update status
        report.status = new_status
        
        # Auto-archive when status is resolved
        if new_status == 'resolved' and old_status != 'resolved':
            report.is_archived = True
            report.archived_at = timezone.now()
        elif new_status != 'resolved' and report.is_archived and not is_restore:
            # Don't auto-unarchive, only manual restore
            pass
        
        # Handle restore from archive
        if is_restore:
            report.is_archived = False
            report.archived_at = None
            report.status = 'pending'  # Set to pending when restored
        
        if new_status == 'collected':
            report.collected_at = timezone.now()
        
        report.save()
        
        # Create notification for user
        if new_status != old_status and not report.is_draft:
            Notification.objects.create(
                user=report.reporter,
                title=f'Report {new_status.title()}',
                message=f'Your report "{report.title}" has been marked as {new_status}.',
                notification_type='report',
                related_report=report,
            )
        
        return JsonResponse({
            'success': True, 
            'status': new_status, 
            'is_archived': report.is_archived
        })
    return JsonResponse({'success': False})

@login_required
def api_stats(request):
    """API endpoint to get user statistics for dashboard"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)

    reports = WasteReport.objects.filter(reporter=request.user, is_draft=False)
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)

    return JsonResponse({
        'total_reports': reports.count(),
        'points': profile.points,
        'level': profile.level,
    })

# ==================== MENTION HELPER FUNCTION ====================

def _process_mentions(content, actor, related_post):
    import re
    mentioned_usernames = set(re.findall(r'@(\w+)', content))
    for username in mentioned_usernames:
        try:
            mentioned_user = User.objects.get(username=username)
            if mentioned_user != actor:
                actor_name = actor.get_full_name() or actor.username
                Notification.objects.create(
                    user=mentioned_user,
                    actor=actor,
                    related_post=related_post,
                    notification_type='mention',
                    title=f'{actor_name} mentioned you',
                    message=content[:150] + ('...' if len(content) > 150 else ''),
                )
        except User.DoesNotExist:
            pass


# ==================== COMMUNITY VIEWS ====================

@login_required
def community(request):
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    posts = CommunityPost.objects.all().select_related(
        'author', 'author__barangay_profile'
    ).prefetch_related('replies', 'replies__author', 'tags', 'tags__tagged_user')
    tips = CommunityPost.objects.filter(is_tip=True)[:6]
    reports_for_map = WasteReport.objects.filter(
        latitude__isnull=False, longitude__isnull=False, is_draft=False
    ).order_by('-reported_at')[:100]
    community_map_json = json.dumps([
        {
            'lat': float(r.latitude),
            'lng': float(r.longitude),
            'title': r.title,
            'category': r.category,
            'purok': r.purok,
            'date': r.reported_at.strftime('%b %d, %Y'),
        }
        for r in reports_for_map
    ])

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        image = request.FILES.get('image')
        video = request.FILES.get('video')
        is_tip = request.POST.get('is_tip') == 'true'
        tip_category = request.POST.get('tip_category', '')
        tagged_usernames = request.POST.getlist('tagged_users[]')

        if not content:
            return JsonResponse({'success': False, 'error': 'Content is required'})

        post = CommunityPost.objects.create(
            author=request.user,
            content=content,
            image=image,
            video=video,
            is_tip=is_tip,
            tip_category=tip_category,
        )

        for username in tagged_usernames:
            try:
                tagged_user = User.objects.get(username=username)
                if tagged_user != request.user:
                    PostTag.objects.get_or_create(post=post, tagged_user=tagged_user)
                    actor_name = request.user.get_full_name() or request.user.username
                    Notification.objects.create(
                        user=tagged_user,
                        actor=request.user,
                        related_post=post,
                        notification_type='tag',
                        title=f'{actor_name} tagged you in a post',
                        message=content[:100] + ('...' if len(content) > 100 else ''),
                    )
            except User.DoesNotExist:
                pass

        _process_mentions(content, request.user, post)

        post_type = 'Eco Tip' if is_tip else 'Community Post'
        preview = content[:60] + ('...' if len(content) > 60 else '')
        for admin_user in User.objects.filter(is_superuser=True):
            Notification.objects.create(
                user=admin_user,
                title=f'New {post_type}',
                message=f'{request.user.username}: "{preview}"',
                notification_type='system',
            )

        return JsonResponse({'success': True, 'post_id': post.id})

    context = {
        'profile': profile,
        'posts': posts,
        'tips': tips,
        'reports_for_map': reports_for_map,
        'community_map_json': community_map_json,
    }
    return render(request, 'waste_management/community.html', context)


@login_required
def community_reply(request, post_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})

    post = get_object_or_404(CommunityPost, id=post_id)
    content = request.POST.get('content', '').strip()
    parent_reply_id = request.POST.get('parent_reply_id')

    if not content:
        return JsonResponse({'success': False})

    parent_reply = None
    if parent_reply_id:
        parent_reply = get_object_or_404(CommunityReply, id=parent_reply_id)

    reply = CommunityReply.objects.create(
        post=post,
        author=request.user,
        content=content,
        parent_reply=parent_reply
    )

    _process_mentions(content, request.user, post)

    if post.author != request.user:
        actor_name = request.user.get_full_name() or request.user.username
        Notification.objects.create(
            user=post.author,
            actor=request.user,
            related_post=post,
            notification_type='reply',
            title=f'{actor_name} replied to your post',
            message=content[:100] + ('...' if len(content) > 100 else ''),
        )

    if parent_reply and parent_reply.author != request.user and parent_reply.author != post.author:
        actor_name = request.user.get_full_name() or request.user.username
        Notification.objects.create(
            user=parent_reply.author,
            actor=request.user,
            related_post=post,
            notification_type='reply',
            title=f'{actor_name} replied to your comment',
            message=content[:100] + ('...' if len(content) > 100 else ''),
        )

    profile = request.user.barangay_profile

    return JsonResponse({
        'success': True,
        'reply': {
            'id': reply.id,
            'content': reply.content,
            'author': reply.author.get_full_name() or reply.author.username,
            'author_username': reply.author.username,
            'author_initial': reply.author.username[0].upper(),
            'avatar_color': profile.avatar_color,
            'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
            'created_at': reply.created_at.strftime('%b %d, %Y %I:%M %p'),
            'like_count': 0,
            'is_owner': True,
            'parent_reply_id': parent_reply_id
        }
    })


@login_required
def edit_community_post(request, post_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    post = get_object_or_404(CommunityPost, id=post_id, author=request.user)
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'success': False})
    post.content = content
    post.save()
    return JsonResponse({'success': True})


@login_required
def delete_community_post(request, post_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    post = get_object_or_404(CommunityPost, id=post_id, author=request.user)
    post.delete()
    return JsonResponse({'success': True})


@login_required
def edit_community_reply(request, reply_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    
    reply = get_object_or_404(CommunityReply, id=reply_id, author=request.user)
    content = request.POST.get('content', '').strip()
    
    if not content:
        return JsonResponse({'success': False})
    
    reply.content = content
    reply.save()
    
    return JsonResponse({'success': True})


@login_required
def delete_community_reply(request, reply_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    
    reply = get_object_or_404(CommunityReply, id=reply_id, author=request.user)
    reply.delete()
    
    return JsonResponse({'success': True})


@login_required
def toggle_like(request, post_id):
    post = get_object_or_404(CommunityPost, id=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
        if post.author != request.user:
            actor_name = request.user.get_full_name() or request.user.username
            Notification.objects.create(
                user=post.author,
                actor=request.user,
                related_post=post,
                notification_type='like',
                title=f'{actor_name} liked your post',
                message=post.content[:100] + ('...' if len(post.content) > 100 else ''),
            )
    return JsonResponse({'liked': liked, 'count': post.like_count})


@login_required
def mention_search(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 1:
        return JsonResponse({'users': []})

    users = User.objects.filter(
        Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
    ).exclude(id=request.user.id).select_related('barangay_profile')[:8]

    result = []
    for u in users:
        try:
            avatar_color = u.barangay_profile.avatar_color
            pic = u.barangay_profile.profile_picture.url if u.barangay_profile.profile_picture else None
        except Exception:
            avatar_color = '#22c55e'
            pic = None
        result.append({
            'username': u.username,
            'display_name': u.get_full_name() or u.username,
            'avatar_color': avatar_color,
            'profile_picture': pic,
        })

    return JsonResponse({'users': result})


# ==================== PROFILE VIEWS ====================

@login_required
def profile_view(request):
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    
    reports = WasteReport.objects.filter(reporter=request.user, is_draft=False).order_by('-reported_at')
    total_reports = reports.count()
    collected = reports.filter(status='collected').count()
    
    recent_posts = CommunityPost.objects.filter(author=request.user)[:5]
    recent_replies = CommunityReply.objects.filter(author=request.user)[:5]
    by_category = reports.values('category').annotate(count=Count('id'))
    leaderboard = BarangayProfile.objects.select_related('user').order_by('-points')[:10]
    
    context = {
        'display_user': request.user,
        'profile': profile,
        'is_own_profile': True,
        'total_reports': total_reports,
        'collected': collected,
        'reports': reports,
        'by_category': by_category,
        'leaderboard': leaderboard,
        'recent_posts': recent_posts,
        'recent_replies': recent_replies,
    }
    return render(request, 'waste_management/profile.html', context)


@login_required
def user_profile(request, username):
    if request.user.username == username:
        return redirect('profile')
    
    profile_user = get_object_or_404(User, username=username)
    profile, _ = BarangayProfile.objects.get_or_create(user=profile_user)
    
    reports = WasteReport.objects.filter(reporter=profile_user, is_draft=False).order_by('-reported_at')
    total_reports = reports.count()
    collected = reports.filter(status='collected').count()
    
    recent_posts = CommunityPost.objects.filter(author=profile_user)[:5]
    recent_replies = CommunityReply.objects.filter(author=profile_user)[:5]
    by_category = reports.values('category').annotate(count=Count('id'))
    leaderboard = BarangayProfile.objects.select_related('user').order_by('-points')[:10]
    
    context = {
        'display_user': profile_user,
        'profile': profile,
        'is_own_profile': False,
        'total_reports': total_reports,
        'collected': collected,
        'reports': reports,
        'by_category': by_category,
        'leaderboard': leaderboard,
        'recent_posts': recent_posts,
        'recent_replies': recent_replies,
    }
    return render(request, 'waste_management/profile.html', context)


@login_required
def admin_profile_view(request):
    if not request.user.is_superuser:
        return redirect('profile')
    
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    
    reports = WasteReport.objects.filter(reporter=request.user, is_draft=False).order_by('-reported_at')
    total_reports = reports.count()
    collected = reports.filter(status='collected').count()
    
    total_users_global = User.objects.count()
    
    context = {
        'display_user': request.user,
        'profile': profile,
        'total_reports': total_reports,
        'collected': collected,
        'total_users_global': total_users_global,
    }
    return render(request, 'waste_management/admin_profile.html', context)


@login_required
def toggle_follow(request, username):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        target_user = get_object_or_404(User, username=username)
        
        if target_user == request.user:
            return JsonResponse({'success': False, 'error': 'You cannot follow yourself'})
        
        follow_record = UserFollow.objects.filter(follower=request.user, following=target_user)
        
        if follow_record.exists():
            follow_record.delete()
            is_following = False
        else:
            UserFollow.objects.create(follower=request.user, following=target_user)
            is_following = True
        
        followers_count = UserFollow.objects.filter(following=target_user).count()
        
        return JsonResponse({
            'success': True,
            'is_following': is_following,
            'followers_count': followers_count
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def user_reports(request, username):
    profile_user = get_object_or_404(User, username=username)
    reports = WasteReport.objects.filter(reporter=profile_user, is_draft=False).order_by('-reported_at')
    
    reports_data = []
    for report in reports:
        reports_data.append({
            'id': report.id,
            'title': report.title,
            'category': report.get_category_display(),
            'status': report.status,
            'location': report.location,
            'date': report.reported_at.strftime('%b %d, %Y'),
            'points': report.points_awarded,
            'image': report.image.url if report.image else None,
        })
    
    return JsonResponse({'success': True, 'reports': reports_data})


@login_required
def my_following(request):
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    following = UserFollow.objects.filter(follower=request.user).select_related('following')
    return render(request, 'waste_management/following.html', {'following': following, 'profile': profile})


@login_required
def my_followers(request):
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    followers = UserFollow.objects.filter(following=request.user).select_related('follower')
    return render(request, 'waste_management/followers.html', {'followers': followers, 'profile': profile})


# ==================== SCHEDULES VIEW ====================

@login_required
def schedules(request):
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    all_schedules = CollectionSchedule.objects.filter(is_active=True)
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    schedule_by_day = {day: all_schedules.filter(day_of_week=day) for day in days}
    today = timezone.now().strftime('%A').lower()
    return render(request, 'waste_management/schedules.html', {
        'profile': profile,
        'schedule_by_day': schedule_by_day,
        'today': today,
        'days': days
    })


# ==================== NOTIFICATION VIEWS ====================

@login_required
def notifications_list(request):
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    notifications = Notification.objects.filter(user=request.user).select_related(
        'announcement', 'related_report', 'related_post', 'actor'
    )
    
    filter_type = request.GET.get('filter', 'all')
    
    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_type != 'all':
        notifications = notifications.filter(notification_type=filter_type)
    
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    for notif in page_obj:
        if notif.announcement:
            notif.announcement.content = mark_safe(notif.announcement.content)

    context = {
        'profile': profile,
        'notifications': page_obj,
        'filter': filter_type,
        'has_other_pages': page_obj.has_other_pages(),
    }
    return render(request, 'waste_management/notifications_list.html', context)


@login_required
def mark_notification_read(request, notification_id):
    notif = get_object_or_404(Notification, pk=notification_id, user=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
 
    if notif.url:
        return redirect(notif.url)
 
    next_url = request.GET.get('next', '')
    if next_url and next_url.startswith('/'):
        return redirect(next_url)
 
    return redirect('notifications_list')


@login_required
def mark_all_notifications_read(request):
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required
def unread_notifications_count_api(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    last_notification = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at').first()
    
    return JsonResponse({
        'count': count,
        'last_notification': last_notification.message if last_notification else None
    })


# ==================== ADMIN VIEWS ====================

@login_required
def admin_reports(request):
    if not request.user.is_superuser:
        return redirect('dashboard')
    
    reports = WasteReport.objects.filter(is_archived=False, is_draft=False).select_related('reporter').order_by('-reported_at')
    
    status = request.GET.get('status')
    category = request.GET.get('category')
    search = request.GET.get('search')
    report_id = request.GET.get('id')  # Add this line
    show_archived = request.GET.get('archive') == 'true'
    show_flagged = request.GET.get('flagged') == 'true'
    
    # If specific report ID is provided, filter by it
    if report_id:
        reports = reports.filter(id=report_id)
    
    if show_archived:
        reports = WasteReport.objects.filter(is_archived=True, is_draft=False).select_related('reporter').order_by('-archived_at', '-reported_at')
    else:
        reports = WasteReport.objects.filter(is_archived=False, is_draft=False).select_related('reporter').order_by('-reported_at')
    
    if status:
        reports = reports.filter(status=status)
    if category:
        reports = reports.filter(category=category)
    if search:
        reports = reports.filter(
            Q(title__icontains=search) |
            Q(reporter__username__icontains=search) |
            Q(location__icontains=search)
        )
    if show_flagged:
        reports = WasteReport.objects.filter(is_archived=False, is_draft=False).filter(
        flags__isnull=False
    ).distinct().select_related('reporter').order_by('-reported_at')
    
    paginator = Paginator(reports, 20)
    page = request.GET.get('page', 1)
    reports_page = paginator.get_page(page)

    all_reports_for_map = WasteReport.objects.filter(
        latitude__isnull=False, longitude__isnull=False,
        is_archived=False, is_draft=False
    ).select_related('reporter').order_by('-reported_at')[:200]
    reports_map_json = json.dumps([
        {
            'lat': float(r.latitude),
            'lng': float(r.longitude),
            'title': r.title,
            'category': r.category,
            'status': r.status,
            'reporter': r.reporter.username,
            'date': r.reported_at.strftime('%b %d, %Y'),
        }
        for r in all_reports_for_map
    ])

    return render(request, 'waste_management/admin_reports.html', {
        'reports': reports_page,
        'reports_map_json': reports_map_json,
        'show_archived': show_archived,
    })


@login_required
def admin_announcements(request):
    if not request.user.is_superuser:
        return redirect('dashboard')
    
    announcements = Announcement.objects.all().order_by('-created_at')
    for ann in announcements:
        ann.content = mark_safe(ann.content)
    emojis = ['📢', '🔔', '⚠️', '♻️', '🗑️', '🌿', '🚨', '📅', '🚛', '💡', '🏘️', '🧹']
    return render(request, 'waste_management/admin_announcements.html', {'announcements': announcements, 'emojis': emojis})


@login_required
def create_announcement(request):
    if not request.user.is_superuser or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    title = request.POST.get('title')
    content = request.POST.get('content')
    priority = request.POST.get('priority', 'medium')
    target_purok = request.POST.get('target_purok', '')
    emoji = request.POST.get('emoji', '')
    send_notification = request.POST.get('send_notification') == 'true'
    
    if not title or not content:
        return JsonResponse({'success': False, 'error': 'Title and content are required'})
    
    try:
        announcement = Announcement.objects.create(
            title=title,
            content=content,
            priority=priority,
            target_barangay=target_purok,
            emoji=emoji,
            send_notification=send_notification,
            created_by=request.user
        )

        if send_notification:
            profiles = BarangayProfile.objects.select_related('user').exclude(user=request.user)
            if target_purok:
                profiles = profiles.filter(purok__iexact=target_purok)
            notif_title = f'{emoji} {title}' if emoji else title
            notif_message = content[:150] + ('...' if len(content) > 150 else '')
            Notification.objects.bulk_create([
                Notification(
                    user=profile.user,
                    title=notif_title,
                    message=notif_message,
                    notification_type='announcement',
                    announcement=announcement,
                )
                for profile in profiles
            ])

        return JsonResponse({'success': True, 'id': announcement.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def edit_announcement(request, announcement_id):
    if not request.user.is_superuser or request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    announcement = get_object_or_404(Announcement, id=announcement_id)
    
    title = request.POST.get('title')
    content = request.POST.get('content')
    priority = request.POST.get('priority')
    
    if not title or not content:
        return JsonResponse({'success': False, 'error': 'Title and content are required'})
    
    announcement.title = title
    announcement.content = content
    announcement.priority = priority
    announcement.save()
    
    return JsonResponse({'success': True})


@login_required
def delete_announcement(request, announcement_id):
    if not request.user.is_superuser or request.method != 'POST':
        return JsonResponse({'success': False})
    
    announcement = get_object_or_404(Announcement, id=announcement_id)
    announcement.delete()
    return JsonResponse({'success': True})


@login_required
def bulk_update_reports(request):
    if not request.user.is_superuser or request.method != 'POST':
        return JsonResponse({'success': False})
    
    status = request.POST.get('status')
    report_ids = json.loads(request.POST.get('report_ids', '[]'))
    
    WasteReport.objects.filter(id__in=report_ids).update(status=status)
    
    if status == 'collected':
        WasteReport.objects.filter(id__in=report_ids).update(collected_at=timezone.now())
    
    return JsonResponse({'success': True, 'count': len(report_ids)})


@login_required
def get_report_details(request, report_id):
    report = get_object_or_404(WasteReport, id=report_id)
    data = {
        'id': report.id,
        'title': report.title,
        'category': report.get_category_display(),
        'status': report.status,
        'reporter': report.reporter.get_full_name() or report.reporter.username,
        'date': report.reported_at.strftime('%b %d, %Y %I:%M %p'),
        'location': report.location,
        'purok': report.purok,
        'description': report.description,
        'image': report.image.url if report.image else None,
        'latitude': str(report.latitude) if report.latitude else None,
        'longitude': str(report.longitude) if report.longitude else None,
    }
    return JsonResponse(data)

@login_required
def flag_report(request):
    """Admin endpoint to flag a report"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    report_id = request.POST.get('report_id')
    flag_type = request.POST.get('flag_type')
    note = request.POST.get('note', '').strip()
    
    if not report_id or not flag_type:
        return JsonResponse({'success': False, 'error': 'Missing report ID or flag type'})
    
    try:
        report = WasteReport.objects.get(id=report_id)
    except WasteReport.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Report not found'})
    
    # Import the ReportFlag model at the top of your views.py
    from .models import ReportFlag
    
    flag_type_display = dict(ReportFlag.FLAG_TYPES).get(flag_type, flag_type)
    
    try:
        flag = ReportFlag.objects.create(
            report=report,
            flagged_by=request.user,
            flag_type=flag_type,
            note=note
        )
        
        # Create notification for the user
        notification_title = 'Your report has been flagged'
        
        if flag_type == 'abusive':
            notification_message = f'Your report "{report.title}" has been flagged as {flag_type_display} and is under review.'
        else:
            notification_message = f'Your report "{report.title}" was flagged as {flag_type_display} by the admin.'
        
        if note:
            notification_message += f'\n\nAdmin note: {note[:200]}'
        
        Notification.objects.create(
            user=report.reporter,
            title=notification_title,
            message=notification_message,
            notification_type='report',
            related_report=report,
            url=f'/history/#report-{report.id}'
        )
        
        return JsonResponse({'success': True, 'flag_id': flag.id, 'flag_type': flag_type})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def unflag_report(request):
    """Admin endpoint to remove a flag from a report"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    report_id = request.POST.get('report_id')
    
    if not report_id:
        return JsonResponse({'success': False, 'error': 'Missing report ID'})
    
    try:
        report = WasteReport.objects.get(id=report_id)
    except WasteReport.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Report not found'})
    
    # Delete all flags for this report
    from .models import ReportFlag
    deleted_count = ReportFlag.objects.filter(report=report).delete()[0]
    
    # Create notification for the user that flag was removed
    Notification.objects.create(
        user=report.reporter,
        title='Flag Removed from Your Report',
        message=f'The flag on your report "{report.title}" has been removed by admin.',
        notification_type='report',
        related_report=report,
        url=f'/history/#report-{report.id}'
    )
    
    return JsonResponse({'success': True, 'deleted_count': deleted_count})
# ==================== API VIEWS ====================

@login_required
def verify_image(request):
    """Image verification with photo recency check (7 days) - Flags old photos instead of rejecting"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    image = request.FILES.get('image')
    if not image:
        return JsonResponse({'error': 'No image provided'}, status=400)
    
    result = {
        'exif_passed': False,
        'exif_requires_review': False,
        'exif_photo_age_days': None,
        'exif_warning': None,
        'ai_passed': True,
        'hash_passed': False,
        'exif_error': None,
        'ai_error': None,
        'hash_error': None,
        'ai_confidence': None,
        'exif_message': None,
        'hive_confidence': None
    }
    
    # 1. Basic image validation
    try:
        image.seek(0)
        img = Image.open(image)
        width, height = img.size
        
        if width < 300 or height < 300:
            result['ai_passed'] = False
            result['ai_error'] = '❌ Image is too small or blurry. Please upload a clearer photo (minimum 300x300 pixels).'
            return JsonResponse(result)
            
        if image.size > 5 * 1024 * 1024:
            result['ai_passed'] = False
            result['ai_error'] = '❌ File size too large (max 5MB). Please compress your image.'
            return JsonResponse(result)
            
    except Exception as e:
        result['ai_passed'] = False
        result['ai_error'] = f'❌ Could not read image: {str(e)}'
        return JsonResponse(result)
    
    # 2. EXIF Metadata Check with PHOTO RECENCY (7 DAYS) - FLAG OLD PHOTOS, DON'T REJECT
    try:
        image.seek(0)
        tags = exifread.process_file(image, details=False)
        
        has_exif = len(tags) > 0
        has_camera = 'Image Make' in tags or 'Image Model' in tags
        has_datetime = 'Image DateTime' in tags or 'EXIF DateTimeOriginal' in tags
        
        # CHECK PHOTO RECENCY (within 7 days)
        photo_age_days = None
        if has_datetime:
            try:
                dt_tag = tags.get('EXIF DateTimeOriginal') or tags.get('Image DateTime')
                dt_str = str(dt_tag)
                photo_dt = dt.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                photo_age_days = (dt.now() - photo_dt).days
                # Store photo age for frontend
                result['exif_photo_age_days'] = photo_age_days
                
                # MODIFIED: Don't reject old photos, just flag them
                if photo_age_days > 7:
                    # FLAG but don't reject - let frontend decide
                    result['exif_passed'] = True  # Still pass for further validation
                    result['exif_requires_review'] = True
                    result['exif_warning'] = f'Photo is {photo_age_days} days old (older than 7 days)'
                    result['exif_message'] = f'⚠️ Photo is {photo_age_days} days old (will be flagged for review)'
                    # Continue to other checks - don't return yet
            except Exception as e:
                print(f"Date parsing error: {e}")
        
        is_screenshot = False
        screenshot_reason = None
        software = tags.get('Image Software', None)
        if software:
            software_str = str(software).lower()
            if 'screenshot' in software_str:
                is_screenshot = True
                screenshot_reason = 'Screenshot software detected'
            elif 'snapchat' in software_str:
                is_screenshot = True
                screenshot_reason = 'Snapchat image detected'
            elif 'instagram' in software_str:
                is_screenshot = True
                screenshot_reason = 'Instagram image detected'
            elif 'facebook' in software_str:
                is_screenshot = True
                screenshot_reason = 'Facebook image detected'
        
        width, height = img.size
        phone_aspect_ratios = [(9, 16), (9, 19.5), (9, 20), (3, 4), (2, 3)]
        aspect = width / height
        is_phone_aspect = any(abs(aspect - (w/h)) < 0.1 for w, h in phone_aspect_ratios)
        
        # Only set exif_passed if not already set by old photo logic
        if 'exif_passed' not in result or not result['exif_passed']:
            if has_camera and not is_screenshot:
                result['exif_passed'] = True
                if photo_age_days is not None:
                    result['exif_message'] = f'✅ Camera photo verified (taken {photo_age_days} days ago)'
                    result['exif_photo_age_days'] = photo_age_days
                else:
                    result['exif_message'] = '✅ Camera photo verified'
            elif is_screenshot:
                result['exif_passed'] = False
                result['exif_error'] = f'Screenshot detected: {screenshot_reason}'
                result['ai_passed'] = False
                result['ai_error'] = f'❌ {result["exif_error"]}. Please upload a photo taken with your camera.'
                return JsonResponse(result)
            elif is_phone_aspect and not has_camera:
                result['exif_passed'] = False
                result['exif_error'] = 'Phone aspect ratio but no camera metadata'
                result['ai_passed'] = False
                result['ai_error'] = '❌ No camera data found. This appears to be a screenshot or downloaded image.'
                return JsonResponse(result)
            elif has_exif and not has_camera:
                result['exif_passed'] = False
                result['exif_error'] = 'EXIF data found but no camera information'
                result['ai_passed'] = False
                result['ai_error'] = '❌ Image has been edited or saved from another source.'
                return JsonResponse(result)
            else:
                result['exif_passed'] = False
                result['exif_error'] = 'No EXIF metadata found'
                result['ai_passed'] = False
                result['ai_error'] = '❌ No camera metadata found. Please upload a real photo taken with your camera.'
                return JsonResponse(result)
            
    except Exception as e:
        result['exif_passed'] = False
        result['exif_error'] = f'Could not read EXIF: {str(e)}'
        result['ai_passed'] = False
        result['ai_error'] = '❌ Could not verify image source.'
        return JsonResponse(result)
    
    # 3. Hive AI Detection
    try:
        image.seek(0)
        is_ai, hive_confidence = check_ai_with_hive(image)
        
        if hive_confidence > 0:
            result['hive_confidence'] = f"{int(hive_confidence * 100)}%"
        
        if is_ai:
            result['ai_passed'] = False
            result['ai_error'] = f'❌ AI-generated image detected ({result["hive_confidence"]} confidence).'
            return JsonResponse(result)
            
    except Exception as e:
        print(f"Hive AI error: {e}")
    
    # 4. WASTE DETECTION
    try:
        image.seek(0)
        img = Image.open(image)
        img_hsv = img.convert('HSV')
        img_array = np.array(img_hsv)
        
        h = img_array[:, :, 0].flatten()
        s = img_array[:, :, 1].flatten()
        v = img_array[:, :, 2].flatten()
        
        waste_colors = (
            ((h > 15) & (h < 35)) |
            ((h > 40) & (h < 85)) |
            ((h > 100) & (h < 135)) |
            ((s < 40) & (v > 40)) |
            ((v < 40) & (s < 60))
        )
        
        waste_ratio = np.sum(waste_colors) / len(h) if len(h) > 0 else 0
        
        img_gray = img.convert('L')
        img_array_gray = np.array(img_gray)
        texture_variance = np.var(img_array_gray)
        has_texture = texture_variance > 500
        
        is_waste_likely = waste_ratio > 0.08 or (waste_ratio > 0.05 and has_texture)
        
        if not is_waste_likely:
            result['ai_passed'] = False
            if waste_ratio < 0.03:
                result['ai_error'] = '❌ No waste materials detected. Please upload a photo of waste.'
            else:
                result['ai_error'] = '❌ Unable to verify waste materials.'
            return JsonResponse(result)
            
        if waste_ratio > 0.15:
            result['ai_confidence'] = f'✅ Waste detected - High confidence ({int(waste_ratio * 100)}%)'
        elif waste_ratio > 0.10:
            result['ai_confidence'] = f'✅ Waste detected - Good confidence ({int(waste_ratio * 100)}%)'
        else:
            result['ai_confidence'] = f'✅ Waste detected ({int(waste_ratio * 100)}%)'
            
    except Exception as e:
        print(f"Waste detection error: {e}")
        if result['exif_passed']:
            result['ai_confidence'] = '⚠️ Waste detection unavailable - proceeding based on camera verification'
        else:
            result['ai_passed'] = False
            result['ai_error'] = '❌ Could not verify image content.'
            return JsonResponse(result)
    
    # 5. Duplicate Check
    try:
        image.seek(0)
        img = Image.open(image)
        img = img.resize((8, 8), Image.Resampling.LANCZOS).convert('L')
        pixels = list(img.getdata())
        avg = sum(pixels) / len(pixels)
        hash_bits = ''.join('1' if p > avg else '0' for p in pixels)
        image_hash = hex(int(hash_bits, 2))[2:].zfill(16)
        
        week_ago = timezone.now() - timedelta(days=7)
        duplicate = WasteReport.objects.filter(
            image_hash=image_hash,
            reported_at__gte=week_ago
        ).exists()
        
        if duplicate:
            result['ai_passed'] = False
            result['ai_error'] = '❌ Duplicate image detected. This image has already been submitted.'
            return JsonResponse(result)
        else:
            result['hash_passed'] = True
            
    except Exception as e:
        result['hash_error'] = str(e)
    
    if result['ai_passed']:
        result['ai_confidence'] = result.get('ai_confidence', '✅ Verified - Real waste photo')
    
    return JsonResponse(result)


@login_required
def toggle_reply_like(request, reply_id):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    
    reply = get_object_or_404(CommunityReply, id=reply_id)
    
    if request.user in reply.likes.all():
        reply.likes.remove(request.user)
        liked = False
    else:
        reply.likes.add(request.user)
        liked = True
        if reply.author != request.user:
            actor_name = request.user.get_full_name() or request.user.username
            Notification.objects.create(
                user=reply.author,
                actor=request.user,
                related_post=reply.post,
                notification_type='like',
                title=f'{actor_name} liked your reply',
                message=reply.content[:100] + ('...' if len(reply.content) > 100 else ''),
            )
    
    return JsonResponse({
        'success': True,
        'liked': liked,
        'count': reply.likes.count()
    })


@login_required
@require_POST
def share_post(request, post_id):
    post = get_object_or_404(CommunityPost, id=post_id)
    if post.author != request.user:
        actor_name = request.user.get_full_name() or request.user.username
        Notification.objects.create(
            user=post.author,
            actor=request.user,
            related_post=post,
            notification_type='share',
            title=f'{actor_name} shared your post',
            message=post.content[:100] + ('...' if len(post.content) > 100 else ''),
        )
    return JsonResponse({'success': True})


@login_required
def report_content(request):
    if request.method != 'POST':
        return JsonResponse({'success': False})
    
    content_id = request.POST.get('content_id')
    content_type = request.POST.get('content_type')
    reason = request.POST.get('reason')
    
    print(f"Report received - Type: {content_type}, ID: {content_id}, Reason: {reason}, Reporter: {request.user.username}")
    
    return JsonResponse({'success': True, 'message': 'Report submitted. Thank you!'})


@login_required
def update_profile(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        user = request.user
        profile = user.barangay_profile
        
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        
        profile.barangay_name = request.POST.get('barangay_name', '')
        profile.purok = request.POST.get('purok', '')
        profile.contact_number = request.POST.get('contact_number', '')
        profile.address = request.POST.get('address', '')
        profile.avatar_color = request.POST.get('avatar_color', '#22c55e')
        
        if request.FILES.get('profile_picture'):
            profile.profile_picture = request.FILES['profile_picture']
        if request.POST.get('remove_avatar') == 'true':
            if profile.profile_picture:
                profile.profile_picture.delete(save=False)
            profile.profile_picture = None
        
        profile.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def view_report(request, report_id):
    report = get_object_or_404(WasteReport, id=report_id)
    
    if report.reporter != request.user and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to view this report.')
        return redirect('history')
    
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    
    context = {
        'profile': profile,
        'report': report,
    }
    return render(request, 'waste_management/view_report.html', context)


@login_required
def settings_view(request):
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    
    reports = WasteReport.objects.filter(reporter=request.user, is_draft=False)
    total_reports = reports.count()
    recent_posts = CommunityPost.objects.filter(author=request.user)
    
    active_tab = request.POST.get('tab') or request.GET.get('tab', 'profile')
    
    if not hasattr(profile, 'notification_settings') or not profile.notification_settings:
        profile.notification_settings = {
            'email': True,
            'report_updates': True,
            'community_activity': True,
            'announcements': True,
        }
        profile.save()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_profile':
            try:
                user = request.user
                username = request.POST.get('username', '')
                
                if username and username != user.username:
                    if User.objects.filter(username=username).exists():
                        messages.error(request, 'Username already taken.')
                        return redirect(f'/settings/?tab={active_tab}')
                    user.username = username
                
                user.first_name = request.POST.get('first_name', '')
                user.last_name = request.POST.get('last_name', '')
                user.email = request.POST.get('email', '')
                user.save()
                
                profile.barangay_name = request.POST.get('barangay_name', '')
                profile.purok = request.POST.get('purok', '')
                profile.contact_number = request.POST.get('contact_number', '')
                profile.address = request.POST.get('address', '')
                profile.avatar_color = request.POST.get('avatar_color', '#22c55e')
                
                if request.FILES.get('profile_picture'):
                    profile.profile_picture = request.FILES['profile_picture']
                if request.POST.get('remove_avatar') == 'true':
                    if profile.profile_picture:
                        profile.profile_picture.delete(save=False)
                    profile.profile_picture = None
                
                profile.save()
                messages.success(request, 'Profile updated successfully!')
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        
        elif action == 'update_notifications':
            try:
                email_notif = request.POST.get('email_notif') == 'on'
                report_notif = request.POST.get('report_notif') == 'on'
                community_notif = request.POST.get('community_notif') == 'on'
                announce_notif = request.POST.get('announce_notif') == 'on'
                
                notification_settings = {
                    'email': email_notif,
                    'report_updates': report_notif,
                    'community_activity': community_notif,
                    'announcements': announce_notif,
                }
                profile.notification_settings = notification_settings
                profile.save()
                messages.success(request, 'Notification settings updated!')
            except Exception as e:
                messages.error(request, f'Error updating notifications: {str(e)}')
        
        elif action == 'update_privacy':
            try:
                profile.is_profile_public = request.POST.get('is_profile_public') == 'on'
                profile.show_email = request.POST.get('show_email') == 'on'
                profile.show_location = request.POST.get('show_location') == 'on'
                profile.allow_messages = request.POST.get('allow_messages') == 'on'
                profile.save()
                messages.success(request, 'Privacy settings updated!')
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        
        elif action == 'change_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
            elif new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
            elif len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
            else:
                request.user.set_password(new_password)
                request.user.save()
                messages.success(request, 'Password changed successfully! Please login again.')
                return redirect('login')
        
        elif action == 'export_data':
            messages.success(request, 'Data export requested.')
        
        elif action == 'delete_account':
            confirmation = request.POST.get('confirmation')
            if confirmation == 'DELETE':
                user = request.user
                logout(request)
                user.delete()
                messages.success(request, 'Account deleted successfully.')
                return redirect('landing')
            else:
                messages.error(request, 'Please type DELETE to confirm.')
        
        return redirect(f'/settings/?tab={active_tab}')
    
    notification_settings = profile.notification_settings
    
    context = {
        'profile': profile,
        'user': request.user,
        'total_reports': total_reports,
        'recent_posts': recent_posts,
        'notification_settings': notification_settings,
        'active_tab': active_tab,
    }
    return render(request, 'waste_management/settings.html', context)


@login_required
def admin_settings_view(request):
    if not request.user.is_superuser:
        return redirect('dashboard')
    
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    
    total_users = User.objects.count()
    total_reports_all = WasteReport.objects.filter(is_draft=False).count()
    community_posts_count = CommunityPost.objects.count()
    total_points = BarangayProfile.objects.aggregate(t=Sum('points'))['t'] or 0
    recent_users_list = User.objects.order_by('-date_joined')[:10]
    
    active_tab = request.GET.get('tab', 'profile')
    
    if 'system_name' not in request.session:
        request.session['system_name'] = 'ReporTrash'
    if 'maintenance_mode' not in request.session:
        request.session['maintenance_mode'] = False
    if 'allow_registration' not in request.session:
        request.session['allow_registration'] = True
    if 'email_verification' not in request.session:
        request.session['email_verification'] = False
    
    if request.method == 'POST':
        action = request.POST.get('action')
        tab = request.POST.get('tab', 'profile')
        
        if action == 'update_profile':
            try:
                user = request.user
                username = request.POST.get('username', '')
                
                if username and username != user.username:
                    if User.objects.filter(username=username).exists():
                        messages.error(request, 'Username already taken.')
                        return redirect(f'/admin-settings/?tab={tab}')
                    user.username = username
                
                user.first_name = request.POST.get('first_name', '')
                user.last_name = request.POST.get('last_name', '')
                user.email = request.POST.get('email', '')
                user.save()
                
                profile.barangay_name = request.POST.get('barangay_name', '')
                profile.contact_number = request.POST.get('contact_number', '')
                profile.address = request.POST.get('address', '')
                profile.avatar_color = request.POST.get('avatar_color', '#22c55e')
                
                if request.FILES.get('profile_picture'):
                    profile.profile_picture = request.FILES['profile_picture']
                if request.POST.get('remove_avatar') == 'true':
                    if profile.profile_picture:
                        profile.profile_picture.delete(save=False)
                    profile.profile_picture = None
                
                profile.save()
                messages.success(request, 'Profile updated successfully!')
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        
        elif action == 'update_system':
            try:
                request.session['system_name'] = request.POST.get('system_name', 'ReporTrash')
                request.session['maintenance_mode'] = request.POST.get('maintenance_mode') == 'on'
                request.session['allow_registration'] = request.POST.get('allow_registration') == 'on'
                request.session['email_verification'] = request.POST.get('email_verification') == 'on'
                messages.success(request, 'System settings updated successfully!')
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        
        elif action == 'change_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not request.user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
            elif new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
            elif len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
            else:
                request.user.set_password(new_password)
                request.user.save()
                messages.success(request, 'Password changed successfully! Please login again.')
                return redirect('login')
        
        return redirect(f'/admin-settings/?tab={tab}')
    
    context = {
        'profile': profile,
        'user': request.user,
        'total_users': total_users,
        'total_reports_all': total_reports_all,
        'community_posts_count': community_posts_count,
        'total_points': total_points,
        'recent_users_list': recent_users_list,
        'active_tab': active_tab,
        'system_name': request.session.get('system_name', 'ReporTrash'),
        'maintenance_mode': request.session.get('maintenance_mode', False),
        'allow_registration': request.session.get('allow_registration', True),
        'email_verification': request.session.get('email_verification', False),
    }
    return render(request, 'waste_management/admin_settings.html', context)


@login_required
def announcements(request):
    profile, _ = BarangayProfile.objects.get_or_create(user=request.user)
    
    priority_filter = request.GET.get('priority', 'all')
    
    announcements_list = Announcement.objects.filter(is_active=True)
    
    if profile.purok:
        announcements_list = announcements_list.filter(
            Q(target_barangay=profile.purok) | 
            Q(target_barangay='') | 
            Q(target_barangay__isnull=True)
        )
    else:
        announcements_list = announcements_list.filter(
            Q(target_barangay='') | Q(target_barangay__isnull=True)
        )
    
    if priority_filter != 'all':
        announcements_list = announcements_list.filter(priority=priority_filter)
    
    priority_order = {'urgent': 0, 'high': 1, 'medium': 2, 'low': 3}
    announcements_list = sorted(
        announcements_list, 
        key=lambda x: (priority_order.get(x.priority, 4), -x.created_at.timestamp())
    )
    
    target_ann_id = request.GET.get('ann_id')
    page_number = request.GET.get('page')
    if target_ann_id and not page_number:
        try:
            target_ann_id_int = int(target_ann_id)
            for idx, ann in enumerate(announcements_list):
                if ann.id == target_ann_id_int:
                    page_number = (idx // 10) + 1
                    break
        except (ValueError, TypeError):
            pass

    paginator = Paginator(announcements_list, 10)
    announcements_page = paginator.get_page(page_number)

    for ann in announcements_page:
        ann.content = mark_safe(ann.content)

    context = {
        'profile': profile,
        'announcements': announcements_page,
        'priority_filter': priority_filter,
        'target_ann_id': target_ann_id,
    }

    return render(request, 'waste_management/announcements.html', context)


# ==================== TRASHBOT AI CHATBOT VIEW ====================

TRASHBOT_SYSTEM_PROMPT = """You are TrashBot, a friendly AI assistant for ReporTrash — a community waste management and reporting platform in the Philippines. Help residents with:
- Submitting waste reports (biodegradable, recyclable, residual, special, hazardous, electronic)
- Tracking report status (pending, in_progress, resolved, rejected)
- The points/rewards system (earning points for verified reports)
- Collection schedules in their barangay
- Community features (posts, likes, follows)
- Announcements from barangay admins
- Account settings and profile

IMPORTANT: If a user has asked more than 3 questions in a row, or seems frustrated/confused, or asks something too complex for you, suggest they speak to a human admin. Use phrases like:
- "I think this would be better handled by our support team. Would you like me to connect you with an admin? Just click the chat icon (headset) at the bottom right."
- "For detailed assistance with this, our admin team would be better suited. You can start a chat with them by clicking the support button."
- "This is beyond my capabilities. Let me help you reach a human admin instead — look for the chat button on the bottom right."

Detect the user's language (English, Tagalog, or Bisaya/Cebuano) and reply in the same language.
Be friendly and concise. Do not make up information unrelated to waste management or ReporTrash.
Key facts: App = ReporTrash. Points awarded when a report is verified/resolved by admin."""


@login_required
def chatbot_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    try:
        body = json.loads(request.body)
        user_message = body.get('message', '').strip()
        session_id = body.get('session_id')
        request_human = body.get('request_human', False)
        clear = body.get('clear', False)

        if not user_message and not clear:
            return JsonResponse({'error': 'Empty message'}, status=400)

        from .models import ChatMessage

        # STRONGER human detection - check for keywords
        human_keywords = ['human', 'talk to admin', 'speak to admin', 'real person', 
                         'live agent', 'customer support', 'help me', 'contact admin',
                         'i need a human', 'real human', 'actual person', 'admin please']
        
        wants_human = request_human or any(keyword in user_message.lower() for keyword in human_keywords)
        
        # Check if there's already a pending human chat
        pending_human_chat = ChatMessage.objects.filter(
            user=request.user,
            status__in=['pending_human', 'human_active']
        ).exists()

        mode = 'human' if pending_human_chat else 'ai'

        if session_id:
            session = ChatbotSession.objects.filter(
                pk=session_id, user=request.user, is_active=True
            ).first()
        else:
            session = None

        if not session:
            ChatbotSession.objects.filter(user=request.user, is_active=True).update(is_active=False)
            session = ChatbotSession.objects.create(user=request.user)

        if clear:
            session.messages.all().delete()
            ChatMessage.objects.filter(user=request.user).delete()
            return JsonResponse({'session_id': session.pk, 'cleared': True, 'mode': 'ai'})

        # Save user message
        ChatbotMessage.objects.create(session=session, role='user', content=user_message)
        
        ChatMessage.objects.create(
            user=request.user,
            message=user_message,
            sender='user',
            status='pending_human' if wants_human else ('human_active' if pending_human_chat else 'ai_only')
        )

        # Handle human support request - IMMEDIATE response
        if wants_human:
            if not pending_human_chat:
                # Notify admins
                from .models import Notification
                for admin in User.objects.filter(is_superuser=True):
                    Notification.objects.create(
                        user=admin,
                        title=f'🆘 Human Support Request from {request.user.username}',
                        message=f'User is requesting human assistance: "{user_message[:100]}"',
                        notification_type='chat',
                        url='/dashboard/admin-chats/'
                    )
                
                # Update status
                ChatMessage.objects.filter(user=request.user, status='ai_only').update(status='pending_human')
                
                return JsonResponse({
                    'success': True,
                    'reply': '🆘 **I\'ve notified our support team!**\n\nA real admin will join this chat shortly. Please wait a moment.\n\nIn the meantime, you can continue describing your issue.',
                    'session_id': session.pk,
                    'mode': 'pending_human',
                    'human_requested': True,
                    'sender': 'system'
                })
            else:
                return JsonResponse({
                    'success': True,
                    'reply': '👥 **Support team has been notified**\n\nAn admin is on their way to help you. Please wait for their response.\n\nYou can continue typing your message and they will see it when they join.',
                    'session_id': session.pk,
                    'mode': 'human',
                    'sender': 'system'
                })

        # If human chat is active
        if pending_human_chat:
            return JsonResponse({
                'success': True,
                'reply': '📝 **Message sent to support team**\n\nAn admin will respond shortly. Please check back in a moment.',
                'session_id': session.pk,
                'mode': 'human',
                'sender': 'system'
            })

        # Otherwise, use AI (normal flow)
        recent_msgs = session.messages.order_by('-created_at')[:20]
        history = [
            {'role': m.role, 'content': m.content}
            for m in reversed(list(recent_msgs))
        ]
        while history and history[0]['role'] != 'user':
            history.pop(0)

        GROQ_API_KEY = getattr(settings, 'GROQ_API_KEY', None)
        if not GROQ_API_KEY:
            return JsonResponse({'error': 'AI service not configured'}, status=500)

        # Modified system prompt
        HUMAN_HANDLER_PROMPT = """You are TrashBot AI assistant for ReporTrash.

IMPORTANT INSTRUCTIONS:
- If a user asks to talk to a human, type "talk to admin", or uses words like "human", "real person", "support", "help me", you MUST respond with: "I'll connect you with a human admin right away. Please type 'CONNECT HUMAN' to confirm."
- When user types "CONNECT HUMAN", you will trigger the human support request.
- DO NOT just tell them to click a button - use the response above.
- Be helpful with waste management questions but know when to escalate.

For waste-related questions: help with reporting, categories, points, schedules, community features."""
        
        groq_messages = [{'role': 'system', 'content': HUMAN_HANDLER_PROMPT}] + history

        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {GROQ_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'llama-3.1-8b-instant',
                'messages': groq_messages,
                'max_tokens': 1000,
            },
            timeout=30,
        )

        if response.status_code != 200:
            return JsonResponse({'error': f'AI API error'}, status=502)

        data = response.json()
        reply = data['choices'][0]['message']['content']
        
        # Check if AI is suggesting to connect to human
        if "CONNECT HUMAN" in reply.upper() or "connect you with a human" in reply.lower():
            wants_human = True
            if not pending_human_chat:
                from .models import Notification
                for admin in User.objects.filter(is_superuser=True):
                    Notification.objects.create(
                        user=admin,
                        title=f'Human Support Request from {request.user.username}',
                        message=f'AI escalated: "{user_message[:100]}"',
                        notification_type='chat',
                        url='/dashboard/admin-chats/'
                    )
                ChatMessage.objects.filter(user=request.user, status='ai_only').update(status='pending_human')
                reply = "🆘 **I'm connecting you with a human admin now!**\n\nPlease wait a moment - our support team will join this chat shortly."

        # Save AI response
        ChatbotMessage.objects.create(session=session, role='assistant', content=reply)
        ChatMessage.objects.create(
            user=request.user,
            message=reply,
            sender='ai',
            status='ai_only'
        )

        return JsonResponse({
            'reply': reply,
            'session_id': session.pk,
            'mode': 'ai',
            'sender': 'ai'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def chat_clear_api(request):
    """Clear chat history"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if session_id:
            session = ChatbotSession.objects.filter(pk=session_id, user=request.user).first()
            if session:
                session.messages.all().delete()
        
        # Clear human messages
        ChatMessage.objects.filter(user=request.user).delete()
        
        # Create new session
        ChatbotSession.objects.filter(user=request.user, is_active=True).update(is_active=False)
        new_session = ChatbotSession.objects.create(user=request.user)
        
        return JsonResponse({'success': True, 'session_id': new_session.pk})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
@login_required
def chat_history_api(request):
    """Get combined chat history (AI + Human)"""
    session_id = request.GET.get('session_id')
    
    if session_id:
        session = ChatbotSession.objects.filter(pk=session_id, user=request.user).first()
    else:
        session = ChatbotSession.objects.filter(user=request.user, is_active=True).first()
    
    if not session:
        return JsonResponse({'session_id': None, 'messages': [], 'mode': 'ai', 'unread_count': 0, 'has_pending_human': False})
    
    # Get AI messages (from ChatbotMessage)
    ai_messages = [
        {'role': m.role, 'content': m.content, 'created_at': m.created_at.strftime('%I:%M %p'), 'sender': m.role}
        for m in session.messages.all()
    ]
    
    # Get human chat messages (from ChatMessage model)
    from .models import ChatMessage
    human_messages = ChatMessage.objects.filter(
        user=request.user,
        sender__in=['admin', 'user', 'ai']
    ).order_by('created_at')
    
    unread_count = human_messages.filter(sender='admin', is_read=False).count()
    
    # Mark admin messages as read
    human_messages.filter(sender='admin', is_read=False).update(is_read=True, read_at=timezone.now())
    
    # Combine messages into a single list sorted by timestamp
    all_messages = []
    
    # Add AI messages (convert to same format)
    for msg in ai_messages:
        all_messages.append({
            'content': msg['content'],
            'sender': 'ai' if msg['role'] == 'assistant' else 'user',
            'created_at': msg['created_at']
        })
    
    # Add human messages
    for msg in human_messages:
        sender = msg.sender
        if sender == 'admin':
            sender = 'admin'
        elif sender == 'user':
            sender = 'user'
        else:
            sender = 'ai'
        
        all_messages.append({
            'content': msg.message,
            'sender': sender,
            'created_at': msg.created_at.strftime('%I:%M %p')
        })
    
    # Sort by time (simple approach - they're already in order if we merge properly)
    # For simplicity, we'll keep the order as is and rely on the fact that AI messages come first then human
    
    # Check mode
    has_pending = ChatMessage.objects.filter(user=request.user, status='pending_human').exists()
    mode = 'human' if has_pending else 'ai'
    
    return JsonResponse({
        'session_id': session.id,
        'messages': all_messages,
        'mode': mode,
        'unread_count': unread_count,
        'has_pending_human': has_pending
    })

# Add these functions to your views.py (after the existing functions, before request_human_api)

def switch_to_human_mode(request, message):
    """Switch user to human mode and notify admin"""
    print(f"SWITCHING TO HUMAN MODE for user: {request.user.username}")
    
    profile = request.user.barangay_profile
    profile.chat_mode = 'human'
    profile.chat_session_active = True
    profile.save()
    
    # Create pending human request
    ChatMessage.objects.create(
        user=request.user,
        message=message if message != "[User requested human support]" else "User requested to speak with an admin",
        sender='user',
        status='pending_human'
    )
    
    # Notify admins
    for admin in User.objects.filter(is_superuser=True):
        Notification.objects.create(
            user=admin,
            title=f'🆘 Human Support Request from {request.user.username}',
            message=f'User requested human assistance',
            notification_type='chat',
            url='/dashboard/admin-chats/'
        )
    
    return JsonResponse({
        'success': True,
        'reply': '🆘 **Switched to Human Support!**\n\nA real admin will join this chat shortly. Please wait a moment.\n\nYou can continue typing your message and they will see it.',
        'sender': 'system',
        'mode': 'human',
        'human_requested': True
    })


def switch_to_ai_mode(request, message):
    """Switch user back to AI mode"""
    print(f"SWITCHING TO AI MODE for user: {request.user.username}")
    from django.utils import timezone
    
    profile = request.user.barangay_profile
    profile.chat_mode = 'ai'
    profile.chat_session_active = False
    profile.save()
    
    # Close all pending human chats so admin stops seeing this user
    updated_count = ChatMessage.objects.filter(
        user=request.user, 
        status__in=['pending_human', 'human_active']
    ).update(status='closed')
    
    print(f"Closed {updated_count} human chat sessions for {request.user.username}")
    
    # Create new AI session
    ChatbotSession.objects.filter(user=request.user, is_active=True).update(is_active=False)
    session = ChatbotSession.objects.create(user=request.user)
    
    # Get AI response
    reply = "🤖 Switched to AI mode! How can I help you with waste reporting today?"
    GROQ_API_KEY = getattr(settings, 'GROQ_API_KEY', None)
    
    if GROQ_API_KEY and message and message not in ["switch to ai", "back to ai"]:
        try:
            response = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
                json={
                    'model': 'llama-3.1-8b-instant',
                    'messages': [
                        {'role': 'system', 'content': 'You are TrashBot AI assistant for ReporTrash.'},
                        {'role': 'user', 'content': message}
                    ],
                    'max_tokens': 500
                },
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                reply = data['choices'][0]['message']['content']
                ChatbotMessage.objects.create(session=session, role='assistant', content=reply)
        except Exception as e:
            print(f"AI error on mode switch: {e}")
    
    return JsonResponse({
        'success': True,
        'reply': reply,
        'session_id': session.pk,
        'sender': 'ai',
        'mode': 'ai'
    })


# Then update your request_human_api function:
@login_required
def request_human_api(request):
    """User explicitly requests human support"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        # Check if already in human mode
        profile = request.user.barangay_profile
        if profile.chat_mode == 'human':
            return JsonResponse({'success': True, 'message': 'Already in human support mode'})
        
        # Check if already has pending request
        existing = ChatMessage.objects.filter(
            user=request.user,
            status__in=['pending_human', 'human_active']
        ).exists()
        
        if existing:
            return JsonResponse({'success': True, 'message': 'Support request already pending'})
        
        return switch_to_human_mode(request, "User requested human support")
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def request_human_api(request):
    """User explicitly requests human support"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        return switch_to_human_mode(request, "[User requested human support]")
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def clear_chat_api(request):
    """Clear chat history"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if session_id:
            session = ChatbotSession.objects.filter(pk=session_id, user=request.user).first()
            if session:
                session.messages.all().delete()
        
        # Clear human messages but keep status
        ChatMessage.objects.filter(user=request.user, sender='user').delete()
        ChatMessage.objects.filter(user=request.user, sender='ai').delete()
        
        # Create new session
        ChatbotSession.objects.filter(user=request.user, is_active=True).update(is_active=False)
        new_session = ChatbotSession.objects.create(user=request.user)
        
        return JsonResponse({'success': True, 'session_id': new_session.pk})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def chatbot_history(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        session = ChatbotSession.objects.filter(user=request.user, is_active=True).first()
    else:
        session = ChatbotSession.objects.filter(pk=session_id, user=request.user).first()

    if not session:
        return JsonResponse({'session_id': None, 'messages': []})

    msgs = [
        {'role': m.role, 'content': m.content, 'created_at': m.created_at.isoformat()}
        for m in session.messages.all()
    ]
    return JsonResponse({'session_id': session.pk, 'messages': msgs})


# ==================== PENDING APPROVAL VIEWS ====================

@login_required
def pending_approval_view(request):
    try:
        profile = request.user.barangay_profile
    except Exception:
        profile = BarangayProfile.objects.get_or_create(user=request.user)[0]
 
    if profile.approval_status == 'approved':
        return redirect('dashboard')
 
    context = {
        'status': profile.approval_status,
        'rejection_reason': profile.rejection_reason,
        'user': request.user,
    }
    return render(request, 'waste_management/pending_approval.html', context)


@login_required
def admin_pending_users_view(request):
    if not request.user.is_superuser:
        return redirect('dashboard')
 
    pending_profiles = BarangayProfile.objects.filter(
        approval_status='pending'
    ).select_related('user').order_by('user__date_joined')
 
    pending_users = [p.user for p in pending_profiles]
 
    context = {
        'pending_users': pending_users,
        'pending_count': len(pending_users),
    }
    return render(request, 'waste_management/admin_pending_users.html', context)
 
 
@login_required
def approve_user_view(request, user_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
 
    try:
        target_user = User.objects.get(pk=user_id)
        profile = target_user.barangay_profile
    except (User.DoesNotExist, BarangayProfile.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
 
    profile.approval_status = 'approved'
    profile.rejection_reason = ''
    profile.save()
 
    Notification.objects.create(
        user=target_user,
        title='Account Approved',
        message=(
            'Your registration for Barangay Zone 1 has been verified by the admin. '
            'Welcome to ReporTrash! You can now log in and start reporting.'
        ),
        notification_type='system',
        url='/dashboard/',
    )
 
    return JsonResponse({'success': True})
 
 
@login_required
def reject_user_view(request, user_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
 
    try:
        data = json.loads(request.body)
        reason = data.get('reason', '').strip()
    except Exception:
        reason = ''
 
    try:
        target_user = User.objects.get(pk=user_id)
        profile = target_user.barangay_profile
    except (User.DoesNotExist, BarangayProfile.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)
 
    profile.approval_status = 'rejected'
    profile.rejection_reason = reason
    profile.save()
 
    reason_text = f' Reason: {reason}' if reason else ''
    Notification.objects.create(
        user=target_user,
        title='Registration Not Approved',
        message=(
            f'Your registration for Barangay Zone 1 could not be verified.{reason_text} '
            'Please visit the barangay hall for assistance.'
        ),
        notification_type='system',
        url='/pending-approval/',
    )
 
    return JsonResponse({'success': True})


@login_required
def add_admin_note(request):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    report_id = request.POST.get('report_id')
    admin_notes = request.POST.get('admin_notes', '').strip()
    
    try:
        report = WasteReport.objects.get(id=report_id)
        report.admin_notes = admin_notes
        report.admin_notes_updated_at = timezone.now()  # Update timestamp
        report.save()
        
        if admin_notes:
            note_preview = admin_notes[:100] + ('...' if len(admin_notes) > 100 else '')
            Notification.objects.create(
                user=report.reporter,
                title='Admin Note on Your Report',
                message=f'Admin added a note to your report "{report.title}": "{note_preview}"',
                notification_type='report',
                related_report=report,
                url=f'/history/#report-{report.id}'
            )
        else:
            Notification.objects.create(
                user=report.reporter,
                title='Admin Note Removed',
                message=f'Admin removed notes from your report "{report.title}".',
                notification_type='report',
                related_report=report,
                url=f'/history/#report-{report.id}'
            )
        
        return JsonResponse({'success': True})
    except WasteReport.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Report not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def admin_analytics(request):
    if not request.user.is_superuser:
        return redirect('dashboard')
    
    now = timezone.now()
    
    all_reports = WasteReport.objects.filter(is_draft=False)
    total_reports_all = all_reports.count()
    pending_total = all_reports.filter(status='pending').count()
    
    purok_qs = (
        all_reports
        .exclude(purok__isnull=True).exclude(purok='')
        .values('purok')
        .annotate(
            count=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            resolved=Count('id', filter=Q(status__in=['inprogress', 'resolved', 'rejected'])),
        )
        .order_by('-count')
    )
    
    total_puroks = purok_qs.count()
    max_count = purok_qs.first()['count'] if purok_qs.exists() else 1
    
    purok_stats = []
    for item in purok_qs:
        item['pct'] = round(item['count'] / max_count * 100, 1)
        purok_stats.append(item)
    
    top_purok = purok_stats[0]['purok'] if purok_stats else None
    top_purok_count = purok_stats[0]['count'] if purok_stats else 0
    
    purok_labels = [p['purok'] for p in purok_stats[:15]]
    purok_counts = [p['count'] for p in purok_stats[:15]]
    purok_pending = [p['pending'] for p in purok_stats[:15]]
    purok_resolved = [p['resolved'] for p in purok_stats[:15]]
    
    cat_qs = all_reports.values('category').annotate(count=Count('id')).order_by('-count')
    cat_labels = [c['category'] for c in cat_qs]
    cat_data = [c['count'] for c in cat_qs]
    top_category = cat_labels[0].capitalize() if cat_labels else None
    
    twelve_ago = now - timezone.timedelta(days=365)
    trend_qs = (
        all_reports
        .filter(reported_at__gte=twelve_ago)
        .annotate(month=TruncMonth('reported_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    trend_labels = [t['month'].strftime('%b %Y') for t in trend_qs]
    trend_data = [t['count'] for t in trend_qs]
    
    status_qs = all_reports.values('status').annotate(count=Count('id')).order_by('-count')
    status_labels = [s['status'] for s in status_qs]
    status_data = [s['count'] for s in status_qs]
    
    reports_map = list(
        all_reports
        .exclude(latitude__isnull=True)
        .values('id', 'title', 'category', 'status', 'location', 'latitude', 'longitude', 'reported_at', 'reporter__username')
    )
    reports_map_json = _json.dumps([
        {
            'id': r['id'],
            'title': r['title'],
            'category': r['category'],
            'status': r['status'],
            'location': r['location'] or '',
            'lat': float(r['latitude']),
            'lng': float(r['longitude']),
            'reporter': r['reporter__username'],
            'date': r['reported_at'].strftime('%b %d, %Y') if r['reported_at'] else '',
        }
        for r in reports_map
    ])
    
    cluster_qs = (
        all_reports
        .exclude(purok__isnull=True).exclude(purok='')
        .exclude(latitude__isnull=True)
        .values('purok')
        .annotate(
            lat=Avg('latitude'),
            lng=Avg('longitude'),
            count=Count('id'),
            pending=Count('id', filter=Q(status='pending')),
            resolved=Count('id', filter=Q(status__in=['inprogress', 'resolved', 'rejected'])),
        )
        .order_by('-count')
    )
    purok_clusters_json = _json.dumps([
        {
            'purok': c['purok'],
            'lat': float(c['lat']),
            'lng': float(c['lng']),
            'count': c['count'],
            'pending': c['pending'],
            'resolved': c['resolved'],
        }
        for c in cluster_qs
    ])
    
    try:
        from .models import DeletedReport
        deleted_qs = DeletedReport.objects.all()
        total_deleted = deleted_qs.count()
        deleted_by_user = deleted_qs.filter(deleted_by_role='user').count()
        deleted_by_admin = deleted_qs.filter(deleted_by_role='admin').count()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        deleted_this_month = deleted_qs.filter(deleted_at__gte=month_start).count()
        
        paginator = Paginator(deleted_qs, 25)
        page_num = request.GET.get('page', 1)
        deleted_records = paginator.get_page(page_num)
    except Exception as e:
        total_deleted = deleted_by_user = deleted_by_admin = deleted_this_month = 0
        deleted_records = []
    
    context = {
        'purok_stats': purok_stats,
        'total_puroks': total_puroks,
        'top_purok': top_purok,
        'top_purok_count': top_purok_count,
        'top_category': top_category,
        'total_reports_all': total_reports_all,
        'pending_total': pending_total,
        'purok_labels_json': _json.dumps(purok_labels),
        'purok_counts_json': _json.dumps(purok_counts),
        'purok_pending_json': _json.dumps(purok_pending),
        'purok_resolved_json': _json.dumps(purok_resolved),
        'cat_labels_json': _json.dumps(cat_labels),
        'cat_data_json': _json.dumps(cat_data),
        'trend_labels_json': _json.dumps(trend_labels),
        'trend_data_json': _json.dumps(trend_data),
        'status_labels_json': _json.dumps(status_labels),
        'status_data_json': _json.dumps(status_data),
        'reports_map_json': reports_map_json,
        'purok_clusters_json': purok_clusters_json,
        'total_deleted': total_deleted,
        'deleted_by_user': deleted_by_user,
        'deleted_by_admin': deleted_by_admin,
        'deleted_this_month': deleted_this_month,
        'deleted_records': deleted_records,
    }
    return render(request, 'waste_management/admin_analytics.html', context)


@login_required
def admin_delete_report(request, report_id):
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        report = WasteReport.objects.get(id=report_id)
        
        try:
            from .models import DeletedReport
            DeletedReport.objects.create(
                original_id=report.id,
                title=report.title,
                description=report.description or '',
                category=report.category,
                status=report.status,
                location=report.location or '',
                purok=report.purok or '',
                image=report.image.url if report.image else '',
                notes=report.notes or '',
                points_awarded=report.points_awarded or 0,
                latitude=getattr(report, 'latitude', None),
                longitude=getattr(report, 'longitude', None),
                reporter_id=report.reporter.id,
                reporter_username=report.reporter.username,
                reporter_full_name=report.reporter.get_full_name(),
                reported_at=report.reported_at,
                collected_at=getattr(report, 'collected_at', None),
                deleted_by_id=request.user.id,
                deleted_by_username=request.user.username,
                deleted_by_role='admin',
            )
        except Exception as e:
            print(f"Archive error: {e}")
        
        report.delete()
        
        return JsonResponse({'success': True})
    except WasteReport.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Report not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    

@login_required
def admin_archive(request):
    if not request.user.is_superuser:
        return redirect('dashboard')
    
    archived_reports = WasteReport.objects.filter(is_archived=True, is_draft=False).select_related('reporter').order_by('-archived_at', '-reported_at')
    
    status = request.GET.get('status')
    category = request.GET.get('category')
    search = request.GET.get('search')
    
    if status:
        archived_reports = archived_reports.filter(status=status)
    if category:
        archived_reports = archived_reports.filter(category=category)
    if search:
        archived_reports = archived_reports.filter(
            Q(title__icontains=search) |
            Q(reporter__username__icontains=search) |
            Q(location__icontains=search)
        )
    
    paginator = Paginator(archived_reports, 20)
    page_num = request.GET.get('page', 1)
    archived_reports_page = paginator.get_page(page_num)
    
    total_archived = WasteReport.objects.filter(is_archived=True, is_draft=False).count()
    archived_this_month = WasteReport.objects.filter(
        is_archived=True, is_draft=False,
        archived_at__year=timezone.now().year,
        archived_at__month=timezone.now().month
    ).count()
    resolved_count = WasteReport.objects.filter(is_archived=True, is_draft=False, status='resolved').count()
    rejected_count = WasteReport.objects.filter(is_archived=True, is_draft=False, status='rejected').count()
    
    context = {
        'archived_reports': archived_reports_page,
        'total_archived': total_archived,
        'archived_this_month': archived_this_month,
        'resolved_count': resolved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'waste_management/admin_archive.html', context)



def check_username_exists(request):
    """API endpoint to check if a username exists"""
    username = request.GET.get('username', '')
    exists = User.objects.filter(username=username).exists()
    return JsonResponse({'exists': exists})

# Add this function for forgot password
def forgot_password_api(request):
    """API endpoint to send password reset link"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'})
    
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email is required'})
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # For security, don't reveal if email exists
            return JsonResponse({'success': True, 'message': 'If an account exists, a reset link has been sent.'})
        
        # Generate reset token
        import secrets
        token = secrets.token_urlsafe(32)
        
        # Store in session or create a PasswordReset model
        request.session[f'reset_token_{user.id}'] = token
        
        reset_link = f"{request.build_absolute_uri('/')}reset-password/{token}/"
        
        # Send email (configure email settings first)
        try:
            send_mail(
                'Password Reset - ReporTrash',
                f'Hello {user.username},\n\nClick the link below to reset your password:\n\n{reset_link}\n\nIf you didn\'t request this, please ignore this email.\n\nThis link expires in 24 hours.\n\n- ReporTrash Team',
                'noreply@reportrash.com',
                [email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Email error: {e}")
            # Still return success to prevent email enumeration
            pass
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        print(f"Password reset error: {e}")
        return JsonResponse({'success': False, 'error': 'An error occurred. Please try again later.'})

# ==================== ADMIN USER MANAGEMENT API ====================

@login_required
def admin_users_api(request):
    """API endpoint to get all users for admin management"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    users = User.objects.all().select_related('barangay_profile').order_by('-date_joined')
    
    user_list = []
    for user in users:
        try:
            profile = user.barangay_profile
            barangay = profile.barangay_name
            purok = profile.purok
            avatar_color = profile.avatar_color
            profile_picture = profile.profile_picture.url if profile.profile_picture else None
            points = profile.points
            approval_status = profile.approval_status
        except BarangayProfile.DoesNotExist:
            barangay = 'Barangay Zone 1'
            purok = ''
            avatar_color = '#22c55e'
            profile_picture = None
            points = 0
            approval_status = 'approved'
        
        status = 'active'
        if approval_status == 'disabled':
            status = 'disabled'
        elif approval_status == 'pending':
            status = 'pending'
        
        user_list.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name(),
            'barangay': barangay,
            'purok': purok,
            'role': 'admin' if user.is_superuser else 'user',
            'status': status,
            'points': points,
            'avatar_color': avatar_color,
            'profile_picture': profile_picture,
            'report_count': WasteReport.objects.filter(reporter=user, is_draft=False).count(),
            'date_joined': user.date_joined.strftime('%b %d, %Y'),
        })
    
    return JsonResponse({'success': True, 'users': user_list})


@login_required
def admin_user_save_api(request):
    """API endpoint to create or update a user"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    user_id = request.POST.get('user_id')
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '')
    first_name = request.POST.get('first_name', '')
    last_name = request.POST.get('last_name', '')
    barangay = request.POST.get('barangay', 'Barangay Zone 1')
    purok = request.POST.get('purok', '')
    role = request.POST.get('role', 'user')
    status = request.POST.get('status', 'active')
    
    if not username or not email:
        return JsonResponse({'success': False, 'error': 'Username and email are required'})
    
    try:
        if user_id:
            # Update existing user
            user = User.objects.get(id=user_id)
            
            # Check username uniqueness (excluding current user)
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                return JsonResponse({'success': False, 'error': 'Username already taken'})
            
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return JsonResponse({'success': False, 'error': 'Email already registered'})
            
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            if password and len(password) >= 8:
                user.set_password(password)
            user.save()
            
            # Update admin status
            if role == 'admin':
                user.is_superuser = True
                user.is_staff = True
            else:
                user.is_superuser = False
                user.is_staff = False
            user.save()
            
            # Update profile
            profile, _ = BarangayProfile.objects.get_or_create(user=user)
            profile.barangay_name = barangay
            profile.purok = purok
            
            # Map status to approval_status
            if status == 'disabled':
                profile.approval_status = 'disabled'
            elif status == 'pending':
                profile.approval_status = 'pending'
            else:
                profile.approval_status = 'approved'
            profile.save()
            
        else:
            # Create new user
            if User.objects.filter(username=username).exists():
                return JsonResponse({'success': False, 'error': 'Username already taken'})
            
            if User.objects.filter(email=email).exists():
                return JsonResponse({'success': False, 'error': 'Email already registered'})
            
            if not password or len(password) < 8:
                return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters'})
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            
            if role == 'admin':
                user.is_superuser = True
                user.is_staff = True
                user.save()
            
            profile = BarangayProfile.objects.create(
                user=user,
                barangay_name=barangay,
                purok=purok,
                approval_status='approved' if status == 'active' else status
            )
        
        return JsonResponse({'success': True, 'message': 'User saved successfully'})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def admin_user_delete_api(request):
    """API endpoint to delete a user"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    user_id = request.POST.get('user_id')
    
    if not user_id:
        return JsonResponse({'success': False, 'error': 'User ID required'})
    
    try:
        user = User.objects.get(id=user_id)
        
        # Prevent admin from deleting themselves
        if user.id == request.user.id:
            return JsonResponse({'success': False, 'error': 'You cannot delete your own account'})
        
        # Delete associated profile (cascades automatically due to OneToOne)
        user.delete()
        
        return JsonResponse({'success': True, 'message': 'User deleted successfully'})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def admin_user_status_api(request):
    """API endpoint to enable/disable a user account"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    user_id = request.POST.get('user_id')
    action = request.POST.get('action')
    
    if not user_id or not action:
        return JsonResponse({'success': False, 'error': 'Missing parameters'})
    
    try:
        user = User.objects.get(id=user_id)
        
        # Prevent admin from disabling themselves
        if user.id == request.user.id and action == 'disable':
            return JsonResponse({'success': False, 'error': 'You cannot disable your own account'})
        
        profile, _ = BarangayProfile.objects.get_or_create(user=user)
        
        if action == 'disable':
            profile.approval_status = 'disabled'
            user.is_active = False
            message = 'User disabled'
            
            # Notify the user
            Notification.objects.create(
                user=user,
                title='Account Disabled',
                message='Your ReporTrash account has been disabled by an administrator. Please contact your barangay admin for assistance.',
                notification_type='system',
                url='/disabled-account/'
            )
            
        elif action == 'enable':
            profile.approval_status = 'approved'
            user.is_active = True
            message = 'User enabled'
            
            # Notify the user
            Notification.objects.create(
                user=user,
                title='Account Re-enabled',
                message='Your ReporTrash account has been re-enabled. You can now log in and submit reports again.',
                notification_type='system',
                url='/dashboard/'
            )
            
        else:
            return JsonResponse({'success': False, 'error': 'Invalid action'})
        
        profile.save()
        user.save()
        
        return JsonResponse({'success': True, 'message': message})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
# ==================== CHAT WITH ADMIN FUNCTIONS ====================

@login_required
def chat_send_api(request):
    """API endpoint to send a chat message to admin"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        
        if not message:
            return JsonResponse({'success': False, 'error': 'Message cannot be empty'})
        
        # Create chat message
        chat_msg = ChatMessage.objects.create(
            user=request.user,
            message=message,
            sender='user',
            status='open'
        )
        
        # Notify all admins
        for admin in User.objects.filter(is_superuser=True):
            Notification.objects.create(
                user=admin,
                title=f'New Chat from {request.user.username}',
                message=message[:100] + ('...' if len(message) > 100 else ''),
                notification_type='chat',
                url=f'/dashboard/admin-chats/?user={request.user.id}'
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Message sent to admin. They will respond shortly.',
            'chat_id': chat_msg.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def chat_get_messages_api(request):
    """API endpoint to get user's chat messages with admin"""
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        # Get all chat messages for this user
        messages = ChatMessage.objects.filter(user=request.user).order_by('created_at')
        
        # Mark user's messages as read
        unread_messages = messages.filter(sender='admin', is_read=False)
        for msg in unread_messages:
            msg.is_read = True
            msg.read_at = timezone.now()
            msg.save()
        
        messages_data = [{
            'id': m.id,
            'message': m.message,
            'sender': m.sender,
            'status': m.status,
            'created_at': m.created_at.strftime('%I:%M %p, %b %d'),
            'is_read': m.is_read,
        } for m in messages]
        
        # Check if there's an open conversation
        has_open_chat = messages.filter(status='open').exists()
        
        return JsonResponse({
            'success': True,
            'messages': messages_data,
            'has_open_chat': has_open_chat,
            'unread_count': messages.filter(sender='admin', is_read=False).count()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def admin_chat_api(request):
    """Admin API endpoint to get all user chats"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method == 'GET':
        # Get all users who have sent chat messages
        users_with_chats = User.objects.filter(chat_messages__isnull=False).distinct()
        
        chat_users = []
        for user in users_with_chats:
            last_message = ChatMessage.objects.filter(user=user).order_by('-created_at').first()
            unread_count = ChatMessage.objects.filter(user=user, sender='user', is_read=False).count()
            open_chats = ChatMessage.objects.filter(user=user, status='open').exists()
            
            chat_users.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'avatar_color': user.barangay_profile.avatar_color if hasattr(user, 'barangay_profile') else '#22c55e',
                'last_message': last_message.message[:50] if last_message else '',
                'last_message_time': last_message.created_at.strftime('%I:%M %p, %b %d') if last_message else '',
                'unread_count': unread_count,
                'has_open_chat': open_chats,
            })
        
        # Sort by last message time (most recent first)
        chat_users.sort(key=lambda x: x['last_message_time'], reverse=True)
        
        return JsonResponse({'success': True, 'users': chat_users})
    
    elif request.method == 'POST':
        # Send admin reply
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            message = data.get('message', '').strip()
            
            if not user_id or not message:
                return JsonResponse({'success': False, 'error': 'Missing required fields'})
            
            user = User.objects.get(id=user_id)
            
            # Create admin reply
            chat_msg = ChatMessage.objects.create(
                user=user,
                message=message,
                sender='admin',
                status='open'
            )
            
            # Notify the user
            Notification.objects.create(
                user=user,
                title=f'Admin replied to your chat',
                message=message[:100] + ('...' if len(message) > 100 else ''),
                notification_type='chat',
                url='/chat/'
            )
            
            return JsonResponse({'success': True, 'message': 'Reply sent'})
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})


@login_required
def admin_chat_messages_api(request, user_id):
    """Admin API endpoint to get chat messages for a specific user"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        user = User.objects.get(id=user_id)
        messages = ChatMessage.objects.filter(user=user).order_by('created_at')
        
        # Mark user messages as read when admin views them
        for msg in messages.filter(sender='user', is_read=False):
            msg.is_read = True
            msg.read_at = timezone.now()
            msg.save()
        
        messages_data = [{
            'id': m.id,
            'message': m.message,
            'sender': m.sender,
            'created_at': m.created_at.strftime('%I:%M %p, %b %d'),
            'is_read': m.is_read,
        } for m in messages]
        
        return JsonResponse({'success': True, 'messages': messages_data, 'user': user.username})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})


@login_required
def admin_close_chat_api(request, user_id):
    """Admin API endpoint to close a chat conversation"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        user = User.objects.get(id=user_id)
        ChatMessage.objects.filter(user=user, status='open').update(status='closed')
        
        # Notify user
        Notification.objects.create(
            user=user,
            title='Chat Conversation Closed',
            message='Your chat with admin has been closed. Start a new conversation if you need further assistance.',
            notification_type='chat',
            url='/chat/'
        )
        
        return JsonResponse({'success': True, 'message': 'Chat closed'})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})


@login_required
def user_close_chat_api(request):
    """User API endpoint to close their own chat"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        ChatMessage.objects.filter(user=request.user, status='open').update(status='closed')
        return JsonResponse({'success': True, 'message': 'Chat closed'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def admin_chat_page(request):
    if not request.user.is_superuser:
        return redirect('dashboard')
    return render(request, 'waste_management/admin_chat.html')

# ==================== USER CHAT (AI BOT) ====================


@login_required
def user_chat_history_api(request):
    """Get user's chat history based on current mode"""
    mode = request.GET.get('mode', 'ai')
    from django.utils import timezone
    
    # Update user's chat mode in profile - THIS IS CRITICAL
    profile = request.user.barangay_profile
    old_mode = profile.chat_mode if hasattr(profile, 'chat_mode') else 'ai'
    
    if mode != old_mode:
        profile.chat_mode = mode
        if mode == 'ai':
            # When switching to AI mode, close all human chats
            from .models import ChatMessage
            ChatMessage.objects.filter(
                user=request.user, 
                status__in=['pending_human', 'human_active']
            ).update(status='closed')
            profile.chat_session_active = False
        else:
            profile.chat_session_active = True
        profile.save()
        print(f"User {request.user.username} switched from {old_mode} to {mode}")
    
    if mode == 'ai':
        # AI Mode: Only show Chatbot messages
        session = ChatbotSession.objects.filter(user=request.user, is_active=True).first()
        if not session:
            session = ChatbotSession.objects.create(user=request.user)
        
        messages = []
        for msg in session.messages.all().order_by('created_at'):
            # Convert to local time (Asia/Manila)
            local_time = timezone.localtime(msg.created_at)
            formatted_time = local_time.strftime('%I:%M %p')
            
            messages.append({
                'content': msg.content,
                'sender': 'user' if msg.role == 'user' else 'ai',
                'sender_name': request.user.username if msg.role == 'user' else 'TrashBot AI',
                'created_at': formatted_time,
                'role': msg.role
            })
        
        return JsonResponse({
            'session_id': session.id,
            'messages': messages,
            'mode': 'ai',
            'has_pending_human': False,
            'has_active_human': False
        })
    
    else:
        # Human Mode: Only show messages from admin (ChatMessage model)
        from .models import ChatMessage
        messages = ChatMessage.objects.filter(
            user=request.user
        ).order_by('created_at')
        
        # Mark admin messages as read
        messages.filter(sender='admin', is_read=False).update(is_read=True, read_at=timezone.now())
        
        messages_data = []
        for msg in messages:
            # Convert to local time (Asia/Manila)
            local_time = timezone.localtime(msg.created_at)
            formatted_time = local_time.strftime('%I:%M %p')
            
            messages_data.append({
                'id': msg.id,
                'content': msg.message,
                'sender': msg.sender,
                'sender_name': 'Support Team' if msg.sender == 'admin' else request.user.username,
                'created_at': formatted_time,
                'is_read': msg.is_read
            })
        
        # Check if there's a pending request
        has_pending = messages.filter(status='pending_human').exists()
        has_active = messages.filter(status='human_active').exists()
        
        return JsonResponse({
            'messages': messages_data,
            'mode': 'human',
            'has_pending_human': has_pending,
            'has_active_human': has_active
        })


@login_required
def user_chat_send_api(request):
    """Send message from user - handles both AI and Human modes"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    try:
        body = json.loads(request.body)
        message = body.get('message', '').strip()
        session_id = body.get('session_id')
        
        if not message:
            return JsonResponse({'error': 'Empty message'}, status=400)
        
        profile = request.user.barangay_profile
        current_mode = profile.chat_mode if hasattr(profile, 'chat_mode') else 'ai'
        
        print(f"User {request.user.username} sending message in mode: {current_mode}")  # Debug
        
        # Check for mode switching keywords
        lower_message = message.lower()
        
        # Keywords to switch to human mode
        human_keywords = ['talk to admin', 'speak to admin', 'human support', 'real person', 
                         'live agent', 'contact admin', 'i need a human', 'talk to human',
                         'help me', 'admin please', 'human', 'customer support', 
                         'can i talk to admin', 'chat with admin', 'speak to human']
        
        # Keywords to switch to AI mode
        ai_keywords = ['talk to ai', 'switch to ai', 'back to ai', 'ai assistant',
                      'go back to ai', 'ai please', 'trashbot', 'back to bot',
                      'switch to ai mode', 'ai mode', 'back to assistant']
        
        # Check for mode switch requests
        for keyword in human_keywords:
            if keyword in lower_message:
                if current_mode != 'human':
                    print(f"Switching to HUMAN mode by keyword: {keyword}")  # Debug
                    return switch_to_human_mode(request, message)
                break
        
        for keyword in ai_keywords:
            if keyword in lower_message:
                if current_mode != 'ai':
                    print(f"Switching to AI mode by keyword: {keyword}")  # Debug
                    return switch_to_ai_mode(request, message)
                break
        
        # If in human mode, send to admin
        if current_mode == 'human':
            print(f"Sending message to ADMIN: {message[:50]}")  # Debug
            
            # Create human message
            chat_msg = ChatMessage.objects.create(
                user=request.user,
                message=message,
                sender='user',
                status='human_active'
            )
            
            # Notify admins
            for admin in User.objects.filter(is_superuser=True):
                Notification.objects.create(
                    user=admin,
                    title=f'💬 New Message from {request.user.username}',
                    message=message[:100] + ('...' if len(message) > 100 else ''),
                    notification_type='chat',
                    url='/dashboard/admin-chats/'
                )
            
            return JsonResponse({
                'reply': '✅ Message sent to admin. They will respond shortly.',
                'sender': 'system',
                'mode': 'human'
            })
        
        # Otherwise, use AI
        print(f"Sending message to AI: {message[:50]}")  # Debug
        
        session = None
        if session_id:
            session = ChatbotSession.objects.filter(pk=session_id, user=request.user).first()
        
        if not session:
            ChatbotSession.objects.filter(user=request.user, is_active=True).update(is_active=False)
            session = ChatbotSession.objects.create(user=request.user)
        
        # Save user message
        ChatbotMessage.objects.create(session=session, role='user', content=message)
        
        # Get conversation history
        recent_msgs = session.messages.order_by('-created_at')[:20]
        history = [{'role': m.role, 'content': m.content} for m in reversed(list(recent_msgs))]
        
        GROQ_API_KEY = getattr(settings, 'GROQ_API_KEY', None)
        if not GROQ_API_KEY:
            return JsonResponse({'error': 'AI service not configured'}, status=500)
        
        AI_PROMPT = """You are TrashBot, a friendly AI assistant for ReporTrash — a community waste management platform. Help with:
- Waste reports (biodegradable, recyclable, residual, special, hazardous, electronic)
- Report status tracking
- Points and rewards system
- Collection schedules
- Community features
- Announcements

IMPORTANT: If the user wants to talk to a human admin, respond with exactly: "HUMAN_REQUEST" and nothing else.
Be friendly and concise. Respond in the user's language (English/Tagalog/Bisaya)."""
        
        groq_messages = [{'role': 'system', 'content': AI_PROMPT}] + history
        
        response = requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'},
            json={'model': 'llama-3.1-8b-instant', 'messages': groq_messages, 'max_tokens': 500},
            timeout=30
        )
        
        if response.status_code != 200:
            return JsonResponse({'error': 'AI API error'}, status=502)
        
        data = response.json()
        reply = data['choices'][0]['message']['content']
        
        # Check if AI wants to escalate to human
        if reply.strip() == "HUMAN_REQUEST":
            return switch_to_human_mode(request, message)
        
        # Save AI response
        ChatbotMessage.objects.create(session=session, role='assistant', content=reply)
        
        return JsonResponse({
            'reply': reply,
            'session_id': session.pk,
            'sender': 'ai',
            'mode': 'ai'
        })
        
    except Exception as e:
        print(f"Error in user_chat_send_api: {e}")  # Debug
        return JsonResponse({'error': str(e)}, status=500)





@login_required
def user_delete_conversation_api(request):
    """User deletes their conversation"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        profile = request.user.barangay_profile
        
        # Delete all messages
        from .models import ChatMessage
        ChatMessage.objects.filter(user=request.user).delete()
        
        sessions = ChatbotSession.objects.filter(user=request.user)
        for session in sessions:
            session.messages.all().delete()
        sessions.delete()
        
        # Reset mode to AI
        profile.chat_mode = 'ai'
        profile.chat_session_active = False
        profile.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ==================== ADMIN SUPPORT CHAT - FIXED ====================

@login_required
def admin_support_users_api(request):
    """Admin gets list of users who are in HUMAN mode only - EXCLUDE AI MODE USERS"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    from .models import ChatMessage
    from django.utils import timezone
    
    # IMPORTANT: Only get users who are in HUMAN mode
    profiles_in_human_mode = BarangayProfile.objects.filter(chat_mode='human').select_related('user')
    
    # Also include users who have pending human messages
    users_with_pending = User.objects.filter(
        chat_messages__status='pending_human'
    ).distinct()
    
    # Combine and deduplicate
    user_ids = set()
    for profile in profiles_in_human_mode:
        user_ids.add(profile.user.id)
    for user in users_with_pending:
        user_ids.add(user.id)
    
    users = []
    for user_id in user_ids:
        try:
            user = User.objects.get(id=user_id)
            profile = user.barangay_profile
            
            # Skip if user is in AI mode (double check)
            if hasattr(profile, 'chat_mode') and profile.chat_mode == 'ai':
                has_pending = ChatMessage.objects.filter(user=user, status='pending_human').exists()
                if not has_pending:
                    continue
            
            # Get last message - order by created_at descending to get the most recent
            last_msg = ChatMessage.objects.filter(user=user).order_by('-created_at').first()
            
            unread_count = ChatMessage.objects.filter(user=user, sender='user', is_read=False).count()
            
            # Determine user mode
            has_pending = ChatMessage.objects.filter(user=user, status='pending_human').exists()
            has_active = ChatMessage.objects.filter(user=user, status='human_active').exists()
            
            # Calculate time ago for display using local time
            last_message_time = ''
            timestamp = 0
            if last_msg:
                # Convert to local time for accurate difference
                local_msg_time = timezone.localtime(last_msg.created_at)
                local_now = timezone.localtime(timezone.now())
                diff = local_now - local_msg_time
                timestamp = last_msg.created_at.timestamp()
                
                if diff.days > 0:
                    last_message_time = f'{diff.days}d ago'
                elif diff.seconds >= 3600:
                    hours = diff.seconds // 3600
                    last_message_time = f'{hours}h ago'
                elif diff.seconds >= 60:
                    minutes = diff.seconds // 60
                    last_message_time = f'{minutes}m ago'
                else:
                    last_message_time = 'Just now'
            
            users.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'avatar_color': profile.avatar_color,
                'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
                'last_message': last_msg.message[:50] if last_msg else 'No messages yet',
                'last_message_time': last_message_time,
                'last_message_timestamp': timestamp,
                'unread_count': unread_count,
                'user_mode': 'human',
                'has_pending_request': has_pending,
                'is_active_conversation': has_active
            })
        except User.DoesNotExist:
            continue
    
    # Sort: pending first, then by most recent message
    users.sort(key=lambda x: (
        -1 if x.get('has_pending_request') else 0,
        -x.get('last_message_timestamp', 0)
    ))
    
    return JsonResponse({'success': True, 'users': users})


@login_required
def admin_support_messages_api(request, user_id):
    """Admin gets chat messages for a specific user"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    from .models import ChatMessage
    from django.utils import timezone
    
    try:
        user = User.objects.get(id=user_id)
        profile = user.barangay_profile
        
        # Check if user is in human mode
        is_human_mode = hasattr(profile, 'chat_mode') and profile.chat_mode == 'human'
        has_pending = ChatMessage.objects.filter(user=user, status='pending_human').exists()
        has_active = ChatMessage.objects.filter(user=user, status='human_active').exists()
        
        # Get ONLY human chat messages - NO AI messages
        human_msgs = ChatMessage.objects.filter(user=user).order_by('created_at')
        
        # Mark user messages as read when admin views
        human_msgs.filter(sender='user', is_read=False).update(is_read=True, read_at=timezone.now())
        
        messages = []
        for msg in human_msgs:
            # Convert to local time (Asia/Manila)
            local_time = timezone.localtime(msg.created_at)
            
            # Skip showing "[User requested human support]" if it's a duplicate system message
            display_message = msg.message
            if msg.message == "[User requested human support]":
                display_message = "User requested to speak with an admin"
            
            sender_name = 'User' if msg.sender == 'user' else 'Admin'
            if msg.sender == 'system':
                sender_name = 'System'
            
            # Format time in 12-hour format with AM/PM using local time
            formatted_time = local_time.strftime('%I:%M %p, %b %d')
            
            messages.append({
                'id': msg.id,
                'message': display_message,
                'sender': msg.sender,
                'sender_name': sender_name,
                'created_at': formatted_time,
                'is_read': msg.is_read
            })
        
        # Build user object for frontend
        user_data = {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'avatar_color': profile.avatar_color,
            'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
            'chat_mode': profile.chat_mode if hasattr(profile, 'chat_mode') else 'ai',
        }
        
        can_chat = is_human_mode or has_pending or has_active
        
        return JsonResponse({
            'success': True,
            'messages': messages,
            'user': user_data,
            'user_mode': 'human' if can_chat else 'ai',
            'is_human_mode': can_chat,
            'can_chat': can_chat
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    
@login_required
def admin_support_reply_api(request):
    """Admin replies to a user - only allowed if user is in human mode"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        user_id = data.get('user_id')
        message = data.get('message', '').strip()
        
        if not user_id or not message:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        user = User.objects.get(id=user_id)
        
        from .models import ChatMessage
        from django.utils import timezone
        
        # Check if user is in human mode
        has_pending = ChatMessage.objects.filter(user=user, status='pending_human').exists()
        has_active = ChatMessage.objects.filter(user=user, status='human_active').exists()
        
        if not (has_pending or has_active):
            return JsonResponse({'success': False, 'error': 'User is not in human support mode'})
        
        # Create admin reply
        admin_msg = ChatMessage.objects.create(
            user=user,
            message=message,
            sender='admin',
            status='human_active',
            created_at=timezone.now()
        )
        
        # Update pending to active
        ChatMessage.objects.filter(user=user, status='pending_human').update(status='human_active')
        
        # Notify user
        Notification.objects.create(
            user=user,
            title='📩 Admin Replied to Your Chat',
            message=message[:100] + ('...' if len(message) > 100 else ''),
            notification_type='chat',
            url='/chat/'
        )
        
        # Convert to local time for display
        local_time = timezone.localtime(admin_msg.created_at)
        now_local = timezone.localtime(timezone.now())
        diff = now_local - local_time
        
        if diff.days > 0:
            time_display = f'{diff.days}d ago'
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            time_display = f'{hours}h ago'
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            time_display = f'{minutes}m ago'
        else:
            time_display = 'Just now'
        
        # Format time for display using local time
        formatted_time = local_time.strftime('%I:%M %p, %b %d')
        
        # Return the message with its timestamp for immediate UI update
        return JsonResponse({
            'success': True, 
            'message': 'Reply sent',
            'message_data': {
                'id': admin_msg.id,
                'message': admin_msg.message,
                'sender': admin_msg.sender,
                'created_at': formatted_time,
                'time_ago': time_display,
                'timestamp': admin_msg.created_at.timestamp()
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
@login_required
def admin_close_chat_api(request, user_id):
    """Admin closes a chat conversation"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        user = User.objects.get(id=user_id)
        
        from .models import ChatMessage
        ChatMessage.objects.filter(user=user, status__in=['pending_human', 'human_active']).update(status='closed')
        
        Notification.objects.create(
            user=user,
            title='Chat Conversation Closed',
            message='Your chat with admin has been closed. Start a new conversation if you need further assistance.',
            notification_type='chat',
            url='/chat/'
        )
        
        return JsonResponse({'success': True, 'message': 'Chat closed'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def admin_delete_conversation_api(request, user_id):
    """Admin deletes entire conversation with a user"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        user = User.objects.get(id=user_id)
        
        from .models import ChatMessage, ChatbotSession, ChatbotMessage
        
        # Delete all messages
        ChatMessage.objects.filter(user=user).delete()
        
        sessions = ChatbotSession.objects.filter(user=user)
        for session in sessions:
            session.messages.all().delete()
        sessions.delete()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def admin_user_detail_api(request, user_id):
    """Admin API endpoint to get detailed user information"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        user = User.objects.get(id=user_id)
        profile = user.barangay_profile if hasattr(user, 'barangay_profile') else None
        
        from .models import ChatMessage
        has_pending_human = ChatMessage.objects.filter(user=user, status='pending_human').exists()
        has_human_active = ChatMessage.objects.filter(user=user, status='human_active').exists()
        user_mode = 'human' if (has_pending_human or has_human_active) else 'ai'
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name(),
            'barangay': profile.barangay_name if profile else 'Barangay Zone 1',
            'purok': profile.purok if profile else '',
            'contact_number': profile.contact_number if profile else '',
            'address': profile.address if profile else '',
            'avatar_color': profile.avatar_color if profile else '#22c55e',
            'profile_picture': profile.profile_picture.url if profile and profile.profile_picture else None,
            'points': profile.points if profile else 0,
            'level': profile.level if profile else 'Eco Starter',
            'report_count': WasteReport.objects.filter(reporter=user, is_draft=False).count(),
            'date_joined': user.date_joined.strftime('%b %d, %Y'),
            'is_active': user.is_active,
            'user_mode': user_mode,
            'chat_mode': profile.chat_mode if profile else 'ai',  # Add this line
            'is_human_mode': profile.chat_mode == 'human' if profile else False,  # Add this line
        }
        
        return JsonResponse({'success': True, 'user': user_data})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found'})
    
@login_required
def user_chat_page(request):
    """User chat page with AI and human support"""
    return render(request, 'waste_management/user_chat.html')


from django.http import JsonResponse
from django.core.management import call_command
from django.views.decorators.csrf import csrf_exempt
import traceback

@csrf_exempt
def migrate_database(request):
    """Temporary endpoint to run migrations"""
    # Only allow in production or with a secret key
    secret = request.GET.get('secret', '')
    if secret != 'migrate_reportrash_2024':
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        # Run migrations
        call_command('migrate', interactive=False)
        return JsonResponse({'status': 'success', 'message': 'Migrations completed successfully'})
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': str(e),
            'traceback': traceback.format_exc()
        }, status=500)
