from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from dashboard.models import Student, Result, Alert, SystemLog, Notification

User = get_user_model()

class Command(BaseCommand):
    help = 'Clears all existing database data and seeds the database with sample logins.'

    def handle(self, *args, **options):
        self.stdout.write('Clearing existing database records...')
        
        # Delete in order of dependency
        Notification.objects.all().delete()
        SystemLog.objects.all().delete()
        Alert.objects.all().delete()
        Result.objects.all().delete()
        Student.objects.all().delete()
        User.objects.all().delete()

        self.stdout.write('Database cleared. Seeding sample logins...')

        # 1. Create Admin (ElimuVISE / project2026)
        admin_user = User.objects.create_superuser(
            username='ElimuVISE',
            email='admin@example.com',
            password='project2026',
            role='admin',
            approved=True,
            first_name='System',
            last_name='Administrator'
        )
        self.stdout.write('OK: Seeded Admin: ElimuVISE / project2026')

        # 2. Create Advisor (advisor@example.com / advisor123)
        advisor_user = User.objects.create_user(
            username='advisor@example.com',
            email='advisor@example.com',
            password='advisor123',
            role='advisor',
            approved=True,
            first_name='Sarah',
            last_name='Mrema',
            school_name='ElimuVISE Academic Center'
        )
        self.stdout.write('OK: Seeded Advisor: advisor@example.com / advisor123')

        # 3. Create Student User and Profile (student123 / student123)
        student_user = User.objects.create_user(
            username='student123',
            email='student@example.com',
            password='student123',
            role='student',
            approved=True,
            first_name='John',
            last_name='Doe'
        )
        
        student_profile = Student.objects.create(
            user=student_user,
            form_level='Form 4',
            combination='PCM',
            attendance_rate=94.5,
            prediction='Low Risk',
            risk_level='low'
        )
        self.stdout.write('OK: Seeded Student Profile: student123 / student123')

        # Seed Results for Student
        results = [
            Result(student=student_profile, subject='Physics', score=85.0, assessment_name='Midterm Exam'),
            Result(student=student_profile, subject='Chemistry', score=78.0, assessment_name='Midterm Exam'),
            Result(student=student_profile, subject='Mathematics', score=92.0, assessment_name='Midterm Exam'),
            Result(student=student_profile, subject='Physics', score=88.0, assessment_name='Final Exam'),
            Result(student=student_profile, subject='Chemistry', score=82.0, assessment_name='Final Exam'),
            Result(student=student_profile, subject='Mathematics', score=95.0, assessment_name='Final Exam'),
        ]
        Result.objects.bulk_create(results)
        self.stdout.write('OK: Seeded mock results for student')

        # Seed Alerts for Student
        alerts = [
            Alert(student=student_profile, message='Excellent academic progress in Mathematics! Recommended for engineering track.'),
            Alert(student=student_profile, message='Maintain current high attendance rate of 94.5% to ensure exam eligibility.'),
        ]
        Alert.objects.bulk_create(alerts)
        self.stdout.write('OK: Seeded mock alerts for student')

        # 4. Create Parent (parent@example.com / parent123)
        parent_user = User.objects.create_user(
            username='parent@example.com',
            email='parent@example.com',
            password='parent123',
            role='parent',
            approved=True,
            first_name='Jane',
            last_name='Doe'
        )
        self.stdout.write('OK: Seeded Parent: parent@example.com / parent123')

        # 5. Create some System logs & Notifications
        SystemLog.objects.create(
            event_type='Database Seed',
            description='System database successfully seeded with mock data.'
        )
        Notification.objects.create(
            user=advisor_user,
            message='System initialization complete. Sample student profile John Doe is ready for review.'
        )
        self.stdout.write('OK: Seeded mock system logs and notifications')

        self.stdout.write(self.style.SUCCESS('Successfully seeded database with all sample accounts!'))
