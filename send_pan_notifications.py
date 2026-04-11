import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'banking_project.settings')
django.setup()

from django.contrib.auth.models import User
from main.models import CustomerProfile, Notification

def send_notifications():
    profiles = CustomerProfile.objects.all()
    count = 0
    for profile in profiles:
        if profile.pan_number:
            Notification.objects.create(
                user=profile.user,
                title="Important: Your Assigned PAN Number",
                message=(
                    f"Dear {profile.user.username},\n\n"
                    f"Your Permanent Account Number (PAN) has been successfully generated and assigned to your Indie Bank account.\n\n"
                    f"PAN Number: {profile.pan_number}\n\n"
                    "This number will be required for credit card applications, taxes, and other high-value transactions. "
                    "Please keep this for your records."
                ),
                notification_type='SYSTEM'
            )
            count += 1
            print(f"Sent PAN notification to {profile.user.username}")

    print(f"Successfully sent notifications to {count} users.")

if __name__ == "__main__":
    send_notifications()
