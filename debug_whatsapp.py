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
        
        # 1. Get admin's partner_id
        admin = models.execute_kw(db, uid, password, 'res.users', 'read', [[uid]], {'fields': ['partner_id']})
        print("Admin user:", admin)
        
        # 2. Get recent messages in a whatsapp channel
        channels = models.execute_kw(db, uid, password, 'discuss.channel', 'search_read', [[['channel_type', '=', 'whatsapp']]], {'limit': 1, 'fields': ['id', 'name']})
        print("Channel:", channels)
        
        if channels:
            msgs = models.execute_kw(db, uid, password, 'mail.message', 'search_read', 
                [[['res_id', '=', channels[0]['id']], ['model', '=', 'discuss.channel']]], 
                {'limit': 5, 'fields': ['id', 'author_id', 'body', 'message_type']})
            print("Messages:", msgs)
            
        # 3. Find WhatsApp account models
        wa_models = models.execute_kw(db, uid, password, 'ir.model', 'search_read', [[['model', 'ilike', 'whatsapp']]], {'fields': ['model', 'name']})
        print("WhatsApp Models:", wa_models)

except Exception as e:
    print(f"Error: {e}")
