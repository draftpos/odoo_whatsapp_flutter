import os
import sys
import paramiko

def run_ssh_script():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('nexas.havano.online', port=9419, username='frappe', password=os.environ.get('SERVER_PASSWORD'))
    
    commands = [
        "cd ~/frappe-bench/apps/havano_zim_payroll && git remote -v",
        "cd ~/frappe-bench/apps/havano_pos_integration && git remote -v"
    ]
    
    for cmd in commands:
        print(f"\\n--- Running: {cmd} ---")
        stdin, stdout, stderr = client.exec_command(cmd)
        print("STDOUT:", stdout.read().decode('utf-8'))
        print("STDERR:", stderr.read().decode('utf-8'))
        
    client.close()

if __name__ == "__main__":
    run_ssh_script()
