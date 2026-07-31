# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################
import ast
import json
import logging
import re as re_module
import time
import requests as req_lib
from datetime import datetime
from markupsafe import Markup, escape

from odoo import api, fields, models, _

from odoo.addons.dev_whatsapp_chatbot_ent.tools import send_helpers

_logger = logging.getLogger(__name__)

# Recursion guard — caps how deep auto-advancing nodes can chain per inbound.
MAX_EXECUTION_DEPTH = 50

# Date format → regex for dynamic date validation
DATE_FORMAT_PATTERNS = {
    'DD-MM-YYYY': r'^\d{2}-\d{2}-\d{4}$',
    'MM-DD-YYYY': r'^\d{2}-\d{2}-\d{4}$',
    'YYYY-MM-DD': r'^\d{4}-\d{2}-\d{2}$',
    'DD/MM/YYYY': r'^\d{2}/\d{2}/\d{4}$',
    'MM/DD/YYYY': r'^\d{2}/\d{2}/\d{4}$',
    'YYYY/MM/DD': r'^\d{4}/\d{2}/\d{2}$',
}

# Date format → strptime format
DATE_FORMAT_STRPTIME = {
    'DD-MM-YYYY': '%d-%m-%Y',
    'MM-DD-YYYY': '%m-%d-%Y',
    'YYYY-MM-DD': '%Y-%m-%d',
    'DD/MM/YYYY': '%d/%m/%Y',
    'MM/DD/YYYY': '%m/%d/%Y',
    'YYYY/MM/DD': '%Y/%m/%d',
}

# Message types this processor accepts on inbound logging
_LOGGABLE_INBOUND_TYPES = ('text', 'image', 'video', 'audio', 'document', 'location', 'interactive')


