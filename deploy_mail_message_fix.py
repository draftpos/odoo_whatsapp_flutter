import paramiko
import base64

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
pw = '***REMOVED***'
ssh.connect('161.97.114.200', username='root', password=pw)

new_code = """from odoo import models, api

class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        
        for rec in records:
            if rec.model == 'wa.chatbot.session' and rec.res_id:
                try:
                    import logging
                    _logger = logging.getLogger(__name__)
                    
                    session = self.env['wa.chatbot.session'].sudo().browse(rec.res_id)
                    if session.exists():
                        account = session.chatbot_id.account_id
                        phone = session.phone
                        partner = session.partner_id
                        
                        _logger.error("DEBUG: Found session for phone %s, account %s", phone, account.id)
                        
                        Channel = self.env['discuss.channel'].sudo()
                        channel = Channel.search([
                            ('channel_type', '=', 'whatsapp'),
                            ('wa_account_id', '=', account.id),
                            ('whatsapp_number', '=', phone),
                        ], limit=1)
                        
                        _logger.error("DEBUG: Searched for channel, found: %s", channel.id if channel else False)
                        
                        if not channel and hasattr(Channel, '_get_whatsapp_channel'):
                            _logger.error("DEBUG: Calling _get_whatsapp_channel...")
                            channel = Channel._get_whatsapp_channel(
                                whatsapp_number=phone,
                                wa_account_id=account,
                                sender_name=partner.name if partner else phone,
                                create_if_not_found=True,
                                related_message=False,
                            )
                            _logger.error("DEBUG: Created/Found channel: %s", channel.id if channel else False)
                            
                        if channel:
                            direction = self.env.context.get('wa_direction')
                            body_html = rec.body or ''
                            
                            if direction == 'inbound':
                                new_author_id = partner.id if partner else False
                            elif direction == 'outbound':
                                new_author_id = self.env.ref('base.partner_root').id
                            else:
                                # Fallback if context is missing
                                new_author_id = rec.author_id.id

                            # Duplicate the message into the discuss.channel so operators can see it
                            rec.sudo().copy({
                                'model': 'discuss.channel',
                                'res_id': channel.id,
                                'message_type': 'whatsapp_message',
                                'author_id': new_author_id,
                                'body': body_html,
                            })
                            _logger.error("DEBUG: Message copied successfully!")
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error("DEBUG: Failed to mirror chatbot msg to discuss.channel: %s", e)

        return records
"""

b64 = base64.b64encode(new_code.encode('utf-8')).decode('utf-8')
cmd = f"echo {b64} | base64 -d > /tmp/mail_message.py"
ssh.exec_command(cmd)

cmd = "docker cp /tmp/mail_message.py odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke:/mnt/extra-addons/whatsapp_web_chats/models/mail_message.py"
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())

cmd = "docker restart odoo_demo1_havano_pro_pknuzuhckrvwadhoboithcke"
stdin, stdout, stderr = ssh.exec_command(cmd)
print("RESTARTED ODOO")
print(stdout.read().decode())
print(stderr.read().decode())

ssh.close()
