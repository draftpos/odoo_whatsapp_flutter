import xmlrpc.client

url = 'https://demo1.havano.pro'
db = 'demo1_havano_pro_pknuzuhckrvwadhoboithcke'
username = 'admin'
password = 'admin'

try:
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})
    if not uid:
        print('Auth failed.')
    else:
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        msgs = models.execute_kw(db, uid, password,
            'mail.message', 'search_read',
            [[['model', '=', 'wa.chatbot.session']]], 
            {'fields': ['id', 'body', 'author_id', 'message_type', 'create_uid'], 'limit': 10, 'order': 'id desc'}
        )
        for m in msgs:
            print(f"ID: {m['id']}, Author: {m.get('author_id')}, Type: {m.get('message_type')}")
            print(f"Body: {m.get('body')}")
            print("---")
except Exception as e:
    print(f'Error: {e}')
