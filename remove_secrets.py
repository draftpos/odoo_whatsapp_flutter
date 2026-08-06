import os, glob

root_dir = r'c:\Users\Ashley\odoo_whatsapp_flutter'
files = glob.glob(os.path.join(root_dir, '*.py')) + glob.glob(os.path.join(root_dir, '**', '*.py'), recursive=True)

count = 0
for f in files:
    if 'remove_secrets.py' in f:
        continue
    try:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
            
        if '***REMOVED***' in content:
            new_content = content.replace("'***REMOVED***'", "os.environ.get('SERVER_PASSWORD')")
            if 'import os' not in new_content:
                new_content = 'import os\n' + new_content
                
            with open(f, 'w', encoding='utf-8', newline='\n') as file:
                file.write(new_content)
            count += 1
            print(f'Replaced in {f}')
    except Exception as e:
        print(f'Error processing {f}: {e}')

print(f'Replaced password in {count} files.')
