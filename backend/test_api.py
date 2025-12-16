#!/usr/bin/env python
import os
import django
import requests

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lockup_backend.settings')
django.setup()

from users.models import User
from rest_framework.authtoken.models import Token

# Get test user token
test_user = User.objects.get(username='test')
test_token, created = Token.objects.get_or_create(user=test_user)
print(f'Test user token: {test_token.key}')

# Test the correct API endpoint
url = 'http://127.0.0.1:8000/api/tasks/a652ea8e-5d60-4fb6-84d9-0e0afe2eee13/'
headers = {'Authorization': f'Token {test_token.key}'}

try:
    response = requests.get(url, headers=headers)
    print(f'Status code: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'Task type: {data.get("task_type")}')
        print(f'Task status: {data.get("status")}')
        print(f'Submission files count: {len(data.get("submission_files", []))}')
        for file in data.get('submission_files', []):
            print(f'  - {file["file_name"]} (is_image: {file["is_image"]})')
    else:
        print(f'Error response: {response.text}')
except Exception as e:
    print(f'Request failed: {e}')