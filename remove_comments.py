import os
import re

def remove_comments(content):
    # 1. Remove HTML comments: <!-- ... --> (multiline)
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    
    # 2. Remove Django block comments: {% comment %} ... {% endcomment %} (multiline)
    content = re.sub(r'{%\s*comment\s*%}.*?{%\s*endcomment\s*%}', '', content, flags=re.DOTALL)
    
    # 3. Remove Django inline comments: {# ... #}
    content = re.sub(r'{#.*?#}', '', content)
    
    # Optional: Clean up excessive empty lines (optional, but requested implicitly by "remove comment lines")
    # This regex replaces triple (or more) newlines with double newlines to keep layout but remove gaps.
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    return content

def process_templates(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                print(f"Processing: {path}")
                
                with open(path, 'r', encoding='utf-8') as f:
                    try:
                        content = f.read()
                    except UnicodeDecodeError:
                        # Fallback for other encodings if necessary
                        with open(path, 'r', encoding='latin-1') as f:
                            content = f.read()
                
                new_content = remove_comments(content)
                
                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"  Updated: {file}")
                else:
                    print(f"  No comments found in: {file}")

if __name__ == "__main__":
    template_dir = os.path.join(os.getcwd(), 'main', 'templates')
    if os.path.exists(template_dir):
        process_templates(template_dir)
        print("\nFinished removing comments from all HTML templates.")
    else:
        print(f"Error: Directory {template_dir} not found.")
