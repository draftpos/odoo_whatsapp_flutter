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
        
        channel_fields = models.execute_kw(db, uid, password, 'discuss.channel', 'fields_get', [], {'attributes': ['string', 'type']})
        
        unread_fields = {k: v for k, v in channel_fields.items() if 'unread' in k.lower() or 'count' in k.lower() or 'message' in k.lower()}
        print("Fields related to unread/messages in discuss.channel:", unread_fields)
        
except Exception as e:
    print(f"Error: {e}")
