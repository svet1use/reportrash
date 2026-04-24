from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='BarangayProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('barangay_name', models.CharField(default='Barangay 1', max_length=100)),
                ('purok', models.CharField(blank=True, max_length=50)),
                ('address', models.TextField(blank=True)),
                ('contact_number', models.CharField(blank=True, max_length=20)),
                ('avatar_color', models.CharField(default='#22c55e', max_length=7)),
                ('points', models.IntegerField(default=0)),
                ('level', models.CharField(default='Eco Starter', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='barangay_profile', to='auth.user')),
            ],
        ),
        migrations.CreateModel(
            name='WasteReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('category', models.CharField(choices=[('biodegradable', '🌿 Biodegradable'), ('recyclable', '♻️ Recyclable'), ('residual', '🗑️ Residual'), ('special', '⚠️ Special Waste'), ('hazardous', '☠️ Hazardous'), ('electronic', '📱 E-Waste')], max_length=50)),
                ('quantity_kg', models.DecimalField(decimal_places=2, max_digits=8)),
                ('location', models.CharField(max_length=200)),
                ('purok', models.CharField(blank=True, max_length=50)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('collected', 'Collected'), ('processed', 'Processed'), ('disposed', 'Disposed')], default='pending', max_length=20)),
                ('image', models.ImageField(blank=True, null=True, upload_to='waste_reports/')),
                ('reported_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('collected_at', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('points_awarded', models.IntegerField(default=0)),
                ('reporter', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='waste_reports', to='auth.user')),
            ],
            options={'ordering': ['-reported_at']},
        ),
        migrations.CreateModel(
            name='CollectionSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day_of_week', models.CharField(choices=[('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'), ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'), ('sunday', 'Sunday')], max_length=20)),
                ('waste_category', models.CharField(choices=[('biodegradable', '🌿 Biodegradable'), ('recyclable', '♻️ Recyclable'), ('residual', '🗑️ Residual'), ('special', '⚠️ Special Waste'), ('hazardous', '☠️ Hazardous'), ('electronic', '📱 E-Waste')], max_length=50)),
                ('time_start', models.TimeField()),
                ('time_end', models.TimeField()),
                ('purok', models.CharField(default='All', max_length=50)),
                ('collector_name', models.CharField(blank=True, max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('notes', models.TextField(blank=True)),
            ],
            options={'ordering': ['day_of_week', 'time_start']},
        ),
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('priority', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')], default='medium', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('emoji', models.CharField(default='📢', max_length=10)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='CommunityPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('image', models.ImageField(blank=True, null=True, upload_to='community/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_tip', models.BooleanField(default=False)),
                ('tip_category', models.CharField(blank=True, max_length=50)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='community_posts', to='auth.user')),
                ('likes', models.ManyToManyField(blank=True, related_name='liked_posts', to='auth.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='WasteStats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.DateField()),
                ('total_biodegradable_kg', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_recyclable_kg', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_residual_kg', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_special_kg', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_hazardous_kg', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_electronic_kg', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total_reports', models.IntegerField(default=0)),
                ('collection_rate', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
            ],
            options={'ordering': ['-month']},
        ),
    ]