class WaChatbotProcessor(models.TransientModel):
    _name = 'wa.chatbot.processor'
    _description = 'WhatsApp Chatbot FSM Processor'

    # =========================================================================
    # ENTRY POINT
    # =========================================================================

    @api.model
    def _try_handle_inbound(self, account, value):
        """
        Called from whatsapp.account._process_messages override.

        Returns True  → chatbot consumed the payload; stock must NOT re-process.
        Returns False → stock should run normally (no chatbot, or handed-off
                        session, or processor error).
        """
        messages = (value or {}).get('messages') or []
        if not messages:
            return False

        chatbot = self._find_active_chatbot(account, messages)
        if not chatbot:
            return False

        contacts = (value or {}).get('contacts') or []
        
        profile_name = ''
        if contacts:
            profile_name = contacts[0].get('profile', {}).get('name', '') or ''
       
        # Pre-scan: if ANY message belongs to a handed-off session, fall through
        # to stock so the human agent sees the message in Discuss. Webhooks
        # typically deliver one message at a time, so this is an all-or-nothing
        # decision per batch.
        for msg in messages:
            phone = self._normalize_phone(msg.get('from', ''))
            if not phone:
                continue
            handed_off = self.env['wa.chatbot.session'].sudo().search([
                ('chatbot_id', '=', chatbot.id),
                ('phone', '=', phone),
                ('state', '=', 'handed_off'),
            ], limit=1)
            if handed_off:
                return False

        for msg in messages:
            try:
                with self.env.cr.savepoint():
                    self._handle_single_message(account, chatbot, msg, profile_name)
            except Exception:
                _logger.exception(
                    "Chatbot processor failed on account=%s msg=%s — falling through to stock",
                    account.id, msg.get('id'),
                )
                return False

        return True

    def _handle_single_message(self, account, chatbot, msg, profile_name):
        """Process one message from the webhook payload."""

        phone = self._normalize_phone(msg.get('from', ''))
        if not phone:
            return

        user_input = self._extract_user_input(msg)
        msg_type = msg.get('type', 'text')
        wamid = msg.get('id', '')

        Session = self.env['wa.chatbot.session'].sudo()
        session = Session.search([
            ('chatbot_id', '=', chatbot.id),
            ('phone', '=', phone),
            ('state', 'in', ('active', 'paused')),
        ], limit=1, order='last_activity_at desc')

        # Working hours guard
        if not chatbot._is_within_working_hours():
            if chatbot.outside_hours_message:
                send_helpers.send_text(self.env, account, phone, chatbot.outside_hours_message, session=session)
            self._log_inbound_message(account, phone, wamid, msg_type, user_input)
            return

        # Global keywords interrupt any running flow
        keyword_match = self._check_keywords(chatbot, user_input, is_global=True)
        if keyword_match:
            self._handle_keyword_match(
                chatbot, session, phone, profile_name or phone,
                keyword_match, user_input, account, wamid, msg_type,
            )
            return

        # No session or expired/closed: try non-global keywords or default flow
        if not session or session.state in ('expired', 'closed'):
            keyword_match = self._check_keywords(chatbot, user_input, is_global=False)
            if keyword_match:
                self._handle_keyword_match(
                    chatbot, None, phone, profile_name or phone,
                    keyword_match, user_input, account, wamid, msg_type,
                )
                return

            session = self._create_session(chatbot, phone, profile_name, account)
            self._log_session_message(session, 'inbound', user_input, msg_type=msg_type, wamid=wamid, account=account)

            if chatbot.welcome_message:
                import logging
                _logger.error("CHATBOT_PROCESSOR DEBUG: calling send_text for welcome_message!")
                wa_msg = send_helpers.send_text(self.env, account, phone, chatbot.welcome_message, session=session)
                self._log_session_message(session, 'outbound', chatbot.welcome_message, wa_msg=wa_msg)

            start_node = chatbot.default_flow_id.node_ids.filtered(lambda n: n.is_entry)
            if start_node:
                session.current_flow_id = chatbot.default_flow_id.id
                session.current_node_id = start_node[0].id
                self._execute_node(session, start_node[0], account=account)
            return

        # Active session: advance state + process at current node
        session.write({
            'last_activity_at': fields.Datetime.now(),
            'message_count': session.message_count + 1,
        })
        session.set_variable('last_input', user_input)
        session.set_variable('message_count', session.message_count)

        self._log_session_message(session, 'inbound', user_input, msg_type=msg_type, wamid=wamid, account=account)

        current_node = session.current_node_id
        if not current_node:
            start_node = session.current_flow_id.node_ids.filtered(lambda n: n.is_entry)
            if start_node:
                self._execute_node(session, start_node[0], account=account)
            return

        # Interactive nodes may want the button/list ID rather than the label
        if current_node.node_type == 'interactive':
            interactive_id = self._extract_interactive_id(msg)
            if interactive_id:
                user_input = interactive_id

        self._process_user_input(session, current_node, user_input, account)

    # =========================================================================
    # FSM CORE
    # =========================================================================

    def _execute_node(self, session, node, user_input=None, account=None, depth=0):
        """Recursive FSM executor. Caps at MAX_EXECUTION_DEPTH to prevent loops."""
        if depth > MAX_EXECUTION_DEPTH:
            _logger.warning("Chatbot max execution depth reached for session %s", session.id)
            return

        if not account:
            account = session.account_id

        cfg = node.get_config()
        phone = session.phone

        session.write({
            'current_node_id': node.id,
            'current_flow_id': node.flow_id.id,
            'last_activity_at': fields.Datetime.now(),
        })

        # ---- START ----
        if node.node_type == 'start':
            next_node = self._get_next_node(node, 'default')
            if next_node:
                self._execute_node(session, next_node, account=account, depth=depth + 1)
            return

        # ---- SEND MESSAGE ----
        if node.node_type == 'send_message':
            body = self._resolve_variables(session, cfg.get('body', ''))
            mtype = cfg.get('message_type', 'text')

            if mtype == 'text':
                _logger.error("CHATBOT_PROCESSOR DEBUG: calling send_text for body!")
                wa_msg = send_helpers.send_text(self.env, account, phone, body, session=session)
            elif mtype == 'location':
                wa_msg = send_helpers.send_location(self.env, account, phone, cfg.get('location', {}), session=session)
            else:
                # Media messages
                attachment_id = cfg.get('attachment_id')
                attachment = self.env['ir.attachment'].sudo().browse(attachment_id) if attachment_id else None
                wa_msg = send_helpers.send_media(
                    self.env, account, phone, mtype,
                    attachment if attachment and attachment.exists() else None,
                    caption=body,
                    session=session,
                )

            self._log_session_message(session, 'outbound', body, node_id=node.id, wa_msg=wa_msg)

            next_node = self._get_next_node(node, 'default')
            if next_node:
                self._execute_node(session, next_node, account=account, depth=depth + 1)
            return

        # ---- INTERACTIVE (BUTTONS / LIST) ----
        if node.node_type == 'interactive':
            body = self._resolve_variables(session, cfg.get('body', ''))
            payload = self._build_interactive_payload(cfg, body)
            wa_msg = send_helpers.send_interactive(self.env, account, phone, payload, session=session)
            self._log_session_message(session, 'outbound', body, node_id=node.id, wa_msg=wa_msg, msg_type='interactive')
            return  # wait for user response

        # ---- INPUT (ASK QUESTION) ----
        if node.node_type == 'input':
            if user_input is None:
                body = self._resolve_variables(session, cfg.get('body', ''))
                wa_msg = send_helpers.send_text(self.env, account, phone, body, session=session)
                self._log_session_message(session, 'outbound', body, node_id=node.id, wa_msg=wa_msg)
                return  # wait for user input
            return  # user responded: handled in _process_user_input

        # ---- CONDITION / BRANCH ----
        if node.node_type == 'condition':
            conditions = cfg.get('conditions', [])
            for cond in conditions:
                if self._evaluate_condition(session, cond):
                    next_node = self._get_next_node(node, cond.get('id', ''))
                    if next_node:
                        self._execute_node(session, next_node, account=account, depth=depth + 1)
                    return
            next_node = self._get_next_node(node, 'default')
            if next_node:
                self._execute_node(session, next_node, account=account, depth=depth + 1)
            return

        # ---- ACTION ----
        if node.node_type == 'action':
            self._execute_action(session, cfg)
            self._log_session_message(
                session, 'system', f"Action: {cfg.get('action_type', '')}",
                node_id=node.id, msg_type='system',
            )
            next_node = self._get_next_node(node, 'default')
            if next_node:
                self._execute_node(session, next_node, account=account, depth=depth + 1)
            return

        # ---- API CALL ----
        if node.node_type == 'api_call':
            success = self._execute_api_call(session, cfg)
            handle = 'success' if success else 'error'
            if not success and cfg.get('error_message'):
                err_msg = self._resolve_variables(session, cfg['error_message'])
                send_helpers.send_text(self.env, account, phone, err_msg, session=session)
                self._log_session_message(session, 'outbound', err_msg, node_id=node.id)
            next_node = self._get_next_node(node, handle)
            if next_node:
                self._execute_node(session, next_node, account=account, depth=depth + 1)
            return

        # ---- DELAY ----
        if node.node_type == 'delay':
            duration = cfg.get('duration', 0)
            unit = cfg.get('unit', 'seconds')
            if unit == 'minutes':
                duration *= 60
            elif unit == 'hours':
                duration *= 3600
            duration = min(duration, 30)  # cap to avoid webhook timeout
            if duration > 0:
                time.sleep(duration)
            next_node = self._get_next_node(node, 'default')
            if next_node:
                self._execute_node(session, next_node, account=account, depth=depth + 1)
            return

        # ---- TEMPLATE MESSAGE ----
        if node.node_type == 'template':
            template_id = cfg.get('template_id')
            if template_id:
                template = self.env['whatsapp.template'].sudo().browse(template_id)
                if template.exists() and template.status == 'approved':
                    variable_mapping = cfg.get('variable_mapping', {})
                    resolved = {}
                    for pos, val in variable_mapping.items():
                        # Odoo expects 'free_text_1' instead of just '1'
                        key = f"free_text_{pos}" if str(pos).isdigit() else pos
                        resolved[key] = self._resolve_variables(session, val)
                        
                    wa_msg_rec = send_helpers.send_template(
                        self.env, account, phone, template, resolved, session=session,
                    )
                    self._log_session_message(
                        session, 'outbound',
                        f"Template: {template.display_name}",
                        node_id=node.id, wa_msg=wa_msg_rec, msg_type='template',
                    )
            next_node = self._get_next_node(node, 'default')
            if next_node:
                self._execute_node(session, next_node, account=account, depth=depth + 1)
            return

        # ---- HANDOFF ----
        if node.node_type == 'handoff':
            self._execute_handoff(session, cfg, account)
            return

        # ---- GOTO ----
        if node.node_type == 'goto':
            target_type = cfg.get('target_type', 'node')
            if target_type == 'node' and cfg.get('target_node_id'):
                target = self.env['wa.chatbot.node'].sudo().browse(cfg['target_node_id'])
                if target.exists():
                    self._execute_node(session, target, account=account, depth=depth + 1)
            elif target_type == 'flow' and cfg.get('target_flow_id'):
                session.push_flow_stack(session.current_flow_id.id, node.id)
                target_flow = self.env['wa.chatbot.flow'].sudo().browse(cfg['target_flow_id'])
                if target_flow.exists():
                    start_node = target_flow.node_ids.filtered(lambda n: n.is_entry)
                    if start_node:
                        session.current_flow_id = target_flow.id
                        if not cfg.get('carry_variables', True):
                            session.clear_variables()
                        self._execute_node(session, start_node[0], account=account, depth=depth + 1)
            return

        # ---- CLOSE ----
        if node.node_type == 'close':
            message = cfg.get('message', '')
            if message:
                body = self._resolve_variables(session, message)
                wa_msg = send_helpers.send_text(self.env, account, phone, body, session=session)
                self._log_session_message(session, 'outbound', body, node_id=node.id, wa_msg=wa_msg)
            session.write({
                'state': 'closed',
                'ended_at': fields.Datetime.now(),
            })
            return

    def _process_user_input(self, session, current_node, user_input, account):
        """Handle a user response at a waiting node (interactive / input)."""
        cfg = current_node.get_config()
        phone = session.phone

        if current_node.node_type == 'interactive':
            matched_handle = self._match_interactive_response(cfg, user_input)
            if matched_handle:
                session.fallback_count = 0
                session.set_variable('last_input', user_input)
                next_node = self._get_next_node(current_node, matched_handle)
                if next_node:
                    self._execute_node(session, next_node, account=account)
                return

            keyword_match = self._check_keywords(session.chatbot_id, user_input, is_global=False)
            if keyword_match:
                self._handle_keyword_match(
                    session.chatbot_id, session, phone,
                    session.partner_id.name or phone,
                    keyword_match, user_input, account, '', 'text',
                )
                return

            self._handle_fallback(session, account)
            return

        if current_node.node_type == 'input':
            if self._validate_input(cfg, user_input):
                session.fallback_count = 0
                var_name = cfg.get('variable_name') or 'input'
                session.set_variable(var_name, user_input)
                next_node = self._get_next_node(current_node, 'default')
                if next_node:
                    self._execute_node(session, next_node, account=account)
            else:
                session.fallback_count = session.fallback_count + 1
                max_retries = cfg.get('max_retries', 2)
                if session.fallback_count >= max_retries:
                    next_node = self._get_next_node(current_node, 'error')
                    if next_node:
                        session.fallback_count = 0
                        self._execute_node(session, next_node, account=account)
                    else:
                        self._handle_fallback(session, account)
                else:
                    error_msg = self._resolve_variables(
                        session,
                        cfg.get('validation_error', 'Invalid input. Please try again.'),
                    )
                    send_helpers.send_text(self.env, account, phone, error_msg, session=session)
                    self._log_session_message(session, 'outbound', error_msg, node_id=current_node.id)
            return

        # Other waiting states → try non-global keywords, then fallback
        keyword_match = self._check_keywords(session.chatbot_id, user_input, is_global=False)
        if keyword_match:
            self._handle_keyword_match(
                session.chatbot_id, session, phone,
                session.partner_id.name or phone,
                keyword_match, user_input, account, '', 'text',
            )
            return

        self._handle_fallback(session, account)

    # =========================================================================
    # SESSION / PARTNER HELPERS
    # =========================================================================

    def _find_active_chatbot(self, account, messages):
        """Find an active chatbot for the account.

        Priority:
        1. Chatbot with an active session for the sender.
        2. Chatbot where the message matches a keyword.
        """
        if not messages:
            return None

        msg = messages[0]
        phone = self._normalize_phone(msg.get('from', ''))
        user_input = self._extract_user_input(msg)

        chatbots = self.env['wa.chatbot'].sudo().search([
            ('account_id', '=', account.id),
            ('state', '=', 'active'),
        ])
        if not chatbots:
            return None

        # PRIORITY 1: Does any chatbot have an active session for this user?
        Session = self.env['wa.chatbot.session'].sudo()
        session = Session.search([
            ('chatbot_id', 'in', chatbots.ids),
            ('phone', '=', phone),
            ('state', 'in', ('active', 'paused')),
        ], limit=1, order='last_activity_at desc')
        if session:
            return session.chatbot_id

        # PRIORITY 2: Does the message match any chatbot's keywords?
        for chatbot in chatbots:
            if self._check_keywords(chatbot, user_input, is_global=True) or \
               self._check_keywords(chatbot, user_input, is_global=False):
                return chatbot

        # PRIORITY 3: Fallback to global default chatbot
        default_chatbot_id = self.env['ir.config_parameter'].sudo().get_param('dev_whatsapp_chatbot_ent.wa_default_chatbot_id')
        if default_chatbot_id:
            default_chatbot = self.env['wa.chatbot'].sudo().browse(int(default_chatbot_id))
            if default_chatbot.exists() and default_chatbot.state == 'active' and default_chatbot.account_id == account:
                return default_chatbot

        return None

    def _create_session(self, chatbot, phone, profile_name, account):
        Session = self.env['wa.chatbot.session'].sudo()

        # Close stale sessions for this phone so only one is active
        stale = Session.search([
            ('chatbot_id', '=', chatbot.id),
            ('phone', '=', phone),
            ('state', 'in', ('active', 'paused')),
        ])
        if stale:
            stale.write({'state': 'expired', 'ended_at': fields.Datetime.now()})

        partner = self._find_partner(phone, profile_name)

        session = Session.create({
            'chatbot_id': chatbot.id,
            'phone': phone,
            'partner_id': partner.id if partner else False,
            'current_flow_id': chatbot.default_flow_id.id if chatbot.default_flow_id else False,
        })

        session.set_variables({
            'phone': phone,
            'customer_name': partner.name if partner else (profile_name or ''),
            'partner_id': partner.id if partner else 0,
            'session_id': session.id,
            'message_count': 0,
            'last_input': '',
        })

        return session

    def _find_partner(self, phone, profile_name):
        """Find or create a res.partner using the enterprise helper."""
        Partner = self.env['res.partner'].sudo()
        # enterprise: addons/whatsapp/models/res_partner.py:33
        partner = Partner._find_or_create_from_number(phone, profile_name or phone)
        return partner

    # =========================================================================
    # WEBHOOK PAYLOAD PARSING
    # =========================================================================

    @staticmethod
    def _normalize_phone(raw):
        """Meta sends the number without a leading +. Add it if missing."""
        if not raw:
            return ''
        raw = str(raw).strip()
        if not raw.startswith('+'):
            raw = '+' + raw
        return raw

    def _extract_user_input(self, msg):
        """Return a human-readable string for logging/variable substitution."""
        mtype = msg.get('type', 'text')
        if mtype == 'text':
            return msg.get('text', {}).get('body', '')
        if mtype == 'interactive':
            interactive = msg.get('interactive', {})
            itype = interactive.get('type', '')
            if itype == 'button_reply':
                reply = interactive.get('button_reply', {})
                return reply.get('title', '') or reply.get('id', '')
            if itype == 'list_reply':
                reply = interactive.get('list_reply', {})
                return reply.get('title', '') or reply.get('id', '')
        if mtype in ('image', 'video', 'audio', 'document'):
            return msg.get(mtype, {}).get('caption', f'[{mtype}]')
        if mtype == 'location':
            loc = msg.get('location', {})
            return f"{loc.get('latitude', '')},{loc.get('longitude', '')}"
        return f'[{mtype}]'

    def _extract_interactive_id(self, msg):
        """For interactive responses, return the button/list row ID (used for routing)."""
        if msg.get('type') != 'interactive':
            return None
        interactive = msg.get('interactive', {})
        itype = interactive.get('type', '')
        if itype == 'button_reply':
            return interactive.get('button_reply', {}).get('id', '')
        if itype == 'list_reply':
            return interactive.get('list_reply', {}).get('id', '')
        return None

    # =========================================================================
    # KEYWORDS / ROUTING
    # =========================================================================

    def _check_keywords(self, chatbot, text, is_global=True):
        if not text:
            return None
        keywords = chatbot.keyword_ids.filtered(
            lambda k: k.active and k.is_global == is_global
        ).sorted('priority')
        for kw in keywords:
            if kw.matches(text):
                return kw
        return None

    def _handle_keyword_match(self, chatbot, session, phone, profile_name,
                              keyword, user_input, account, wamid, msg_type):
        if keyword.reset_session or not session:
            if session and session.state in ('active', 'paused'):
                session.write({'state': 'closed', 'ended_at': fields.Datetime.now()})
            session = self._create_session(chatbot, phone, profile_name, account)

        self._log_session_message(session, 'inbound', user_input, msg_type=msg_type, wamid=wamid, account=account)
        session.set_variable('last_input', user_input)
        session.fallback_count = 0

        if keyword.target_type == 'flow' and keyword.target_flow_id:
            session.current_flow_id = keyword.target_flow_id.id
            start_node = keyword.target_flow_id.node_ids.filtered(lambda n: n.is_entry)
            if start_node:
                session.current_node_id = start_node[0].id
                self._execute_node(session, start_node[0], account=account)

        elif keyword.target_type == 'node' and keyword.target_node_id:
            session.current_flow_id = keyword.target_node_id.flow_id.id
            session.current_node_id = keyword.target_node_id.id
            self._execute_node(session, keyword.target_node_id, account=account)

        elif keyword.target_type == 'handoff':
            self._execute_handoff(session, {
                'message': chatbot.handoff_message or '',
                'priority': 'normal',
                'context_summary': True,
            }, account)

        elif keyword.target_type == 'close':
            close_msg = 'Goodbye!'
            send_helpers.send_text(self.env, account, phone, close_msg, session=session)
            self._log_session_message(session, 'outbound', close_msg)
            session.write({'state': 'closed', 'ended_at': fields.Datetime.now()})

        return session

    def _handle_fallback(self, session, account):
        chatbot = session.chatbot_id
        session.fallback_count = session.fallback_count + 1

        if session.fallback_count >= chatbot.fallback_max_retries:
            self._execute_handoff(session, {
                'message': chatbot.handoff_message or 'Connecting you with an agent...',
                'priority': 'normal',
                'context_summary': True,
            }, account)
        else:
            msg = self._resolve_variables(
                session,
                chatbot.fallback_message or "Sorry, I didn't understand that.",
            )
            send_helpers.send_text(self.env, account, session.phone, msg, session=session)
            self._log_session_message(session, 'outbound', msg)

    def _get_next_node(self, node, handle='default'):
        """Find the target node for the given output handle."""
        edges = node.outgoing_edge_ids.sorted('sequence')
        for edge in edges:
            if edge.source_handle == handle:
                return edge.target_node_id
        for edge in edges:
            if edge.condition_type == 'fallback':
                return edge.target_node_id
        for edge in edges:
            if edge.condition_type == 'always':
                return edge.target_node_id
        if edges:
            return edges[0].target_node_id
        return None

    def _match_interactive_response(self, cfg, user_input):
        if not user_input:
            return None
        for btn in cfg.get('buttons', []):
            if btn.get('id') == user_input:
                return btn['id']
            if btn.get('title', '').lower().strip() == user_input.lower().strip():
                return btn['id']
        for section in cfg.get('sections', []):
            for row in section.get('rows', []):
                if row.get('id') == user_input:
                    return row['id']
                if row.get('title', '').lower().strip() == user_input.lower().strip():
                    return row['id']
        return None

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def _validate_input(self, cfg, user_input):
        input_type = cfg.get('input_type', 'any')
        if input_type == 'any':
            return bool(user_input)
        if input_type == 'email':
            return bool(re_module.match(r'^[\w.+-]+@[\w.-]+\.\w+$', user_input or ''))
        if input_type == 'phone':
            return bool(re_module.match(r'^\+?[\d\s()-]{7,20}$', user_input or ''))
        if input_type == 'number':
            try:
                float(user_input)
                return True
            except (ValueError, TypeError):
                return False
        if input_type == 'date':
            return self._validate_date_input(cfg, user_input)
        if input_type == 'text':
            regex = cfg.get('validation_regex')
            if regex:
                try:
                    return bool(re_module.match(regex, user_input or ''))
                except re_module.error:
                    return True
            return bool(user_input)
        return bool(user_input)

    def _validate_date_input(self, cfg, user_input):
        date_format = cfg.get('date_format', 'DD-MM-YYYY')
        pattern = DATE_FORMAT_PATTERNS.get(date_format, r'^\d{2}-\d{2}-\d{4}$')
        if not re_module.match(pattern, user_input or ''):
            return False
        strptime_fmt = DATE_FORMAT_STRPTIME.get(date_format, '%d-%m-%Y')
        try:
            datetime.strptime(user_input, strptime_fmt)
            return True
        except ValueError:
            return False

    # =========================================================================
    # CONDITIONS / ACTIONS / API
    # =========================================================================

    def _evaluate_condition(self, session, condition):
        var_name = condition.get('variable', '')
        operator = condition.get('operator', 'equals')
        expected = condition.get('value', '')

        actual = session.get_variable(var_name, '')
        if actual is None:
            actual = ''
        actual = str(actual)
        expected = str(expected)

        al = actual.lower()
        el = expected.lower()

        if operator == 'equals':
            return al == el
        if operator == 'not_equals':
            return al != el
        if operator == 'contains':
            return el in al
        if operator == 'not_contains':
            return el not in al
        if operator == 'starts_with':
            return al.startswith(el)
        if operator == 'ends_with':
            return al.endswith(el)
        if operator == 'regex':
            try:
                return bool(re_module.search(expected, actual, re_module.IGNORECASE))
            except re_module.error:
                return False
        if operator in ('gt', 'lt', 'gte', 'lte'):
            try:
                a, e = float(actual), float(expected)
            except ValueError:
                return False
            return {'gt': a > e, 'lt': a < e, 'gte': a >= e, 'lte': a <= e}[operator]
        if operator == 'is_set':
            return bool(session.get_variable(var_name))
        if operator == 'is_not_set':
            return not bool(session.get_variable(var_name))
        if operator == 'in_list':
            items = [i.strip().lower() for i in expected.split(',')]
            return al in items
        return False

    def _execute_action(self, session, cfg):
        action_type = cfg.get('action_type', '')

        if action_type == 'set_variable':
            var_cfg = cfg.get('set_variable', {})
            name = var_cfg.get('name', '')
            value = self._resolve_variables(session, var_cfg.get('value', ''))
            if name:
                session.set_variable(name, value)

        elif action_type == 'create_record':
            rec_cfg = cfg.get('create_record', {})
            model_name = rec_cfg.get('model', '')
            values = rec_cfg.get('values', {})
            field_types = rec_cfg.get('field_types', {})
            if model_name and values:
                try:
                    Model = self.env[model_name].sudo()
                    resolved_vals = {}
                    for k, v in values.items():
                        resolved = self._resolve_variables(session, str(v))
                        resolved_vals[k] = self._coerce_field_value(resolved, field_types.get(k, ''), Model, k)
                    Model.create(resolved_vals)
                except Exception as e:
                    _logger.warning("Action create_record failed: %s", e)

        elif action_type == 'update_record':
            rec_cfg = cfg.get('update_record', {})
            model_name = rec_cfg.get('model', '')
            domain_str = rec_cfg.get('domain', '[]')
            values = rec_cfg.get('values', {})
            field_types = rec_cfg.get('field_types', {})
            if model_name and values:
                try:
                    Model = self.env[model_name].sudo()
                    # Parameterized, injection-safe domain (same builder as
                    # search_record): user values land only in leaf value slots.
                    domain = self._build_safe_domain(Model, session.get_variables(), domain_str)
                    if domain is None:
                        # Unparseable domain → do NOT fall back to an empty domain
                        # (that would match & overwrite an arbitrary first record).
                        _logger.warning("update_record: unparseable domain for %s, skipping", model_name)
                        return
                    records = Model.search(domain, limit=1)
                    if records:
                        resolved_vals = {}
                        for k, v in values.items():
                            resolved = self._resolve_variables(session, str(v))
                            resolved_vals[k] = self._coerce_field_value(resolved, field_types.get(k, ''), Model, k)
                        records.write(resolved_vals)
                except Exception as e:
                    _logger.warning("Action update_record failed: %s", e)

        elif action_type == 'send_notification':
            notif_cfg = cfg.get('notification', {})
            message = self._resolve_variables(session, notif_cfg.get('message', ''))
            user_ids = notif_cfg.get('user_ids', [])
            if message and user_ids:
                try:
                    # Coerce IDs to integers to be safe with JSON storage
                    clean_user_ids = [int(uid) for uid in user_ids if uid]
                    users = self.env['res.users'].sudo().browse(clean_user_ids)
                    
                    # Get valid users
                    valid_users = users.filtered(lambda u: u.exists())
                    
                    if valid_users:
                        
                        for user in valid_users:
                            try:
                                # 1. Real-time Display Notification (Blue Toast)
                                # Type 'info' renders the cyan/blue style seen in standard Odoo notifications
                                user._bus_send('simple_notification', {
                                    'type': 'info',
                                    'title': _("Chatbot Notification"),
                                    'message': message,
                                    'sticky': False,
                                })
                                
                                # 2. Discuss Inbox / Bell Notification
                                # We use message_notify to ensure it hits the user's Inbox/Bell icon
                                user.partner_id.message_notify(
                                    body=message,
                                    partner_ids=user.partner_id.ids,
                                    author_id=self.env.ref('base.partner_root').id,
                                    subject=_("Chatbot Alert: %s", session.phone),
                                )
                            except Exception as notif_e:
                                _logger.warning("Failed to send notification to user %s: %s", user.name, notif_e)

                except Exception as e:
                    _logger.warning("Action send_notification failed: %s", e)

        elif action_type == 'search_record':
            self._execute_search(session, cfg.get('search_record', {}))

    # =========================================================================
    # SEARCH ODOO DATA  (action_type == 'search_record')
    # =========================================================================

    def _execute_search(self, session, search_cfg):
        """Run a search_record action: query an Odoo model and write the result
        back into session variables. Never raises — on any failure it stores an
        empty/not-found result so the flow can still branch on {{search_found}}.
        """
        partner_id = session.partner_id.id if session.partner_id else False
        result = self._run_search(search_cfg, session.get_variables(), partner_id)
        for name, value in (result.get('variables') or {}).items():
            session.set_variable(name, value)

    def _run_search(self, search_cfg, variables, partner_id):
        """Core search engine for the search_record action.

        Returns:
            {
              'found': bool,
              'count': int,
              'result_text': str,            # list-mode rendered text (or empty_value)
              'variables': {name: value},    # session variables to write back
            }

        'variables' holds the single-mode field mappings (or the list-mode result
        variable) plus the found/count flag variables.
        """
        search_cfg = search_cfg or {}
        found_var = search_cfg.get('found_variable') or 'search_found'
        count_var = search_cfg.get('count_variable') or 'search_count'
        result_var = search_cfg.get('result_variable') or 'search_results'
        empty_value = search_cfg.get('empty_value', '') or ''
        result_mode = search_cfg.get('result_mode', 'single')

        def _empty(text=None):
            text = empty_value if text is None else text
            out_vars = {found_var: 'false', count_var: '0'}
            if result_mode == 'list':
                out_vars[result_var] = text
            return {'found': False, 'count': 0, 'result_text': text, 'variables': out_vars}

        model_name = (search_cfg.get('model') or '').strip()
        if not model_name or model_name not in self.env:
            return _empty()

        try:
            Model = self.env[model_name].sudo()

            # Fields the node references: single → mapping keys, list → {{placeholders}}
            field_mapping = search_cfg.get('field_mapping', {}) or {}
            if result_mode == 'list':
                read_fields = re_module.findall(r'\{\{(\w+)\}\}', search_cfg.get('row_template', '') or '')
            else:
                read_fields = list(field_mapping.keys())
            read_fields = [f for f in dict.fromkeys(read_fields) if f in Model._fields]

            # Build the domain from the visual rule builder. Fall back to a raw
            # domain string only for advanced/imported configs with no rules.
            filters = search_cfg.get('filters')
            if filters:
                domain = self._build_domain_from_filters(
                    Model, variables, filters, search_cfg.get('match_type', 'all'),
                )
            else:
                domain = self._build_safe_domain(Model, variables, search_cfg.get('domain', ''))
            if domain is None:
                return _empty()

            # Optional: restrict results to the contact's own records
            if search_cfg.get('scope_to_contact'):
                partner_field = (search_cfg.get('partner_field') or '').strip()
                if not partner_field or partner_field not in Model._fields or not partner_id:
                    # Fail closed: scoping requested but unavailable → no cross-customer leak.
                    return _empty()
                # A trailing leaf is implicitly ANDed with the rest of the domain,
                # regardless of any &/| operators the builder used.
                domain = domain + [(partner_field, '=', partner_id)]

            try:
                limit = max(1, min(int(search_cfg.get('limit') or 5), 50))
            except (ValueError, TypeError):
                limit = 5
            order = (search_cfg.get('order') or '').strip() or None

            records = Model.search(domain, order=order, limit=limit)
        except Exception as e:
            _logger.warning("search_record failed on model %s: %s", model_name, e)
            return _empty()

        if not records:
            return _empty()

        # Human-readable value dict per record
        records_vals = [
            {f: self._format_field_value(rec, f) for f in read_fields}
            for rec in records
        ]

        out_vars = {found_var: 'true', count_var: str(len(records))}
        result_text = ''

        if result_mode == 'list':
            separator = (search_cfg.get('separator') or '\n').replace('\\n', '\n')
            row_template = search_cfg.get('row_template', '') or ''
            rows = [self._render_record_template(rv, row_template) for rv in records_vals]
            result_text = separator.join(r for r in rows if r) or empty_value
            out_vars[result_var] = result_text
        else:
            first = records_vals[0]
            for model_field, var_name in field_mapping.items():
                if var_name:
                    out_vars[var_name] = first.get(model_field, '')

        return {
            'found': True,
            'count': len(records),
            'result_text': result_text,
            'variables': out_vars,
        }

    # Friendly operator (visual builder) → Odoo domain operator
    _SEARCH_OPERATORS = {
        'equals': '=',
        'not_equals': '!=',
        'contains': 'ilike',
        'not_contains': 'not ilike',
        'greater_than': '>',
        'less_than': '<',
        'greater_equal': '>=',
        'less_equal': '<=',
    }

    def _build_domain_from_filters(self, Model, variables, filters, match_type='all'):
        """Turn the visual rule builder's structured filters into a domain list.

        Each filter is {field, operator, value_source: 'value'|'variable', value}.
        Values are taken either literally or from a session variable, then type-
        coerced — they only ever occupy the value slot of a leaf, so there is no
        way for user input to alter the query structure (injection-proof by design).
        """
        leaves = []
        for flt in filters or []:
            field = (flt.get('field') or '').strip()
            if not field or field not in Model._fields:
                continue
            # The search builder offers ALL fields (for display/mapping), but only
            # stored or explicitly-searchable fields can go in a domain. Skip the
            # rest so one non-searchable pick doesn't void the whole search.
            fobj = Model._fields[field]
            if not (fobj.store or fobj.search):
                _logger.info("search_record: skipping non-searchable field %r on %s", field, Model._name)
                continue
            op_key = flt.get('operator') or 'equals'

            if op_key == 'is_set':
                leaves.append((field, '!=', False))
                continue
            if op_key == 'is_not_set':
                leaves.append((field, '=', False))
                continue

            if flt.get('value_source') == 'variable':
                raw = variables.get((flt.get('value') or '').strip(), '')
            else:
                raw = flt.get('value', '')

            odoo_op = self._SEARCH_OPERATORS.get(op_key, '=')
            if odoo_op in ('ilike', 'not ilike'):
                value = str(raw)
            else:
                value = self._coerce_field_value(str(raw), '', Model, field)
            leaves.append((field, odoo_op, value))

        if not leaves:
            return []
        if match_type == 'any' and len(leaves) > 1:
            # Prefix N-1 OR operators (Polish notation) to OR all leaves together.
            return ['|'] * (len(leaves) - 1) + leaves
        return leaves

    def _build_safe_domain(self, Model, variables, domain_str):
        """Turn a builder-authored domain template into a safe domain list.

        {{var}} placeholders are replaced with unique sentinel string literals
        BEFORE parsing, then each sentinel is substituted with the real session
        value (type-coerced) only in leaf VALUE positions. User input therefore
        can never inject a field name, operator, or list bracket.

        Returns [] for an empty template, a domain list on success, or None when
        the template can't be parsed (caller treats that as a no-match).
        """
        if not domain_str or not domain_str.strip():
            return []

        sentinels = {}
        counter = [0]

        def _make(match):
            token = '__WA_SENTINEL_%d__' % counter[0]
            counter[0] += 1
            sentinels[token] = match.group(2).strip()
            return repr(token)

        # Match optionally-quoted placeholders: '{{v}}', "{{v}}" or bare {{v}}
        templated = re_module.sub(r"""(['"]?)\{\{(\w+)\}\}\1""", _make, domain_str)
        try:
            parsed = ast.literal_eval(templated)
        except Exception:
            _logger.warning("search_record: could not parse domain %r", domain_str)
            return None

        if isinstance(parsed, tuple):
            parsed = [parsed]
        if not isinstance(parsed, list):
            return None

        domain = []
        for item in parsed:
            if (isinstance(item, (list, tuple)) and len(item) == 3
                    and isinstance(item[0], str) and item[0] not in ('&', '|', '!')):
                field, op, value = item
                if isinstance(value, str) and value in sentinels:
                    raw = variables.get(sentinels[value], '')
                    value = self._coerce_field_value(str(raw), '', Model, field)
                domain.append((field, op, value))
            else:
                # operator token ('&','|','!') or an already-literal leaf — keep as-is
                domain.append(item)
        return domain

    @staticmethod
    def _format_field_value(record, field_name):
        """Return a human-readable value for one field on a single record."""
        if field_name not in record._fields:
            return ''
        field = record._fields[field_name]
        value = record[field_name]
        if value is False or value is None:
            return ''
        ftype = field.type
        if ftype == 'many2one':
            return value.display_name or ''
        if ftype in ('one2many', 'many2many'):
            return ', '.join(v for v in value.mapped('display_name') if v)
        if ftype == 'selection':
            try:
                selection = dict(field._description_selection(record.env))
                return selection.get(value, value)
            except Exception:
                return value
        return value

    def _render_record_template(self, record_vals, template):
        """Resolve {{field}} placeholders against a single record's value dict.

        Distinct from _resolve_variables (session vars): here {{name}} means the
        record's 'name' field. Missing keys render as an empty string.
        """
        if not template:
            return ''

        def _replace(match):
            value = record_vals.get(match.group(1).strip(), '')
            return str(value) if value not in (False, None) else ''

        return re_module.sub(r'\{\{(\w+)\}\}', _replace, template).replace('\\n', '\n')

    def _execute_api_call(self, session, cfg):
        """Execute an HTTP API call node. Returns True on success (HTTP < 400).

        Request URL, header values and JSON body values all support {{variable}}
        substitution. The response is stored raw in `response_variable`, the HTTP
        status in `api_status_code`, and any number of fields can be pulled out of
        a JSON response into session variables via `response_mappings`.
        """
        url = self._resolve_variables(session, cfg.get('url', ''))
        method = (cfg.get('method') or 'GET').upper()
        headers = cfg.get('headers', {}) or {}
        body_json = cfg.get('body_json', {}) or {}
        response_variable = cfg.get('response_variable') or 'api_response'

        if not url or method not in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE'):
            return False

        # Cap the timeout so a slow endpoint can't tie up the webhook worker.
        try:
            timeout = min(max(int(cfg.get('timeout') or 10), 1), 30)
        except (ValueError, TypeError):
            timeout = 10

        resolved_headers = {k.strip(): self._resolve_variables(session, str(v)) for k, v in headers.items()}
        resolved_body = {k.strip(): self._resolve_variables(session, str(v)) for k, v in body_json.items()}

        try:
            request_kwargs = {'headers': resolved_headers, 'timeout': timeout}
            if method in ('POST', 'PUT', 'PATCH'):
                request_kwargs['json'] = resolved_body
            resp = req_lib.request(method, url, **request_kwargs)

            # Expose the status code so a flow can branch beyond success/error.
            session.set_variable('api_status_code', str(resp.status_code))

            try:
                response_data = resp.json()
                session.set_variable(response_variable, json.dumps(response_data))
            except Exception:
                response_data = resp.text
                session.set_variable(response_variable, resp.text)

            self._apply_response_mappings(session, cfg, response_data)
            self._apply_response_list(session, cfg, response_data)

            return resp.status_code < 400
        except Exception as e:
            _logger.warning("API call failed for session %s: %s", session.id, e)
            session.set_variable(response_variable, str(e))
            session.set_variable('api_status_code', '0')
            return False

    def _apply_response_mappings(self, session, cfg, response_data):
        """Set session variables from JSON paths in the API response.

        Reads the `response_mappings` list ([{path, variable}, ...]) and also
        honours the legacy single success_path/success_variable pair.
        """
        mappings = list(cfg.get('response_mappings') or [])
        legacy_path = cfg.get('success_path')
        legacy_var = cfg.get('success_variable')
        if legacy_path and legacy_var:
            mappings.append({'path': legacy_path, 'variable': legacy_var})

        for mapping in mappings:
            path = (mapping.get('path') or '').strip()
            var = (mapping.get('variable') or '').strip()
            if not path or not var:
                continue
            extracted = self._extract_json_path(response_data, path)
            session.set_variable(var, '' if extracted is None else str(extracted))

    def _apply_response_list(self, session, cfg, response_data):
        """Render a LIST in the API response into a single text variable.

        `list_path` points at the array in the response ('' = the response is
        itself the array). Each item that is a dict is rendered with
        `list_row_template` ({{field}} → that item's field), others are stringified;
        rows are joined by `list_separator`, capped at `list_limit`, and stored in
        `list_variable`. `<list_variable>_count` gets the total item count.

        Skipped entirely unless `list_variable` is set.
        """
        list_var = (cfg.get('list_variable') or '').strip()
        if not list_var:
            return

        row_template = cfg.get('list_row_template') or ''
        separator = (cfg.get('list_separator') or '\n').replace('\\n', '\n')
        empty_value = cfg.get('list_empty_value', '') or ''
        try:
            limit = max(1, min(int(cfg.get('list_limit') or 10), 50))
        except (ValueError, TypeError):
            limit = 10

        items = self._extract_json_path(response_data, cfg.get('list_path') or '')
        if not isinstance(items, list):
            items = []

        rows = []
        for item in items[:limit]:
            rendered = (
                self._render_record_template(item, row_template)
                if isinstance(item, dict) else str(item)
            )
            if rendered:
                rows.append(rendered)

        session.set_variable(list_var, separator.join(rows) or empty_value)
        session.set_variable(list_var + '_count', str(len(items)))

    # =========================================================================
    # HANDOFF
    # =========================================================================

    def _execute_handoff(self, session, cfg, account):
        """Transfer the conversation to a human agent via a discuss.channel (whatsapp type)."""
        phone = session.phone
        chatbot = session.chatbot_id

        # 1. Acknowledge to the WhatsApp user
        try:
            message = self._resolve_variables(session, cfg.get('message', '') or chatbot.handoff_message or '')
            if message:
                wa_msg = send_helpers.send_text(self.env, account, phone, message, session=session)
                self._log_session_message(session, 'outbound', message, wa_msg=wa_msg)
        except Exception as e:
            _logger.warning("Handoff: failed to send handoff message to user: %s", e)

        # 2. Resolve the bot user: node → chatbot → account.notify_user_ids → admin
        node = session.current_node_id
        bot_user = (
            node.user_id
            or chatbot.user_id
            or (account.notify_user_ids[:1] if account.notify_user_ids else False)
            or self.env.ref('base.user_admin')
        )
        bot_partner = bot_user.partner_id
        partner = session.partner_id

        # 3. Find or create the whatsapp discuss channel using the enterprise helper.
        #    The helper handles responsible-user assignment + whatsapp_partner_id creation.
        Channel = self.env['discuss.channel'].sudo()
        channel = Channel.search([
            ('channel_type', '=', 'whatsapp'),
            ('wa_account_id', '=', account.id),
            ('whatsapp_number', '=', phone),
        ], limit=1)
        if not channel:
            # Find the most recent inbound mail.message for this session to use
            # as related_message so _get_whatsapp_channel can resolve record_name.
            # Fall back to creating without a related_message to avoid AttributeError.
            session_mail_msg = self.env['mail.message'].sudo().search([
                ('model', '=', 'wa.chatbot.session'),
                ('res_id', '=', session.id),
            ], limit=1, order='id desc')
            related_message = session_mail_msg if session_mail_msg else False
            channel = Channel._get_whatsapp_channel(
                whatsapp_number=phone,
                wa_account_id=account,
                sender_name=partner.name if partner else phone,
                create_if_not_found=True,
                related_message=related_message,
            )

        # Ensure bot partner is a member (the whatsapp_partner and responsibles
        # are already added by _get_whatsapp_channel; we just add the chatbot owner).
        if bot_partner and bot_partner not in channel.channel_member_ids.mapped('partner_id'):
            channel.add_members(partner_ids=bot_partner.ids)

        # 4. Tag the channel with chatbot context (our own fields from the inherit)
        context_data = self._build_handoff_context(session, cfg)
        partner_name = partner.name or phone
        account_name = account.name or "WhatsApp"
        new_name = f"{partner_name}({account_name})"

        channel.write({
            'name': new_name,
            'chatbot_handoff': True,
            'chatbot_session_id': session.id,
            'chatbot_context': json.dumps(context_data, ensure_ascii=False),
        })

        # 5. Replay the conversation history as internal notes so the agent has
        #    context. Using message_type='comment' + mail.mt_note keeps these
        #    from triggering the enterprise whatsapp send path (which fires on
        #    message_type='whatsapp_message').
        try:
            self._post_conversation_history(session, channel, partner, bot_partner)
        except Exception as e:
            _logger.exception("Handoff: failed to post conversation history: %s", e)

        try:
            summary_html = self._build_handoff_summary_html(session, cfg, context_data)
            channel.message_post(
                body=summary_html,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        except Exception as e:
            _logger.exception("Handoff: failed to post summary note: %s", e)

        # 6. Update session state — always runs, even if channel operations failed
        reason = cfg.get('reason', '') or 'Chatbot handoff'
        session.write({
            'state': 'handed_off',
            'handoff_channel_id': channel.id,
            'handoff_reason': reason,
        })

        self._log_session_message(session, 'system', 'Handed off to human agent', msg_type='system')

    def _post_conversation_history(self, session, channel, partner, bot_partner):
        """Post the entire chatbot conversation as internal notes in the Discuss channel.

        Uses message_type='comment' with subtype mail.mt_note so the enterprise
        whatsapp override (which sends outbound WA for message_type='whatsapp_message')
        doesn't replay these messages back to Meta.
        """
        all_logs = session.log_ids.sorted('timestamp')
        if not all_logs:
            return

        for log in all_logs:
            if log.direction == 'system':
                continue
            body = log.body or ''
            if not body:
                continue
            is_customer = (log.direction == 'inbound')
            author = partner if is_customer else bot_partner
            prefix = 'Customer: ' if is_customer else 'Bot: '
            try:
                channel.message_post(
                    body=f"{prefix}{body}",
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                    author_id=author.id if author else False,
                )
            except Exception as e:
                _logger.warning("Handoff: failed to post log entry %s: %s", log.id, e)

    def _build_handoff_context(self, session, cfg):
        variables = session.get_variables()

        duration_minutes = 0
        if session.started_at:
            delta = fields.Datetime.now() - session.started_at
            duration_minutes = round(delta.total_seconds() / 60, 1)

        context = {
            'session_id': session.id,
            'chatbot_name': session.chatbot_id.name or '',
            'flow_name': session.current_flow_id.name if session.current_flow_id else '',
            'phone': session.phone,
            'contact_name': session.partner_id.name if session.partner_id else '',
            'started_at': str(session.started_at) if session.started_at else '',
            'duration_minutes': duration_minutes,
            'message_count': session.message_count or 0,
            'fallback_count': session.fallback_count or 0,
            'handoff_reason': cfg.get('reason', '') or 'Chatbot handoff',
            'priority': cfg.get('priority', 'normal'),
            'collected_info': {},
            'conversation': [],
        }

        system_keys = {'session_id', 'message_count', 'last_input', 'fallback_count', 'partner_id'}
        for key, val in variables.items():
            if key not in system_keys and val:
                context['collected_info'][key] = val

        for log in session.log_ids.sorted('timestamp'):
            if log.direction == 'system':
                continue
            context['conversation'].append({
                'direction': 'User' if log.direction == 'inbound' else 'Bot',
                'body': log.body or '',
                'type': log.message_type or 'text',
                'time': str(log.timestamp) if log.timestamp else '',
            })

        return context

    def _build_handoff_summary_html(self, session, cfg, context_data):
        priority = cfg.get('priority', 'normal')
        priority_colors = {'normal': '#17a2b8', 'high': '#fd7e14', 'urgent': '#dc3545'}
        priority_color = priority_colors.get(priority, '#17a2b8')

        parts = []
        parts.append(
            '<div style="border-left: 4px solid %s; padding: 8px 12px; margin-bottom: 12px; '
            'background: #f8f9fa; border-radius: 4px;">' % priority_color
        )
        parts.append('<b style="font-size: 14px;">Chatbot Handoff — Conversation transferred to you</b>')
        if priority != 'normal':
            parts.append(
                ' <span style="background: %s; color: white; padding: 2px 8px; '
                'border-radius: 10px; font-size: 11px; text-transform: uppercase;">%s</span>'
                % (priority_color, priority)
            )
        reason = context_data.get('handoff_reason', '')
        if reason and reason != 'Chatbot handoff':
            parts.append('<br/><small style="color: #666;">Reason: %s</small>' % self._html_escape(reason))
        parts.append('</div>')

        parts.append('<div style="margin-bottom: 12px;">')
        parts.append('<b>Session Info</b><br/>')
        parts.append('<table style="font-size: 13px; border-collapse: collapse; width: 100%%;">')
        meta_rows = [
            ('Contact', context_data.get('contact_name', '') or session.phone),
            ('Phone', session.phone),
            ('Chatbot', context_data.get('chatbot_name', '')),
            ('Flow', context_data.get('flow_name', '')),
            ('Duration', '%s min' % context_data.get('duration_minutes', 0)),
            ('Messages', str(context_data.get('message_count', 0))),
        ]
        for label, value in meta_rows:
            if value:
                parts.append(
                    '<tr><td style="padding: 2px 8px 2px 0; color: #666; white-space: nowrap;">'
                    '%s:</td><td style="padding: 2px 0;">%s</td></tr>'
                    % (label, self._html_escape(str(value)))
                )
        parts.append('</table>')
        parts.append('</div>')

        # Centered hyperlink to open the session in Odoo
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        session_url = '%s/odoo/wa.chatbot.session/%s' % (base_url, session.id)
        parts.append(
            '<div style="text-align: center; margin: 16px 0;">'
            '<a href="%s" target="_blank" '
            'style="display: inline-block; padding: 10px 20px; '
            'background-color: #714B67; '
            'color: #ffffff; border-radius: 6px; '
            'text-decoration: none; font-size: 13px; font-weight: 600;">'
            '📋 View Full Session Details'
            '</a>'
            '<br/>'
            '<small style="color: #666; display: block; margin-top: 6px;">'
            'Click to open the complete chatbot session'
            '</small>'
            '</div>' % session_url
        )
        return Markup(''.join(parts))

    @staticmethod
    def _html_escape(text):
        if not text:
            return ''
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))

    # =========================================================================
    # INTERACTIVE PAYLOAD BUILDER
    # =========================================================================

    def _build_interactive_payload(self, cfg, body):
        """Build a Meta-compliant interactive payload from a node config."""
        interactive_type = cfg.get('interactive_type', 'button')
        interactive = {
            'type': interactive_type,
            'body': {'text': body},
        }

        header = cfg.get('header', {})
        if header and header.get('type') not in (None, 'none', ''):
            interactive['header'] = {'type': header['type']}
            if header['type'] == 'text':
                interactive['header']['text'] = header.get('text', '')

        footer = cfg.get('footer', '')
        if footer:
            interactive['footer'] = {'text': footer[:60]}

        if interactive_type == 'button':
            buttons = []
            for btn in cfg.get('buttons', [])[:3]:  # Meta max: 3
                buttons.append({
                    'type': 'reply',
                    'reply': {
                        'id': btn.get('id', ''),
                        'title': btn.get('title', '')[:20],  # Meta max: 20 chars
                    },
                })
            interactive['action'] = {'buttons': buttons}

        elif interactive_type == 'list':
            sections = []
            for section in cfg.get('sections', [])[:10]:
                rows = []
                for row in section.get('rows', []):
                    row_data = {
                        'id': row.get('id', ''),
                        'title': row.get('title', '')[:24],
                    }
                    if row.get('description'):
                        row_data['description'] = row['description'][:72]
                    rows.append(row_data)
                sections.append({
                    'title': section.get('title', ''),
                    'rows': rows,
                })
            interactive['action'] = {
                'button': cfg.get('button_text', 'Select')[:20],
                'sections': sections,
            }

        return interactive

    # =========================================================================
    # VARIABLE RESOLUTION / DOMAIN / TYPE COERCION
    # =========================================================================

    @staticmethod
    def _coerce_field_value(value, ttype, Model, field_name):
        if not ttype and field_name in Model._fields:
            ttype = Model._fields[field_name].type
        if not ttype:
            return value

        if ttype in ('integer', 'many2one'):
            try:
                return int(float(value)) if value else False
            except (ValueError, TypeError):
                return False
        if ttype in ('float', 'monetary'):
            try:
                return float(value) if value else 0.0
            except (ValueError, TypeError):
                return 0.0
        if ttype == 'boolean':
            return str(value).lower().strip() in ('true', '1', 'yes')
        if ttype == 'date':
            if not value:
                return False
            try:
                return fields.Date.to_date(value)
            except Exception:
                for fmt in ('%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
                    try:
                        return datetime.strptime(value, fmt).date()
                    except ValueError:
                        pass
                return False
        if ttype == 'datetime':
            if not value:
                return False
            try:
                return fields.Datetime.to_datetime(value)
            except Exception:
                for fmt in ('%d-%m-%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        pass
                return False
        if ttype == 'selection':
            return value if value else False
        return value

    def _resolve_variables(self, session, text):
        """Replace {{variable_name}} placeholders with session variable values."""
        if not text:
            return text

        def replacer(match):
            var_name = match.group(1).strip()
            variables = session.get_variables()
            if var_name in variables:
                return str(variables[var_name])
            if var_name == 'date':
                return str(fields.Date.today())
            if var_name == 'time':
                return fields.Datetime.now().strftime('%H:%M')
            if var_name == 'datetime':
                return str(fields.Datetime.now())
            return match.group(0)

        return re_module.sub(r'\{\{(\w+)\}\}', replacer, text).replace('\\n', '\n')

    @staticmethod
    def _extract_json_path(data, path):
        """Extract a value from parsed JSON via dot notation, e.g.
        'data.items.0.name'. A leading JSONPath-style '$.' or '$' root is
        ignored. List indices are integers in the path. Returns None if the
        path doesn't resolve.
        """
        if not path or data is None:
            return data
        path = path.strip()
        if path.startswith('$.'):
            path = path[2:]
        elif path.startswith('$'):
            path = path[1:]
        path = path.lstrip('.')
        if not path:
            return data
        current = data
        for part in path.split('.'):
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
            if current is None:
                return None
        return current

    # =========================================================================
    # LOGGING
    # =========================================================================

    def _log_session_message(self, session, direction, body, node_id=None,
                             wa_msg=None, msg_type='text', wamid=None, account=None):
        """Create a session log entry and (for inbound) an audit whatsapp.message."""
        Log = self.env['wa.chatbot.session.log'].sudo()
        Log.create({
            'session_id': session.id,
            'direction': direction,
            'message_type': msg_type,
            'body': body,
            'node_id': node_id,
            'wa_message_id': wa_msg.id if wa_msg else False,
            'variables_snapshot': session.variables,
        })

        # For inbound, also create a whatsapp.message audit trail — the stock
        # _process_messages path (which creates this normally) didn't run
        # because we consumed the webhook.
        if direction == 'inbound' and wamid and account:
            safe_type = msg_type if msg_type in _LOGGABLE_INBOUND_TYPES else 'text'
            send_helpers.log_inbound(
                self.env, account, session.phone, wamid, body,
                session=session, message_type=safe_type,
            )

    def _log_inbound_message(self, account, phone, wamid, msg_type, body):
        """Log an inbound message without creating a session (e.g. outside working hours)."""
        if not wamid:
            return
        send_helpers.log_inbound(self.env, account, phone, wamid, body, session=None)
