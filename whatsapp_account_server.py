from odoo import models, fields, api

class WhatsAppAccount(models.Model):
    _inherit = 'whatsapp.account'

    image_1920 = fields.Image(string="Profile Picture", max_width=1920, max_height=1920)

    @api.model
    def get_whatsapp_web_channels(self, wa_account_id=None):
        domain = [('channel_type', '=', 'whatsapp')]
        if wa_account_id:
            domain.append(('wa_account_id', '=', int(wa_account_id)))
        
        # Use sudo() to bypass strict channel membership rules
        channels = self.env['discuss.channel'].sudo().search(domain, order='write_date desc')
        
        res = []
        for c in channels:
            res.append({
                'id': c.id,
                'name': c.name,
                'channel_type': c.channel_type,
                'whatsapp_partner_id': [c.whatsapp_partner_id.id, c.whatsapp_partner_id.display_name] if c.whatsapp_partner_id else False,
                'wa_account_id': [c.wa_account_id.id, c.wa_account_id.display_name] if c.wa_account_id else False,
                'message_needaction_counter': 0,
                'write_date': c.write_date,
                'whatsapp_number': c.whatsapp_number,
            })
        return res
        
    @api.model
    def get_whatsapp_web_messages(self, channel_id):
        messages = self.env['mail.message'].sudo().search([
            ('res_id', '=', int(channel_id)),
            ('model', '=', 'discuss.channel')
        ], limit=100, order='date asc')
        
        res = []
        for m in messages:
            res.append({
                'id': m.id,
                'body': m.body,
                'author_id': [m.author_id.id, m.author_id.display_name] if m.author_id else False,
                'date': m.date,
                'message_type': m.message_type,
                'attachment_ids': m.attachment_ids.ids,
            })
        return res

    def _process_messages(self, value):
        for message in value.get('messages', []):
            if message.get('type') == 'order':
                order = message.get('order', {})
                items = order.get('product_items', [])
                
                text_lines = ["🛒 *New Order Received!*"]
                if order.get('text'):
                    text_lines.append(f"Note: {order['text']}")
                text_lines.append("Items:")
                
                for item in items:
                    qty = item.get('quantity', 0)
                    price = item.get('item_price', '')
                    currency = item.get('currency', '')
                    product_id = item.get('product_retailer_id', 'Unknown Item')
                    
                    product = self.env['product.product'].sudo().search([
                        '|', ('default_code', '=', product_id), 
                        ('id', '=', int(product_id) if str(product_id).isdigit() else 0)
                    ], limit=1)
                    
                    product_name = product.name if product else product_id
                    text_lines.append(f"- {qty}x {product_name} ({currency} {price})")
                
                message['type'] = 'text'
                message['text'] = {'body': '\n'.join(text_lines)}
                
        return super()._process_messages(value)
