import os
import paramiko
import sys

host = "161.97.114.200"
password = "Farai@#$1234"
username = "root"

def run_ssh(cmd):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=username, password=password, timeout=15)
        
        # SFTP upload the changed files to bypass Github auth issues on the remote server
        print("Uploading changed files via SFTP...")
        sftp = client.open_sftp()
        
        base_remote = "/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/havano_schools_odoo"
        base_local = r"c:\odoo19\addons\havano_schools_odoo"
        
        files_to_upload = [
            "__manifest__.py",
            "models/__init__.py",
            "models/havano_admin_comment.py",
            "models/financial_report_override.py",
            "report/customer_statement_details_override.py",
            "views/customer_statement_report_override.xml",
            "views/havano_student_payment_views.xml",
            "report/fees_structure_balance_report_template.xml",
            "views/havano_partner_ledger_templates.xml",
            "views/res_partner_statement_report_template_override.xml",
            "report/custom_student_statement_report.xml",
            "report/custom_fees_structure_balance_report.xml",
            "views/havano_partner_ledger_action.xml",
            "views/fees_structure_balance_report_views.xml"
        ]
        
        for file in files_to_upload:
            local_path = os.path.join(base_local, file.replace('/', '\\'))
            remote_path = f"{base_remote}/{file}"
            print(f"Uploading {local_path} -> {remote_path}")
            sftp.put(local_path, remote_path)
            
        sftp.close()
        print("Upload complete!")

        # Execute upgrade and restart
        print("Executing upgrade and restart...")
        stdin, stdout, stderr = client.exec_command(cmd)
        upgrade_out = stdout.read().decode()
        upgrade_err = stderr.read().decode()
        print("UPGRADE STDOUT:")
        print(upgrade_out)
        print("UPGRADE STDERR:")
        print(upgrade_err)
        
        # Read line by line to show progress
        while True:
            line = stdout.readline()
            if not line:
                break
            print(line, end="")
            
        err = stderr.read().decode()
        if err:
            print("ERROR/WARNING:\n" + err)
    finally:
        client.close()

if __name__ == "__main__":
    cmd = '''
    CONTAINER="odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
    DB_NAME="demo1_havano_pro_pknuzuhckrvwadhoboithcke"
    
    echo "Upgrading havano_schools_odoo on DB: $DB_NAME"
    docker exec -u odoo $CONTAINER odoo -u havano_schools_odoo -d $DB_NAME -c /etc/odoo/odoo.conf --db_host=db --db_user=odoo --db_password=odoo --stop-after-init --http-port=8070 2>&1
    
    echo "Restarting Odoo container to flush cache..."
    docker restart $CONTAINER
    echo "Deployment completed successfully!"
    '''
    run_ssh(cmd)
