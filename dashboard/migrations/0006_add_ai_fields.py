from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('dashboard', '0005_result_edited_by_result_updated_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='result',
            name='ai_prediction',
            field=models.JSONField(blank=True, null=True, help_text='AI prediction metadata'),
        ),
        migrations.AddField(
            model_name='result',
            name='ai_recommendation',
            field=models.TextField(blank=True, null=True, help_text='AI recommendation text'),
        ),
    ]
