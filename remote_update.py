import os
import paramiko
import sys

host = "161.97.114.200"
password = "***REMOVED***"
username = "root"

def run_ssh(cmd):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=username, password=password, timeout=15)
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode()
        err = stderr.read().decode()
        if out:
            print("OUTPUT:\n" + out)
        if err:
            print("ERROR:\n" + err)
    finally:
        client.close()

if __name__ == "__main__":
    cmd = '''
    CONTAINER="odoo_nadias_havano_pro_qpkucybbewofhnjdtyqxcyi"
    DB_NAME=$(docker exec psql_nadias_havano_pro_qpkucybbewofhnjdtyqxcyi psql -U odoo -lqt | cut -d \| -f 1 | grep -v 'postgres\|template\|None' | awk '{$1=$1};1' | head -n 1)
    
    echo "Upgrading on DB: $DB_NAME"
    docker exec -u odoo $CONTAINER odoo -u havano_schools_odoo -d $DB_NAME -c /etc/odoo/odoo.conf --db_host=db --db_user=odoo --db_password=odoo --stop-after-init --http-port=8070
    
    echo "Restarting Odoo container to flush cache..."
    docker restart $CONTAINER
    '''
    run_ssh(cmd)
