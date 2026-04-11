import os
import django
import random
import string

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'banking_project.settings')
django.setup()

from main.models import CustomerProfile

def generate_pan():
    letters = ''.join(random.choices(string.ascii_uppercase, k=5))
    digits = ''.join(random.choices(string.digits, k=4))
    last_letter = random.choice(string.ascii_uppercase)
    return f"{letters}{digits}{last_letter}"

def backfill():
    profiles = CustomerProfile.objects.filter(pan_number__isnull=True) | CustomerProfile.objects.filter(pan_number='')
    count = 0
    used_pans = set(CustomerProfile.objects.exclude(pan_number__isnull=True).exclude(pan_number='').values_list('pan_number', flat=True))
    
    for profile in profiles:
        new_pan = generate_pan()
        while new_pan in used_pans:
            new_pan = generate_pan()
        
        profile.pan_number = new_pan
        profile.save()
        used_pans.add(new_pan)
        count += 1
        print(f"Assigned PAN {new_pan} to {profile.user.username}")

    print(f"Successfully backfilled {count} profiles.")

if __name__ == "__main__":
    backfill()
