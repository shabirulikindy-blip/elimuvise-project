from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('dashboard', '0006_add_ai_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdvisorProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_main', models.BooleanField(default=False, help_text='Main advisor with full permissions')),
                ('can_edit', models.BooleanField(default=True, help_text='Assistant advisors can edit uploaded data')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='advisor_profile', to='dashboard.user')),
            ],
            options={
                'db_table': 'advisor_profiles',
            },
        ),
    ]
