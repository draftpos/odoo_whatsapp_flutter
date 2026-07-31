import paramiko
import os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = '***REMOVED***'
ssh.connect('161.97.114.200', username='root', password=pw)

sftp = ssh.open_sftp()
local_path = r'C:\odoo19\addons\whatsapp_web_chats\static\src\xml\chats_template.xml'
remote_path = '/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/whatsapp_web_chats/static/src/xml/chats_template.xml'

sftp.put(local_path, remote_path)
sftp.close()
ssh.close()
print('Successfully uploaded chats_template.xml to live server.')
