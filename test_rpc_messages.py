import xmlrpc.client

url = 'http://161.97.114.200:8019'
db = 'demo1_havano_pro_pknuzuhckrvwadhoboithcke'
username = 'admin'
password = '123'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
print("UID:", uid)

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

messages = models.execute_kw(db, uid, password,
    'whatsapp.account', 'get_whatsapp_web_messages',
    [28]) # channel id 28

print(f"Messages count: {len(messages)}")
for msg in messages[-5:]:
    print(msg)
