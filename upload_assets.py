import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

sftp = ssh.open_sftp()
local_xml = r'C:\odoo19\addons\whatsapp_web_chats\static\src\xml\chats_template.xml'
remote_xml = '/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/whatsapp_web_chats/static/src/xml/chats_template.xml'

local_js = r'C:\odoo19\addons\whatsapp_web_chats\static\src\js\chats.js'
remote_js = '/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/whatsapp_web_chats/static/src/js/chats.js'

sftp.put(local_xml, remote_xml)
sftp.put(local_js, remote_js)

sftp.close()
ssh.close()
print('Successfully uploaded chats_template.xml and chats.js to live server.')
