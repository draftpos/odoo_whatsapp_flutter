import sys
import paramiko

def run_ssh_script():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('nexas.havano.online', port=9419, username='frappe', password='***REMOVED***')
    
    html_content = """<style>
	.print-format table, .print-format tr, 
	.print-format td, .print-format div, .print-format p {
		font-family: "Helvetica Neue", Helvetica, Arial, "Open Sans", sans-serif;
	}
	.payslip-header {
		text-align: center;
		margin-bottom: 30px;
	}
	.payslip-title {
		font-size: 24px;
		font-weight: bold;
		text-transform: uppercase;
		margin-bottom: 5px;
	}
	.summary-table {
		width: 100%;
		border-collapse: collapse;
		margin-top: 20px;
	}
	.summary-table th {
		background-color: #f8f9fa;
		border: 1px solid #d1d8dd;
		padding: 10px;
		text-align: left;
		font-weight: 600;
	}
	.summary-table th.text-right {
		text-align: right;
	}
	.summary-table td {
		border: 1px solid #d1d8dd;
		padding: 8px 10px;
	}
	.summary-table td.text-right {
		text-align: right;
	}
	.total-row td {
		font-weight: bold;
		background-color: #f4f5f6;
	}
</style>

<div class="payslip-header">
	<div class="payslip-title">Combined Payroll Summary</div>
	{% if (filters && filters.payroll_period) { %}
	<p>For the month of {%= filters.payroll_period %}</p>
	{% } %}
</div>

<table class="summary-table">
	<thead>
		<tr>
			<th style="width: 35%;">Earnings Component</th>
			<th class="text-right" style="width: 15%;">Amount (USD)</th>
			<th style="width: 35%;">Deduction Component</th>
			<th class="text-right" style="width: 15%;">Amount (USD)</th>
		</tr>
	</thead>
	<tbody>
		{% for (var i=0, l=data.length; i<l; i++) { 
			var row = data[i]; 
			var is_total = (row.earnings == "Total Earnings" || row.earnings == "Net Balance");
		%}
			<tr {% if (is_total) { %}class="total-row"{% } %}>
				<td>{%= row.earnings || "" %}</td>
				<td class="text-right">
					{% if (row.earnings_amount_usd != null) { %}
						{%= frappe.format(row.earnings_amount_usd, {"fieldtype": "Currency"}) %}
					{% } %}
				</td>
				<td>{%= row.deductions || "" %}</td>
				<td class="text-right">
					{% if (row.deductions_amount_usd != null) { %}
						{%= frappe.format(row.deductions_amount_usd, {"fieldtype": "Currency"}) %}
					{% } %}
				</td>
			</tr>
		{% } %}
	</tbody>
</table>"""

    script = f"""
import os

html_content = '''{html_content}'''

paths = [
    'apps/havano_zim_payroll/havano_zim_payroll/havano_zim_payroll/report/payroll_summary/payroll_summary.html',
    'apps/havano_pos_integration/havano_pos_integration/havano_pos_integration/report/payroll_summary/payroll_summary.html'
]

for path in paths:
    if os.path.exists(path):
        with open(path, 'w') as f:
            f.write(html_content)
        print("Updated", path)
"""
    
    command = f'''cat << 'EOF' > ~/frappe-bench/fix_html2.py
{script}
EOF
cd ~/frappe-bench && python3 fix_html2.py
'''
    stdin, stdout, stderr = client.exec_command(command)
    
    print("STDOUT:", stdout.read().decode('utf-8'))
    print("STDERR:", stderr.read().decode('utf-8'))
    client.close()

if __name__ == "__main__":
    run_ssh_script()
