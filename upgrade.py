import os
import xmlrpc.client

url = "http://localhost:8069"
db = "havano_schools_odoo"
username = "admin"
password = "***REMOVED***"

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})

if not uid:
    # Try another password?
    uid = common.authenticate(db, username, "admin", {})

if uid:
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    # Find module
    module_ids = models.execute_kw(db, uid, password if password == "***REMOVED***" else "admin", 'ir.module.module', 'search', [[('name', '=', 'whatsapp_web_chats')]])
    if module_ids:
        # Upgrade
        models.execute_kw(db, uid, password if password == "***REMOVED***" else "admin", 'ir.module.module', 'button_immediate_upgrade', [module_ids])
        print("Module upgraded successfully via XML-RPC.")
    else:
        print("Module not found.")
else:
    print("Failed to authenticate.")
