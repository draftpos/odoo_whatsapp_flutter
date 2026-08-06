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
        exit_status = stdout.channel.recv_exit_status()
        out = stdout.read().decode()
        err = stderr.read().decode()
        print(f"EXIT STATUS: {exit_status}")
        if out:
            print("OUTPUT:\n" + out)
        if err:
            print("ERROR:\n" + err)
    finally:
        client.close()

if __name__ == "__main__":
    cmd = '''
    CONTAINER="odoo_nadias_havano_pro_qpkucybbewofhnjdtyqxcyi"
    DB_NAME="nadias_havano_pro_qpkucybbewofhnjdtyqxcyi"
    
    cat << 'EOF' > /tmp/check_teacher.py
import sys

admin_group_xml_id = 'havano_schools_odoo.group_havano_admin'
teacher_group_xml_id = 'havano_schools_odoo.group_havano_teacher'

all_users = env['res.users'].search([])
print("Checking all users...")

found_teachers = 0
for user in all_users:
    if user.has_group(teacher_group_xml_id):
        found_teachers += 1
        is_admin = user.has_group(admin_group_xml_id)
        
        print(f"\\n--- Checking Teacher: {user.name} (ID: {user.id}) | Admin: {is_admin} ---")
        faculty = env['havano.faculty'].search([('user_id', '=', user.id)], limit=1)
        if faculty:
            print(f"Faculty: {faculty.name} | Allow All Data: {faculty.allow_all_data_access}")
            assignments = env['havano.faculty.assignment'].search([('faculty_id.user_id', '=', user.id)])
            print(f"Assignments count: {len(assignments)}")
            
            if not is_admin:
                env_user = env(user=user)
                try:
                    students = env_user['havano.student'].search([])
                    print(f"Students visible to this teacher: {len(students)}")
                    total_students = env['havano.student'].search_count([])
                    print(f"Total students in system: {total_students}")
                except Exception as e:
                    print(f"Error searching students: {e}")
            else:
                print("Skipping student search because user is an Admin (sees everything).")
        else:
            print("No linked faculty record.")

if found_teachers == 0:
    print("NO TEACHERS FOUND!")

env.cr.rollback()
EOF
    
    docker exec -i -u odoo $CONTAINER odoo shell -d $DB_NAME -c /etc/odoo/odoo.conf --db_host=db --db_user=odoo --db_password=odoo --no-http < /tmp/check_teacher.py
    '''
    run_ssh(cmd)
