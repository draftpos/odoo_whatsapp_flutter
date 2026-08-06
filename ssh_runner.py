import os
import sys
import paramiko

def run_ssh_command(cmd):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect('nexas.havano.online', port=9419, username='frappe', password=os.environ.get('SERVER_PASSWORD'))
        # Load environment for bash if needed, or run from frappe-bench
        command = f"cd ~/frappe-bench && {cmd}"
        stdin, stdout, stderr = client.exec_command(command)
        
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        
        if out:
            print(out)
        if err:
            print("ERROR:")
            print(err)
    except Exception as e:
        print("EXCEPTION:", e)
    finally:
        client.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        run_ssh_command(cmd)
