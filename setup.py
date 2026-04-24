#!/usr/bin/env python3
"""
EcoBarangay - Quick Setup Script
Run this once to set up the database and create demo data.
Usage: python setup.py
"""
import os
import sys
import subprocess

def run(cmd):
    print(f"  → {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠ Warning: {result.stderr[:200]}")
    return result.returncode == 0

print("\n🌿 EcoBarangay Setup\n" + "="*40)

print("\n[1/4] Running migrations...")
run("python manage.py migrate")

print("\n[2/4] Creating sample data...")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'barangay_waste.settings')

import django
django.setup()

from django.contrib.auth.models import User
from waste_management.models import (BarangayProfile, WasteReport,
    CollectionSchedule, Announcement, CommunityPost)
from django.utils import timezone
from datetime import time
import random

# Create superuser
if not User.objects.filter(username='admin').exists():
    admin = User.objects.create_superuser('admin', 'admin@ecobarangay.local', 'admin123',
        first_name='Admin', last_name='User')
    BarangayProfile.objects.get_or_create(user=admin, defaults={
        'barangay_name': 'Barangay San Jose',
        'points': 500, 'level': 'Eco Champion',
        'avatar_color': '#00ff87'
    })
    print("  → Admin created (username: admin, password: admin123)")

# Create demo users
demo_users = [
    ('juan', 'juan@demo.com', 'demo1234', 'Juan', 'Dela Cruz', 'Barangay San Jose', '#3b82f6', 320),
    ('maria', 'maria@demo.com', 'demo1234', 'Maria', 'Santos', 'Barangay Rizal', '#f59e0b', 185),
    ('pedro', 'pedro@demo.com', 'demo1234', 'Pedro', 'Reyes', 'Barangay Bonifacio', '#a855f7', 90),
]
for username, email, pw, fn, ln, bn, color, pts in demo_users:
    if not User.objects.filter(username=username).exists():
        u = User.objects.create_user(username, email, pw, first_name=fn, last_name=ln)
        profile = BarangayProfile.objects.create(user=u, barangay_name=bn,
            avatar_color=color, points=pts)
        profile.update_level()
        print(f"  → Demo user created: {username} (password: demo1234)")

# Sample waste reports
juan = User.objects.filter(username='juan').first()
if juan and not WasteReport.objects.filter(reporter=juan).exists():
    categories = ['biodegradable', 'recyclable', 'residual', 'electronic', 'hazardous', 'special']
    locations = ['Purok 1 Corner', 'Near Covered Court', 'Sitio Bagong Buhay', 'Market Area', 'School Perimeter']
    for i in range(8):
        WasteReport.objects.create(
            reporter=juan,
            title=f"Waste Report #{i+1}",
            category=random.choice(categories),
            quantity_kg=random.uniform(2.5, 25.0),
            location=random.choice(locations),
            purok=f"Purok {random.randint(1,5)}",
            description="Sample waste report generated during setup.",
            status=random.choice(['pending', 'collected', 'processed', 'disposed']),
        )
    print("  → Sample waste reports created")

# Collection schedules
if not CollectionSchedule.objects.exists():
    schedules = [
        ('monday', 'biodegradable', time(6, 0), time(9, 0), 'All', 'Juan Collector'),
        ('monday', 'recyclable', time(9, 0), time(12, 0), 'Purok 1-3', 'Maria Collector'),
        ('wednesday', 'residual', time(6, 0), time(10, 0), 'All', ''),
        ('wednesday', 'hazardous', time(10, 0), time(12, 0), 'Purok 4-6', 'Pedro Collector'),
        ('friday', 'electronic', time(7, 0), time(11, 0), 'All', 'E-Waste Team'),
        ('saturday', 'special', time(8, 0), time(12, 0), 'Purok 1-6', 'Special Team'),
    ]
    for day, cat, ts, te, purok, collector in schedules:
        CollectionSchedule.objects.create(
            day_of_week=day, waste_category=cat,
            time_start=ts, time_end=te, purok=purok, collector_name=collector
        )
    print("  → Collection schedules created")

# Announcements
admin_user = User.objects.filter(username='admin').first()
if admin_user and not Announcement.objects.exists():
    Announcement.objects.create(
        title="Welcome to EcoBarangay!",
        content="Our new waste management system is live. Start reporting waste to earn eco-points!",
        priority='high', emoji='🎉', created_by=admin_user
    )
    Announcement.objects.create(
        title="Special Collection This Saturday",
        content="E-waste and hazardous materials will be collected from 8AM-12PM. Bring your old electronics!",
        priority='urgent', emoji='⚠️', created_by=admin_user
    )
    print("  → Announcements created")

# Community posts
if juan and not CommunityPost.objects.exists():
    CommunityPost.objects.create(
        author=juan,
        content="🌿 Tip: Segregate your biodegradable waste and use it for composting. It's great for your garden!",
        is_tip=True, tip_category='composting'
    )
    CommunityPost.objects.create(
        author=juan,
        content="Just submitted my weekly waste report! Already at 185 eco-points this month 🏆",
        is_tip=False
    )
    print("  → Community posts created")

print("\n[3/4] Setup complete! ✅")
print("\n" + "="*40)
print("🚀 To start the server:")
print("   python manage.py runserver")
print("\n🌐 Then open: http://127.0.0.1:8000")
print("\n👤 Demo accounts:")
print("   admin / admin123  (superuser)")
print("   juan  / demo1234")
print("   maria / demo1234")
print("   pedro / demo1234")
print("\n⚙️  Admin panel: http://127.0.0.1:8000/admin/")
print("="*40 + "\n")
