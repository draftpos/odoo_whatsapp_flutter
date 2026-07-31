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
        
        # Check whatsapp.account fields
        account_fields = models.execute_kw(db, uid, password, 'whatsapp.account', 'fields_get', [], {'attributes': ['string', 'type']})
        image_fields = {k: v for k, v in account_fields.items() if 'image' in k.lower() or 'avatar' in k.lower() or 'pic' in k.lower()}
        print("WhatsApp Account Image fields:", image_fields)
        
        # Check res.partner image fields
        partner_fields = models.execute_kw(db, uid, password, 'res.partner', 'fields_get', [], {'attributes': ['string', 'type']})
        p_image_fields = {k: v for k, v in partner_fields.items() if 'image' in k.lower() or 'avatar' in k.lower()}
        print("Partner Image fields:", list(p_image_fields.keys()))
        
except Exception as e:
    print(f"Error: {e}")
