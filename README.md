# 🌿 EcoBarangay — Smart Waste Management System

A stunning, glassmorphic barangay solid waste reporting and management system built with Django.

## ✨ Features

- **Revolutionary glassmorphic bottom navigation** — floating pill navbar nobody's seen before
- **Animated landing page** with custom cursor, floating particles, and live mockup
- **Split-panel login** — features panel on left, auth form on right with live password strength
- **Gamified eco-points system** — earn points per report, level up from Newcomer → Eco Champion
- **Category-based waste reporting** — Biodegradable, Recyclable, Residual, Special, Hazardous, E-Waste
- **Visual analytics dashboard** — animated bar charts, category breakdowns, XP progress bar
- **Collection schedule viewer** — day-by-day tabs with today highlighted
- **Community hub** — post updates, share eco-tips, like posts
- **Interactive history** — filter by category/status, modal detail view
- **Profile customization** — avatar color picker, leaderboard, breakdown charts

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run setup (creates DB, demo data, sample accounts)
```bash
python setup.py
```

### 3. Start the server
```bash
python manage.py runserver
```

### 4. Open your browser
Visit: **http://127.0.0.1:8000**

## 👤 Demo Accounts

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Superuser |
| `juan` | `demo1234` | Demo User (320 pts) |
| `maria` | `demo1234` | Demo User (185 pts) |
| `pedro` | `demo1234` | Demo User (90 pts) |

## 🗂️ Pages

| Page | URL | Description |
|------|-----|-------------|
| Landing | `/` | Public landing with features showcase |
| Login/Register | `/login/` | Split-panel auth page |
| Dashboard | `/dashboard/` | Stats, charts, quick actions |
| Report | `/report/` | Submit new waste report |
| History | `/history/` | All reports with filtering |
| Community | `/community/` | Posts, eco-tips, likes |
| Profile | `/profile/` | Settings, leaderboard |
| Schedules | `/schedules/` | Collection calendar |
| Admin | `/admin/` | Django admin panel |

## 🎨 Design System

- **Colors**: Deep dark (`#030a0e`) + Neon green (`#00ff87`) + Cyan (`#00d4ff`)
- **Typography**: Syne (headings) + Space Grotesk (body) + DM Mono (labels)
- **Style**: Glassmorphism + ambient gradients + animated grid
- **Nav**: Floating pill bottom navigation with active lift effect

## 📁 Project Structure

```
barangay_waste/
├── barangay_waste/      # Django project config
├── waste_management/    # Main app
│   ├── models.py        # Database models
│   ├── views.py         # All views/logic
│   ├── urls.py          # URL routing
│   ├── templates/       # HTML templates
│   │   └── waste_management/
│   │       ├── base.html      # Base with glassmorphic nav
│   │       ├── landing.html   # Public landing page
│   │       ├── login.html     # Auth page
│   │       ├── dashboard.html # Main dashboard
│   │       ├── report.html    # Waste reporting
│   │       ├── history.html   # Report history
│   │       ├── community.html # Community feed
│   │       ├── profile.html   # User profile
│   │       └── schedules.html # Collection schedules
├── setup.py             # Quick setup & demo data
├── requirements.txt     # Python dependencies
└── manage.py            # Django management
```
