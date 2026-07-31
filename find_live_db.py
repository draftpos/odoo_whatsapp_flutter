import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = '***REMOVED***'
ssh.connect('161.97.114.200', username='root', password=pw)

CONTAINER = 'odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke'

# Check the databases available
cmd = f'docker exec -i {CONTAINER} psql -U odoo -h db -lqt | cut -d \\| -f 1'
print("Databases:")
stdin, stdout, stderr = ssh.exec_command(cmd)
dbs = stdout.read().decode('utf-8').strip().split('\n')
for db in dbs:
    db = db.strip()
    if db and not db.startswith('template') and db != 'postgres':
        print(f"Found DB: {db}")

ssh.close()
