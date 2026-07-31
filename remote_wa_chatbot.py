# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################
import json
import logging
import re
from datetime import timedelta
import pytz
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

# Default keywords that trigger built-in behaviors
DEFAULT_GLOBAL_KEYWORDS = [
    {'keyword': 'menu', 'match_type': 'exact', 'is_global': True, 'reset_session': True},
    {'keyword': 'start', 'match_type': 'exact', 'is_global': True, 'reset_session': True},
    {'keyword': 'agent', 'match_type': 'exact', 'is_global': True},
    {'keyword': 'human', 'match_type': 'exact', 'is_global': True},
]
# Note: 'stop' / 'unsubscribe' are intentionally NOT listed — the enterprise
# whatsapp.message.create() hook blacklists those numbers automatically, and
# we must not intercept them.


class WaChatbot(models.Model):
    _name = 'wa.chatbot'
    _description = 'WhatsApp Chatbot'
    _inherit = ['mail.thread']
    _order = 'name'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------
    name = fields.Char(required=True, tracking=True)
    account_id = fields.Many2one(
        'whatsapp.account',
        required=True,
        string="WhatsApp Account",
        ondelete='cascade',
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('paused', 'Paused'),
            ('archived', 'Archived'),
        ],
        default='draft',
        tracking=True,
    )
    description = fields.Text()

    # Flows
    default_flow_id = fields.Many2one(
        'wa.chatbot.flow',
        string="Default Flow",
        domain="[('chatbot_id', '=', id)]",
    )
    flow_ids = fields.One2many('wa.chatbot.flow', 'chatbot_id', string="Flows")

    # Keywords
    keyword_ids = fields.One2many('wa.chatbot.keyword', 'chatbot_id', string="Keywords")

    # Messages
    welcome_message = fields.Text(
        string="Welcome Message",
        help="Sent when bot first engages with a new user. Leave empty to jump directly into the default flow.",
    )
    fallback_message = fields.Text(
        default="Sorry, I didn't understand that. Could you try again?",
        string="Fallback Message",
    )
    fallback_max_retries = fields.Integer(
        default=2,
        string="Max Fallback Retries",
        help="After this many consecutive fallbacks, hand off to a human agent.",
    )

    # Session
    session_timeout = fields.Integer(
        default=30,
        string="Session Timeout (min)",
        help="Minutes of inactivity before the session is reset.",
    )

    # Working Hours
    working_hours_only = fields.Boolean(
        string="Active Only During Working Hours",
    )
    working_hour_start = fields.Float(default=9.0, string="Start Hour")
    working_hour_end = fields.Float(default=18.0, string="End Hour")
    working_hour_timezone = fields.Selection(
        '_tz_get',
        string="Timezone",
        default='UTC',
    )
    outside_hours_message = fields.Text(
        default="We're currently outside working hours. We'll get back to you soon!",
        string="Outside Hours Message",
    )

    # Handoff
    handoff_message = fields.Text(
        default="I'm connecting you with a human agent. Please hold on...",
        string="Handoff Message",
    )
    user_id = fields.Many2one(
        'res.users',
        string="Handoff User",
        help="User responsible for handling handoff conversations. "
             "Auto-set from the WhatsApp account's first notify user, but can be overridden.",
    )

    # Stats (computed)
    active_session_count = fields.Integer(
        compute='_compute_session_stats',
        string="Active Sessions",
    )
    total_sessions = fields.Integer(
        compute='_compute_session_stats',
        string="Total Sessions",
    )
    total_messages = fields.Integer(
        compute='_compute_message_stats',
        string="Total Messages",
    )
    flow_count = fields.Integer(compute='_compute_flow_count', string="Flows")

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        help="Company owning this chatbot. Enterprise whatsapp.account exposes "
             "allowed_company_ids (multi); keep this as a standalone default.",
    )
    active = fields.Boolean(default=True)

    @api.model
    def _tz_get(self):
        return [(tz, tz) for tz in sorted(pytz.all_timezones_set)]

    @api.onchange('account_id')
    def _onchange_account_id(self):
        if self.account_id and self.account_id.notify_user_ids:
            self.user_id = self.account_id.notify_user_ids[:1]

    # -------------------------------------------------------------------------
    # COMPUTE
    # -------------------------------------------------------------------------
    def _compute_session_stats(self):
        Session = self.env['wa.chatbot.session']
        for rec in self:
            rec.active_session_count = Session.search_count([
                ('chatbot_id', '=', rec.id),
                ('state', '=', 'active'),
            ])
            rec.total_sessions = Session.search_count([
                ('chatbot_id', '=', rec.id),
            ])

    def _compute_message_stats(self):
        WaMessage = self.env['whatsapp.message']
        for rec in self:
            rec.total_messages = WaMessage.search_count([
                ('is_bot_message', '=', True),
                ('chatbot_session_id.chatbot_id', '=', rec.id),
            ])

    def _compute_flow_count(self):
        for rec in self:
            rec.flow_count = len(rec.flow_ids)

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    def action_activate(self):
        self.ensure_one()
        if not self.default_flow_id:
            raise UserError(_("Please set a default flow before activating the chatbot."))
        if not self.default_flow_id.node_ids.filtered(lambda n: n.is_entry):
            raise UserError(_("The default flow must have a Start node."))
        if self.default_flow_id.state != 'published':
            raise UserError(_("The default flow must be published before activating the chatbot."))
        self.state = 'active'

    def action_pause(self):
        self.ensure_one()
        self.state = 'paused'

    def action_archive_bot(self):
        self.ensure_one()
        # Close all active sessions
        self.env['wa.chatbot.session'].search([
            ('chatbot_id', '=', self.id),
            ('state', 'in', ('active', 'paused')),
        ]).write({'state': 'closed', 'ended_at': fields.Datetime.now()})
        self.state = 'archived'

    def action_reset_draft(self):
        self.ensure_one()
        self.state = 'draft'

    def action_view_flows(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Flows"),
            'res_model': 'wa.chatbot.flow',
            'view_mode': 'list,form',
            'domain': [('chatbot_id', '=', self.id)],
            'context': {'default_chatbot_id': self.id},
        }

    def action_view_sessions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Sessions"),
            'res_model': 'wa.chatbot.session',
            'view_mode': 'list,form',
            'domain': [('chatbot_id', '=', self.id)],
        }

    @api.model
    def get_dashboard_data(self, chatbot_id=None, days=30):
        """Return live dashboard statistics computed directly from sessions.

        Works without the analytics cron — queries session records directly.
        """
        Session = self.env['wa.chatbot.session']
        Log = self.env['wa.chatbot.session.log']

        date_from = fields.Datetime.now() - timedelta(days=days)
        domain = [('started_at', '>=', date_from)]
        if chatbot_id:
            domain.append(('chatbot_id', '=', chatbot_id))

        sessions = Session.search(domain)

        total = len(sessions)
        active = len(sessions.filtered(lambda s: s.state == 'active'))
        completed = len(sessions.filtered(lambda s: s.state == 'closed'))
        handed_off = len(sessions.filtered(lambda s: s.state == 'handed_off'))
        expired = len(sessions.filtered(lambda s: s.state == 'expired'))

        # Message counts from session logs
        log_domain = [('session_id', 'in', sessions.ids)]
        logs = Log.search(log_domain)
        msgs_sent = len(logs.filtered(lambda l: l.direction == 'outbound'))
        msgs_received = len(logs.filtered(lambda l: l.direction == 'inbound'))

        # Average duration
        durations = []
        for s in sessions.filtered(lambda s: s.ended_at and s.started_at):
            delta = (s.ended_at - s.started_at).total_seconds() / 60.0
            durations.append(delta)
        avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

        # Per-chatbot breakdown
        chatbot_stats = []
        chatbot_ids = sessions.mapped('chatbot_id')
        for bot in chatbot_ids:
            bot_sessions = sessions.filtered(lambda s: s.chatbot_id == bot)
            bot_active = len(bot_sessions.filtered(lambda s: s.state == 'active'))
            bot_total = len(bot_sessions)
            chatbot_stats.append({
                'id': bot.id,
                'name': bot.name,
                'total': bot_total,
                'active': bot_active,
                'completed': len(bot_sessions.filtered(lambda s: s.state == 'closed')),
                'handed_off': len(bot_sessions.filtered(lambda s: s.state == 'handed_off')),
            })

        return {
            'total_sessions': total,
            'active_sessions': active,
            'completed_sessions': completed,
            'handed_off_sessions': handed_off,
            'expired_sessions': expired,
            'messages_sent': msgs_sent,
            'messages_received': msgs_received,
            'avg_duration': avg_duration,
            'completion_rate': round((completed / total) * 100) if total > 0 else 0,
            'handoff_rate': round((handed_off / total) * 100) if total > 0 else 0,
            'chatbot_stats': chatbot_stats,
        }

    # -------------------------------------------------------------------------
    # WORKING HOURS CHECK
    # -------------------------------------------------------------------------
    def _is_within_working_hours(self):
        """Check if current time is within configured working hours."""
        self.ensure_one()
        if not self.working_hours_only:
            return True
        try:
            tz = pytz.timezone(self.working_hour_timezone or 'UTC')
            now = fields.Datetime.now().astimezone(tz) if hasattr(fields.Datetime.now(), 'astimezone') else fields.Datetime.context_timestamp(self, fields.Datetime.now())
            current_hour = now.hour + now.minute / 60.0
            return self.working_hour_start <= current_hour < self.working_hour_end
        except Exception:
            return True
