import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = '***REMOVED***'
ssh.connect('161.97.114.200', username='root', password=pw)

CONTAINER = 'odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke'
COMPOSE_DIR = '/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke'

print("Restarting Odoo container...")
stdin, stdout, stderr = ssh.exec_command(f'cd {COMPOSE_DIR} && docker compose restart web 2>&1')
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print(out or err or "(no output)")

# Wait a few seconds and check status
time.sleep(5)
stdin, stdout, stderr = ssh.exec_command(f'docker ps --filter name={CONTAINER} --format "table {{{{.Names}}}}\t{{{{.Status}}}}"')
print("\nContainer status after restart:")
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
