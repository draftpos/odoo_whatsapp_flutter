import xmlrpc.client

url = 'https://demo1.havano.pro'
db = 'demo1_havano_pro_pknuzuhckrvwadhoboithcke'
username = 'admin'
password = '123'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
if not uid:
    print("Authentication failed")
    exit()

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

channels = models.execute_kw(db, uid, password, 'whatsapp.account', 'get_whatsapp_web_channels', [])
print(f"Channels: {len(channels)}")

if channels:
    for c in channels:
        if c.get('message_needaction_counter', 0) > 0 or c['id'] == 28:
            print(f"Channel: {c['name']} (ID: {c['id']}), Unread: {c.get('message_needaction_counter')}")
            messages = models.execute_kw(db, uid, password, 'whatsapp.account', 'get_whatsapp_web_messages', [c['id']])
            print(f"  Messages count: {len(messages)}")
            for m in messages[-2:]:
                print(f"    - {m['body'][:50]}")
            break
