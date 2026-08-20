import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("161.97.114.200", username="root", password="Farai@#$1234")

cmd = "cat /home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/tk_customer_statements/report/customer_statement_report_pdf.xml"
stdin, stdout, stderr = ssh.exec_command(cmd)
print("OUT:")
print(stdout.read().decode())
print("ERR:")
print(stderr.read().decode())
