import json
import logging
from datetime import timedelta
from datetime import date, datetime as dt_class

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class WaChatbotSession(models.Model):
    _name = 'wa.chatbot.session'
    _description = 'Chatbot User Session'
    _order = 'last_activity_at desc'

    name = fields.Char(compute='_compute_name', store=True)
    chatbot_id = fields.Many2one(
        'wa.chatbot',
        required=True,
        ondelete='cascade',
        index=True,
    )
    account_id = fields.Many2one(
        'whatsapp.account',
        related='chatbot_id.account_id',
        store=True,
    )
    phone = fields.Char(required=True, index=True)
    partner_id = fields.Many2one('res.partner')
    state = fields.Selection(
        [
            ('active', 'Active'),
            ('paused', 'Paused'),
            ('handed_off', 'Handed Off'),
            ('closed', 'Closed'),
            ('expired', 'Expired'),
        ],
        default='active',
        index=True,
    )

    # Current position in the flow graph
    current_flow_id = fields.Many2one('wa.chatbot.flow')
    current_node_id = fields.Many2one('wa.chatbot.node')

    # Session data
    variables = fields.Text(
        default='{}',
        help="JSON dictionary of current session variable values.",
    )
    variables_pretty = fields.Text(
        string="Variables (formatted)",
        compute='_compute_variables_pretty',
        inverse='_inverse_variables_pretty',
    )
    flow_stack = fields.Text(
        default='[]',
        help="JSON array stack for GoTo returns: [{flow_id, node_id}, ...]",
    )
    fallback_count = fields.Integer(default=0, help="Consecutive fallback counter.")
    message_count = fields.Integer(default=0)

    # Timestamps
    started_at = fields.Datetime(default=fields.Datetime.now)
    last_activity_at = fields.Datetime(default=fields.Datetime.now, index=True)
    ended_at = fields.Datetime()

    # Handoff
    handoff_channel_id = fields.Many2one('discuss.channel', string="Discuss Channel")
    handoff_reason = fields.Char()

    # Logs
    log_ids = fields.One2many('wa.chatbot.session.log', 'session_id', string="Message Log")

    company_id = fields.Many2one(
        'res.company',
        related='chatbot_id.company_id',
        store=True,
    )

    # Note: Active session uniqueness is enforced in _create_session() by closing
    # stale sessions before creating new ones. An EXCLUDE constraint would require
    # the btree_gist extension which may not be available on all installations.

    # -------------------------------------------------------------------------
    # COMPUTE
    # -------------------------------------------------------------------------
    @api.depends('variables')
    def _compute_variables_pretty(self):
        for rec in self:
            try:
                data = json.loads(rec.variables or '{}')
                rec.variables_pretty = json.dumps(data, indent=4, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                rec.variables_pretty = rec.variables or '{}'

    def _inverse_variables_pretty(self):
        for rec in self:
            try:
                data = json.loads(rec.variables_pretty or '{}')
                rec.variables = json.dumps(data, ensure_ascii=False)
            except (json.JSONDecodeError, TypeError):
                pass

    @api.depends('chatbot_id.name', 'phone')
    def _compute_name(self):
        for rec in self:
            bot_name = rec.chatbot_id.name or 'Bot'
            rec.name = f"{bot_name} - {rec.phone or '?'}"

    # -------------------------------------------------------------------------
    # VARIABLE MANAGEMENT
    # -------------------------------------------------------------------------
    def get_variables(self):
        """Return session variables as a dict."""
        self.ensure_one()
        try:
            return json.loads(self.variables or '{}')
        except json.JSONDecodeError:
            return {}

    def set_variable(self, name, value):
        """Set a single session variable."""
        self.ensure_one()
        variables = self.get_variables()
        variables[name] = value
        self.variables = json.dumps(variables, ensure_ascii=False, default=self._json_safe_default)

    def set_variables(self, var_dict):
        """Merge a dict of variables into the session."""
        self.ensure_one()
        variables = self.get_variables()
        variables.update(var_dict)
        self.variables = json.dumps(variables, ensure_ascii=False, default=self._json_safe_default)

    @staticmethod
    def _json_safe_default(obj):
        """Fallback serializer for json.dumps — converts date/datetime and
        other non-serializable types to strings instead of raising TypeError."""
        if isinstance(obj, dt_class):
            return obj.isoformat(sep=' ', timespec='seconds')
        if isinstance(obj, date):
            return obj.isoformat()
        return str(obj)

    def get_variable(self, name, default=None):
        """Get a single variable value."""
        self.ensure_one()
        return self.get_variables().get(name, default)

    def clear_variables(self):
        """Reset all session variables."""
        self.ensure_one()
        self.variables = '{}'

    # -------------------------------------------------------------------------
    # FLOW STACK (for GoTo returns)
    # -------------------------------------------------------------------------
    def push_flow_stack(self, flow_id, node_id):
        """Push current position onto the stack before jumping to another flow."""
        self.ensure_one()
        try:
            stack = json.loads(self.flow_stack or '[]')
        except json.JSONDecodeError:
            stack = []
        stack.append({'flow_id': flow_id, 'node_id': node_id})
        self.flow_stack = json.dumps(stack)

    def pop_flow_stack(self):
        """Pop and return the previous position from the stack."""
        self.ensure_one()
        try:
            stack = json.loads(self.flow_stack or '[]')
        except json.JSONDecodeError:
            return None
        if not stack:
            return None
        entry = stack.pop()
        self.flow_stack = json.dumps(stack)
        return entry

    # -------------------------------------------------------------------------
    # LIFECYCLE
    # -------------------------------------------------------------------------
    def action_close(self):
        self.ensure_one()
        self.write({
            'state': 'closed',
            'ended_at': fields.Datetime.now(),
        })

    def action_resume(self):
        """Resume a paused or handed-off session."""
        self.ensure_one()
        if self.state in ('paused', 'handed_off'):
            self.write({
                'state': 'active',
                'last_activity_at': fields.Datetime.now(),
            })

    # -------------------------------------------------------------------------
    # CRON: Expire inactive sessions
    # -------------------------------------------------------------------------
    @api.model
    def _cron_expire_sessions(self):
        """Expire sessions that have been inactive beyond their chatbot's timeout."""
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
                    "Expired %d sessions for chatbot '%s'",
                    len(expired), chatbot.name,
                )
