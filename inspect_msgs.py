import xmlrpc.client

url = 'http://localhost:8069'
db = 'havano_db'
username = 'admin'
password = 'admin' # Assuming standard local dev password, or I can check odoo.conf

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
msgs = models.execute_kw(db, uid, password, 'mail.message', 'search_read',
    [[['message_type', '=', 'whatsapp_message']]],
    {'fields': ['id', 'body', 'model', 'res_id', 'message_type'], 'limit': 10}
)
for m in msgs:
    print(m)
