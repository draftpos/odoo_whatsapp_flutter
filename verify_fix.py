import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = '***REMOVED***'
ssh.connect('161.97.114.200', username='root', password=pw)

BASE = '/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/dev_whatsapp_chatbot_ent/models'

# Verify session fix
print("=== VERIFYING wa_chatbot_session.py fix ===")
stdin, stdout, stderr = ssh.exec_command(f"grep -n 'handed_off\\|in.*active.*handed_off\\|Also expire' {BASE}/wa_chatbot_session.py")
print(stdout.read().decode('utf-8', errors='replace'))

# Verify processor fix
print("\n=== VERIFYING chatbot_processor.py fix ===")
stdin, stdout, stderr = ssh.exec_command(f"grep -n 'handed_off.*expired\\|expire it now\\|restarting bot' {BASE}/chatbot_processor.py")
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
