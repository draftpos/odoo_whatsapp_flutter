import xmlrpc.client

url = 'https://demo1.havano.pro'
db = 'demo1_havano_pro_pknuzuhckrvwadhoboithcke'
username = 'admin'
password = '123'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

# Try channel_seen
try:
    models.execute_kw(db, uid, password, 'discuss.channel', 'channel_seen', [[28]])
    print("channel_seen SUCCESS")
except Exception as e:
    print(f"channel_seen failed: {e}")

# Try channel_set_custom_info
try:
    models.execute_kw(db, uid, password, 'discuss.channel', 'channel_set_custom_info', [[28]])
    print("channel_set_custom_info SUCCESS")
except Exception as e:
    print(f"channel_set_custom_info failed: {e}")

# check if needaction goes down
channels = models.execute_kw(db, uid, password, 'whatsapp.account', 'get_whatsapp_web_channels', [])
for c in channels:
    if c['id'] == 28:
        print(f"Channel 28 unread count: {c.get('message_needaction_counter')}")
