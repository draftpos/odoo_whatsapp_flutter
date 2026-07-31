import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('161.97.114.200', username='root', password='***REMOVED***', timeout=10)

cmd = """python3 -c "
import xmlrpc.client
url = 'http://localhost:8069'
db = 'havano_pro_pknuzuhckrvwadhoboithcke'
username = 'admin'
password = 'admin'
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
msgs = models.execute_kw(db, uid, password, 'mail.message', 'search_read', [[['message_type', '=', 'whatsapp_message']]], {'limit': 5, 'fields': ['model', 'res_id', 'body', 'message_type'], 'order': 'id desc'})
print(msgs)
" """
stdin, stdout, stderr = ssh.exec_command(cmd)
print('STDOUT:', stdout.read().decode())
print('STDERR:', stderr.read().decode())
ssh.close()
