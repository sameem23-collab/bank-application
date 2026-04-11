import os
import django
from django.test import RequestFactory
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'banking_project.settings')
django.setup()

from main.models import Complaint, Notification
from main.views import update_complaint_status, submit_complaint

def test_complaint_notification():
    user = User.objects.first()
    if not user:
        print("No user found")
        return
        
    # 1. Create a complaint associated with user
    complaint = Complaint.objects.create(
        user=user,
        full_name="Test User",
        email=user.email or "test@example.com",
        message="Test Complaint Message"
    )
    print(f"Created complaint: {complaint.complaint_id} for user: {user.username}")
    
    # 2. Update status via view
    factory = RequestFactory()
    request = factory.post(f'/admin-dashboard/complaints/{complaint.pk}/update/', {'status': 'IN_PROGRESS'})
    request.user = User.objects.filter(is_staff=True).first() or user # Mock admin
    
    # Add messages middleware support
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    try:
        response = update_complaint_status(request, complaint.pk)
        print(f"Update response status: {response.status_code}")
        
        # 3. Check if notification was created
        notif = Notification.objects.filter(user=user, notification_type='COMPLAINT').first()
        if notif:
            print(f"SUCCESS: Notification created! Title: {notif.title}")
            print(f"Message: {notif.message}")
        else:
            print("FAILED: No notification found for user.")
            
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    test_complaint_notification()
