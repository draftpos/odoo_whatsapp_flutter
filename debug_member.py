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
        
        member_fields = models.execute_kw(db, uid, password, 'discuss.channel.member', 'fields_get', [], {'attributes': ['string', 'type']})
        
        print("Member fields:", {k: v for k, v in member_fields.items() if 'unread' in k.lower() or 'message' in k.lower() or 'count' in k.lower()})
        
except Exception as e:
    print(f"Error: {e}")
