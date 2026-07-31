import paramiko
import sys

def run_ssh_command(host, port, username, password, command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, port=port, username=username, password=password)
        stdin, stdout, stderr = client.exec_command(command)
        out = stdout.read().decode()
        err = stderr.read().decode()
        if out:
            print(out)
        if err:
            print("ERROR:", err)
    except Exception as e:
        print("Exception:", str(e))
    finally:
        client.close()

if __name__ == '__main__':
    command = ' '.join(sys.argv[1:])
    run_ssh_command('nexas.havano.online', 9419, 'frappe', 'Farai@#', command)
