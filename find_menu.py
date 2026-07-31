import xmlrpc.client

url = 'https://demo1.havano.pro'
db = 'demo1_havano_pro_pknuzuhckrvwadhoboithcke'
username = 'admin'
password = 'admin'

try:
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})
    if uid:
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        
        ext_ids = models.execute_kw(db, uid, password,
            'ir.model.data', 'search_read',
            [[['model', '=', 'ir.ui.menu'], ['res_id', '=', 505]]],
            {'fields': ['module', 'name']})
        print("WhatsApp Menu External IDs:", ext_ids)
            
except Exception as e:
    print(f"Error: {e}")
