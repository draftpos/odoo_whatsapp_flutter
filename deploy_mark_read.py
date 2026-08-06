import os
import paramiko
import base64

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

# Read the file
cmd = "docker exec odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke cat /mnt/extra-addons/whatsapp_web_chats/models/whatsapp_account.py"
stdin, stdout, stderr = ssh.exec_command(cmd)
content = stdout.read().decode('utf-8')

# Add the new method
new_method = """
    @api.model
    def mark_whatsapp_web_messages_read(self, channel_id):
        channel = self.env['discuss.channel'].sudo().browse(int(channel_id))
        if channel.exists():
            channel.channel_seen()
            return True
        return False
"""
if 'mark_whatsapp_web_messages_read' not in content:
    content = content.replace("class WhatsappAccount(models.Model):", "class WhatsappAccount(models.Model):\n" + new_method)
    
    # Save back
    b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    cmd = f"echo {b64} | base64 -d > /tmp/whatsapp_account.py"
    ssh.exec_command(cmd)
    
    cmd = "docker cp /tmp/whatsapp_account.py odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke:/mnt/extra-addons/whatsapp_web_chats/models/whatsapp_account.py"
    ssh.exec_command(cmd)
    
    cmd = "docker restart odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
    ssh.exec_command(cmd)
    print("Restarted Odoo")
else:
    print("Method already exists")

ssh.close()
