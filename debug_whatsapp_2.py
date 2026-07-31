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
        
        # Get fields for discuss.channel
        channel_fields = models.execute_kw(db, uid, password, 'discuss.channel', 'fields_get', [], {'attributes': ['string', 'type', 'relation']})
        
        wa_fields = {k: v for k, v in channel_fields.items() if 'wa' in k.lower() or 'whatsapp' in k.lower() or 'account' in k.lower()}
        print("WhatsApp fields in discuss.channel:", wa_fields)
        
        # Get whatsapp accounts
        accounts = models.execute_kw(db, uid, password, 'whatsapp.account', 'search_read', [], {'fields': ['id', 'name']})
        print("WhatsApp Accounts:", accounts)
        
except Exception as e:
    print(f"Error: {e}")
