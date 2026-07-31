from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_lead = fields.Boolean(string="Is Lead", default=False)
