import os
"""
Fix script for WhatsApp chatbot "Talk to Human" session expiry bug.

PROBLEM:
  When a user selects "Talk to Human", the session enters 'handed_off' state.
  The cron _cron_expire_sessions() only expires 'active' sessions, NOT 'handed_off' ones.
  After the human agent finishes, the session remains 'handed_off' forever.
  All future messages from that phone number fall through (return False) to the 
  stock whatsapp handler since _try_handle_inbound checks for 'handed_off' state 
  and immediately returns False -- so the chatbot auto-messages never resume.

FIX (2 changes):
  1. wa_chatbot_session.py - _cron_expire_sessions():
     Also expire 'handed_off' sessions that have been inactive beyond timeout.
     
  2. chatbot_processor.py - _try_handle_inbound():
     When a 'handed_off' session is found but it has expired (last_activity_at
     beyond timeout), treat it as expired/closed so a new session starts.
     This provides immediate fix even before cron runs.
"""

import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = os.environ.get('SERVER_PASSWORD')
ssh.connect('161.97.114.200', username='root', password=pw)

BASE = '/home/demo1_havano_pro_pknuzuhckrvwadhoboithcke/custom-addons/dev_whatsapp_chatbot_ent/models'

# ============================================================
# FIX 1: wa_chatbot_session.py — expand cron to also expire handed_off sessions
# ============================================================
session_path = f'{BASE}/wa_chatbot_session.py'
stdin, stdout, stderr = ssh.exec_command(f'cat {session_path}')
session_content = stdout.read().decode('utf-8', errors='replace')

OLD_CRON = """    @api.model
    def _cron_expire_sessions(self):
        \"\"\"Expire sessions that have been inactive beyond their chatbot's timeout.\"\"\"
        chatbots = self.env['wa.chatbot'].search([('state', '=', 'active')])
        for chatbot in chatbots:
            timeout = chatbot.session_timeout or 30
            cutoff = fields.Datetime.now() - timedelta(minutes=timeout)
            expired = self.search([
                ('chatbot_id', '=', chatbot.id),
                ('state', '=', 'active'),
                ('last_activity_at', '<', cutoff),
            ])
            if expired:
                expired.write({
                    'state': 'expired',
                    'ended_at': fields.Datetime.now(),
                })
                _logger.info(
                    \"Expired %d sessions for chatbot '%s'\",
                    len(expired), chatbot.name,
                )"""

NEW_CRON = """    @api.model
    def _cron_expire_sessions(self):
        \"\"\"Expire sessions that have been inactive beyond their chatbot's timeout.

        'active' sessions that timeout become 'expired'.
        'handed_off' sessions that timeout also become 'expired' so the next
        message from the same phone number starts a fresh chatbot session
        instead of falling through to the human-agent channel forever.
        \"\"\"
        chatbots = self.env['wa.chatbot'].search([('state', '=', 'active')])
        for chatbot in chatbots:
            timeout = chatbot.session_timeout or 30
            cutoff = fields.Datetime.now() - timedelta(minutes=timeout)
            # Expire both active and handed_off sessions that have gone stale
            expired = self.search([
                ('chatbot_id', '=', chatbot.id),
                ('state', 'in', ('active', 'handed_off')),
                ('last_activity_at', '<', cutoff),
            ])
            if expired:
                expired.write({
                    'state': 'expired',
                    'ended_at': fields.Datetime.now(),
                })
                _logger.info(
                    \"Expired %d sessions for chatbot '%s'\",
                    len(expired), chatbot.name,
                )"""

if OLD_CRON in session_content:
    new_session_content = session_content.replace(OLD_CRON, NEW_CRON)
    print("FIX 1: Found cron section — patching wa_chatbot_session.py ...")
    # Backup original
    ssh.exec_command(f'cp {session_path} {session_path}.bak')
    # Write fixed version
    sftp = ssh.open_sftp()
    with sftp.open(session_path, 'w') as f:
        f.write(new_session_content)
    sftp.close()
    print("FIX 1: wa_chatbot_session.py patched successfully.")
else:
    print("FIX 1: WARNING - Could not find the exact cron text. Check manually.")
    print("Looking for:", repr(OLD_CRON[:100]))

# ============================================================
# FIX 2: chatbot_processor.py — handle timed-out handed_off sessions immediately
# ============================================================
processor_path = f'{BASE}/chatbot_processor.py'
stdin, stdout, stderr = ssh.exec_command(f'cat {processor_path}')
processor_content = stdout.read().decode('utf-8', errors='replace')

# Find the pre-scan block that checks for handed_off and returns False immediately
OLD_PRESCAN = """        for msg in messages:
            phone = self._normalize_phone(msg.get('from', ''))
            if not phone:
                continue
            handed_off = self.env['wa.chatbot.session'].sudo().search([
                ('chatbot_id', '=', chatbot.id),
                ('phone', '=', phone),
                ('state', '=', 'handed_off'),
            ], limit=1)
            if handed_off:
                return False"""

NEW_PRESCAN = """        for msg in messages:
            phone = self._normalize_phone(msg.get('from', ''))
            if not phone:
                continue
            handed_off = self.env['wa.chatbot.session'].sudo().search([
                ('chatbot_id', '=', chatbot.id),
                ('phone', '=', phone),
                ('state', '=', 'handed_off'),
            ], limit=1)
            if handed_off:
                # If the handed_off session has been inactive beyond the chatbot's
                # session timeout, expire it now and let the chatbot restart.
                # (The nightly cron also does this, but this handles the case where
                # the user messages before the cron fires.)
                timeout = chatbot.session_timeout or 30
                from datetime import timedelta
                cutoff = fields.Datetime.now() - timedelta(minutes=timeout)
                if handed_off.last_activity_at and handed_off.last_activity_at < cutoff:
                    handed_off.write({
                        'state': 'expired',
                        'ended_at': fields.Datetime.now(),
                    })
                    _logger.info(
                        \"Chatbot '%s': handed_off session %s for %s expired on inbound — restarting bot.\",
                        chatbot.name, handed_off.id, phone,
                    )
                    # Don't return False — fall through to normal chatbot processing
                    continue
                return False"""

if OLD_PRESCAN in processor_content:
    new_processor_content = processor_content.replace(OLD_PRESCAN, NEW_PRESCAN)
    print("\nFIX 2: Found pre-scan block — patching chatbot_processor.py ...")
    ssh.exec_command(f'cp {processor_path} {processor_path}.bak')
    sftp = ssh.open_sftp()
    with sftp.open(processor_path, 'w') as f:
        f.write(new_processor_content)
    sftp.close()
    print("FIX 2: chatbot_processor.py patched successfully.")
else:
    print("\nFIX 2: WARNING - Could not find the exact pre-scan block. Check manually.")
    print("Searching for partial match...")
    if "handed_off = self.env['wa.chatbot.session'].sudo().search" in processor_content:
        print("  -> Found the search block, but text doesn't match exactly. Manual edit needed.")

# Verify backups exist
stdin, stdout, stderr = ssh.exec_command(f'ls -la {BASE}/*.bak 2>/dev/null')
print("\nBackup files:", stdout.read().decode())

ssh.close()
print("\nDone. Restart Odoo docker to apply: docker-compose restart odoo")
