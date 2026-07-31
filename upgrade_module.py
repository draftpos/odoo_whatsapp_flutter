import xmlrpc.client

url = 'https://demo1.havano.pro'
db = 'demo1_havano_pro_pknuzuhckrvwadhoboithcke'
username = 'admin'
password = 'admin'
module_name = 'whatsapp_web_chats'

try:
    print(f"Connecting to {url}...")
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})
    if not uid:
        print("Auth failed.")
    else:
        print(f"Authenticated as uid: {uid}")
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        
        print("Updating apps list...")
        models.execute_kw(db, uid, password, 'ir.module.module', 'update_list', [])
        
        print(f"Searching for module '{module_name}'...")
        module_ids = models.execute_kw(db, uid, password,
            'ir.module.module', 'search',
            [[['name', '=', module_name]]])
            
        if not module_ids:
            print(f"Module {module_name} not found! Did it upload correctly?")
        else:
            module_id = module_ids[0]
            print(f"Found module {module_name} with ID {module_id}. Upgrading...")
            models.execute_kw(db, uid, password,
                'ir.module.module', 'button_immediate_upgrade',
                [[module_id]])
            print("Upgrade command sent successfully!")
            
except Exception as e:
    print(f"Error: {e}")
