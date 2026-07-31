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
        
        # Check product.product
        try:
            products = models.execute_kw(db, uid, password, 'product.product', 'search_read', [], {'limit': 1, 'fields': ['id', 'name', 'list_price']})
            print("Products available:", products)
        except Exception as e:
            print("Product model not available:", e)
        
except Exception as e:
    print(f"Error: {e}")
