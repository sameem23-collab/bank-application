import os
import glob

files_to_update = [
    'main/views.py',
    'main/api_views.py',
    'main/templates/*.html'
]

replacement_pairs = [
    ('$', '₹'),
]

for pattern in files_to_update:
    for filepath in glob.glob(pattern):
        if os.path.isfile(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = content
            for old, new in replacement_pairs:
                new_content = new_content.replace(old, new)
            
            if new_content != content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {filepath}")
