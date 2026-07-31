import paramiko
import os
import sys

host = '161.97.114.200'
port = 22
username = 'root'
password = '***REMOVED***'

local_path = r'C:\odoo19\addons\whatsapp_web_chats'
remote_path = '/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/whatsapp_web_chats'

def create_remote_dir(sftp, remote_dir):
    dirs = remote_dir.split('/')
    path = ''
    for dir in dirs:
        if not dir:
            continue
        path += f'/{dir}'
        try:
            sftp.stat(path)
        except FileNotFoundError:
            sftp.mkdir(path)

def upload_dir(sftp, local_dir, remote_dir):
    create_remote_dir(sftp, remote_dir)
    for item in os.listdir(local_dir):
        l_path = os.path.join(local_dir, item)
        r_path = f"{remote_dir}/{item}"
        if os.path.isdir(l_path):
            upload_dir(sftp, l_path, r_path)
        else:
            sftp.put(l_path, r_path)
            print(f"Uploaded {l_path} to {r_path}")

def deploy():
    print("Connecting via SSH...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username=username, password=password)
        print("Connected! Opening SFTP session...")
        sftp = client.open_sftp()
        
        print("Uploading directory...")
        upload_dir(sftp, local_path, remote_path)
        
        print("Upload complete. Restarting Odoo might be required.")
        sftp.close()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == '__main__':
    deploy()
