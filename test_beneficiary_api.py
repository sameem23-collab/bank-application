import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'banking_project.settings')
django.setup()

from django.contrib.auth.models import User
from main.models import Beneficiary
from rest_framework.test import APIRequestFactory, force_authenticate
from main.api_views import BeneficiaryViewSet

def test_api():
    user = User.objects.first()
    if not user:
        print("No user found")
        return
        
    factory = APIRequestFactory()
    view = BeneficiaryViewSet.as_view({'get': 'list', 'post': 'create'})
    
    # Test GET
    request = factory.get('/api/beneficiaries/')
    # force_authenticate(request, user=user) # Optional, since I added fallback
    response = view(request)
    print(f"GET Response Status: {response.status_code}")
    print(f"GET Data Length: {len(response.data)}")
    
    # Test POST
    data = {'name': 'Test Dev', 'account_number': '123456789012'}
    request = factory.post('/api/beneficiaries/', data, format='json')
    response = view(request)
    print(f"POST Response Status: {response.status_code}")
    if response.status_code == 201:
        print("POST Success")
    else:
        print(f"POST Failed: {response.data}")

if __name__ == '__main__':
    test_api()
