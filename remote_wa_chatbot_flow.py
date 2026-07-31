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

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
from odoo.addons.dev_whatsapp_chatbot_ent.data.demo_real_estate_data import (
    load_demo_real_estate_chatbot,
)

_logger = logging.getLogger(__name__)


class WaChatbotFlow(models.Model):
    _name = 'wa.chatbot.flow'
    _description = 'Chatbot Conversation Flow'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    chatbot_id = fields.Many2one(
        'wa.chatbot',
        required=True,
        ondelete='cascade',
    )
    description = fields.Text()
    is_default = fields.Boolean(
        string="Default Flow",
        help="Entry-point flow when bot starts.",
    )
    sequence = fields.Integer(default=10)

    # Graph data
    node_ids = fields.One2many('wa.chatbot.node', 'flow_id', string="Nodes")
    edge_ids = fields.One2many('wa.chatbot.edge', 'flow_id', string="Edges")
    variable_ids = fields.One2many('wa.chatbot.variable', 'flow_id', string="Variables")

    # Canvas UI state (positions, viewport, zoom)
    canvas_data = fields.Text(
        default='{}',
        string="Canvas Data",
        help="JSON with viewport position, zoom level, and grid settings.",
    )

    # Versioning
    version = fields.Integer(default=1)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('published', 'Published'),
        ],
        default='draft',
    )

    node_count = fields.Integer(compute='_compute_node_count', string="Nodes")
    edge_count = fields.Integer(compute='_compute_edge_count', string="Edges")

    company_id = fields.Many2one(
        'res.company',
        related='chatbot_id.company_id',
        store=True,
    )

    # -------------------------------------------------------------------------
    # COMPUTE
    # -------------------------------------------------------------------------
    def _compute_node_count(self):
        for rec in self:
            rec.node_count = len(rec.node_ids)

    def _compute_edge_count(self):
        for rec in self:
            rec.edge_count = len(rec.edge_ids)

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------
    def action_publish(self):
        self.ensure_one()
        start_nodes = self.node_ids.filtered(lambda n: n.is_entry)
        if not start_nodes:
            raise UserError(_("Flow must have at least one Start node before publishing."))
        self.write({
            'state': 'published',
            'version': self.version + 1,
        })
        # Auto-set as default if no default flow on chatbot
        if not self.chatbot_id.default_flow_id:
            self.chatbot_id.default_flow_id = self.id

    def action_reset_draft(self):
        self.ensure_one()
        self.state = 'draft'

    def action_open_canvas(self):
        """Open the visual flow builder canvas."""
        self.ensure_one()
        action = self.env['ir.actions.client']._for_xml_id(
            'dev_whatsapp_chatbot_ent.action_wa_chatbot_canvas'
        )
        action['name'] = _("Flow Builder: %s", self.name)
        action['params'] = {
            'flow_id': self.id,
            'chatbot_id': self.chatbot_id.id,
        }
        return action

    def action_duplicate_flow(self):
        self.ensure_one()
        new_flow = self.copy({'name': _("%s (Copy)", self.name), 'state': 'draft', 'version': 1})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wa.chatbot.flow',
            'res_id': new_flow.id,
            'view_mode': 'form',
        }

    # -------------------------------------------------------------------------
    # CANVAS DATA (Save / Load for JS)
    # -------------------------------------------------------------------------
    def get_flow_data(self):
        """Return complete flow data for the canvas JS component."""
        self.ensure_one()
        nodes = []
        for node in self.node_ids:
            nodes.append({
                'id': node.id,
                'name': node.name,
                'node_type': node.node_type,
                'config': json.loads(node.config or '{}'),
                'position_x': node.position_x,
                'position_y': node.position_y,
                'is_entry': node.is_entry,
                'sequence': node.sequence,
                'user_id': node.user_id.id if node.user_id else False,
                'user_name': node.user_id.name if node.user_id else '',
            })
        edges = []
        for edge in self.edge_ids:
            edges.append({
                'id': edge.id,
                'source_node_id': edge.source_node_id.id,
                'target_node_id': edge.target_node_id.id,
                'source_handle': edge.source_handle,
                'label': edge.label,
                'sequence': edge.sequence,
                'condition_type': edge.condition_type,
            })
        variables = []
        for var in self.variable_ids:
            variables.append({
                'id': var.id,
                'name': var.name,
                'variable_type': var.variable_type,
                'default_value': var.default_value,
                'scope': var.scope,
                'is_system': var.is_system,
                'description': var.description,
            })
        # Sibling flows (same chatbot) for GoTo node dropdowns
        sibling_flows = []
        for flow in self.chatbot_id.flow_ids:
            sibling_flows.append({
                'id': flow.id,
                'name': flow.name,
            })

        # WhatsApp templates (same account) for Template node dropdown
        wa_templates = []
        account = self.chatbot_id.account_id
        if account:
            for tmpl in self.env['whatsapp.template'].search([
                ('wa_account_id', '=', account.id),
                ('status', '=', 'approved'),
            ], order='name'):
                wa_templates.append({
                    'id': tmpl.id,
                    'name': tmpl.name,
                })

        # Internal users for handoff node user assignment dropdown
        available_users = []
        for user in self.env['res.users'].search([
            ('share', '=', False),
        ], order='name'):
            available_users.append({
                'id': user.id,
                'name': user.name,
            })

        return {
            'flow': {
                'id': self.id,
                'name': self.name,
                'state': self.state,
                'version': self.version,
                'canvas_data': json.loads(self.canvas_data or '{}'),
            },
            'nodes': nodes,
            'edges': edges,
            'variables': variables,
            'sibling_flows': sibling_flows,
            'wa_templates': wa_templates,
            'available_users': available_users,
        }

    def save_flow_data(self, data):
        """Save canvas data from JS component back to database.

        Performs a full sync: creates/updates/deletes nodes and edges
        to match the incoming data from the canvas editor.
        """
        self.ensure_one()
        Node = self.env['wa.chatbot.node']
        Edge = self.env['wa.chatbot.edge']

        # Save canvas viewport data
        canvas_data = data.get('canvas_data', {})
        self.canvas_data = json.dumps(canvas_data)

        # --- Sync nodes ---
        # Separate existing nodes (positive IDs) from new nodes (negative temp IDs)
        existing_updates = {}
        new_nodes = []
        for n in data.get('nodes', []):
            nid = n.get('id')
            if isinstance(nid, int) and nid > 0:
                existing_updates[nid] = n
            else:
                new_nodes.append(n)

        existing_node_ids = set(self.node_ids.ids)

        # Delete nodes removed from canvas
        to_delete = existing_node_ids - set(existing_updates.keys())
        if to_delete:
            Node.browse(list(to_delete)).unlink()

        # Update existing nodes
        for node_id, ndata in existing_updates.items():
            if node_id in existing_node_ids:
                node = Node.browse(node_id)
                config_val = ndata.get('config', {})
                if isinstance(config_val, dict):
                    config_val = json.dumps(config_val, ensure_ascii=False)
                vals = {
                    'name': ndata.get('name', node.name),
                    'node_type': ndata.get('node_type', node.node_type),
                    'config': config_val,
                    'position_x': ndata.get('position_x', node.position_x),
                    'position_y': ndata.get('position_y', node.position_y),
                    'is_entry': ndata.get('is_entry', node.is_entry),
                    'sequence': ndata.get('sequence', node.sequence),
                }
                if 'user_id' in ndata:
                    vals['user_id'] = ndata['user_id'] or False
                node.write(vals)

        # Create new nodes (map temp IDs to real IDs)
        id_map = {}
        for ndata in new_nodes:
            temp_id = ndata.get('id', 0)
            config_val = ndata.get('config', {})
            if isinstance(config_val, dict):
                config_val = json.dumps(config_val, ensure_ascii=False)
            create_vals = {
                'name': ndata.get('name', 'New Node'),
                'flow_id': self.id,
                'node_type': ndata.get('node_type', 'send_message'),
                'config': config_val,
                'position_x': ndata.get('position_x', 0),
                'position_y': ndata.get('position_y', 0),
                'is_entry': ndata.get('is_entry', False),
                'sequence': ndata.get('sequence', 10),
            }
            if ndata.get('user_id'):
                create_vals['user_id'] = ndata['user_id']
            new_node = Node.create(create_vals)
            id_map[temp_id] = new_node.id

        # --- Sync edges ---
        # Delete all existing edges and recreate (simpler and avoids complex diffing)
        self.edge_ids.unlink()
        for edata in data.get('edges', []):
            source_id = edata.get('source_node_id')
            target_id = edata.get('target_node_id')
            # Resolve temp IDs
            if source_id in id_map:
                source_id = id_map[source_id]
            if target_id in id_map:
                target_id = id_map[target_id]
            # Validate that both nodes exist
            if not source_id or not target_id:
                _logger.warning("Skipping edge with invalid IDs: source=%s target=%s", source_id, target_id)
                continue
            # Also skip if node IDs are negative (unresolved temp IDs)
            if (isinstance(source_id, int) and source_id < 0) or (isinstance(target_id, int) and target_id < 0):
                _logger.warning("Skipping edge with unresolved temp IDs: source=%s target=%s", source_id, target_id)
                continue
            Edge.create({
                'flow_id': self.id,
                'source_node_id': source_id,
                'target_node_id': target_id,
                'source_handle': edata.get('source_handle', 'default'),
                'label': edata.get('label', ''),
                'sequence': edata.get('sequence', 10),
                'condition_type': edata.get('condition_type', 'always'),
            })

        return self.get_flow_data()

    @api.model
    def _ensure_builder_access(self):
        """Guard for the flow-builder RPCs below.

        These methods introspect the model/field catalog (sudo) so the builder
        can offer model/field pickers. Only flow builders (chatbot managers)
        should reach them — otherwise a read-only chatbot user could enumerate
        models/fields via RPC.
        """
        if not self.env.user.has_group('dev_whatsapp_chatbot_ent.group_chatbot_manager'):
            raise AccessError(_("Only Chatbot Managers may use the flow builder tools."))

    @api.model
    def get_available_models(self):
        """Return list of models available for create/update record actions."""
        self._ensure_builder_access()
        IrModel = self.env['ir.model'].sudo()
        models = IrModel.search([('transient', '=', False)], order='name')
        return [
            {'model': m.model, 'name': m.name}
            for m in models
        ]

    @api.model
    def get_model_fields(self, model_name):
        """Return writable fields for a given model, sorted by name.

        Used by the create_record / update_record actions, which can only set
        simple, writable fields — hence the readonly / x2many / binary filtering.
        For the search_record builder use get_search_fields() instead.
        """
        self._ensure_builder_access()
        if not model_name or model_name not in self.env:
            return []
        IrModelFields = self.env['ir.model.fields'].sudo()
        domain = [
            ('model', '=', model_name),
            ('store', '=', True),
            ('readonly', '=', False),
            ('ttype', 'not in', ['one2many', 'many2many', 'binary', 'reference']),
        ]
        flds = IrModelFields.search(domain, order='field_description')
        return [
            {
                'name': f.name,
                'string': f.field_description,
                'ttype': f.ttype,
                'required': f.required,
                'relation': f.relation or '',
            }
            for f in flds
        ]

    @api.model
    def get_search_fields(self, model_name):
        """Return ALL fields of a model for the search_record builder.

        Distinct from get_model_fields (create/update → writable only): search
        needs to read AND filter on the full field set — including readonly,
        computed, and relational fields — so we apply no restrictive conditions.
        Only binary is dropped (a blob can't be searched or rendered as text).
        Each field carries `store` so the UI can tell searchable (stored) fields
        from display-only (non-stored) ones.
        """
        self._ensure_builder_access()
        if not model_name or model_name not in self.env:
            return []
        IrModelFields = self.env['ir.model.fields'].sudo()
        flds = IrModelFields.search([
            ('model', '=', model_name),
            ('ttype', '!=', 'binary'),
        ], order='field_description')
        return [
            {
                'name': f.name,
                'string': f.field_description,
                'ttype': f.ttype,
                'required': f.required,
                'relation': f.relation or '',
                'store': f.store,
            }
            for f in flds
        ]

    def export_flow_json(self):
        """Export flow as a portable JSON structure (for import/export)."""
        self.ensure_one()
        data = self.get_flow_data()
        return json.dumps(data, indent=2, ensure_ascii=False)

    @api.model
    def load_demo_real_estate_chatbot(self, account_id=None):
        """Load the complete Dream Home Realty demo chatbot.

        Creates a production-ready chatbot for a real estate business that
        demonstrates ALL 12 node types across 3 interconnected flows:

        Flow 1 - Main Menu:
            Start → Input (ask name) → Send Message (welcome) →
            Interactive Buttons (menu) → Action (set variable) →
            GoTo (jump to property/visit flow) or Handoff (agent)

        Flow 2 - Property Search:
            Start → Interactive List Menu (9 property types in 3 sections) →
            Action (save type) → Input (location) → Interactive Buttons (budget) →
            Condition (3 branches by budget) → API Call (fetch listings) →
            Delay (searching...) → Send Message (results) →
            Input (email validation) → Interactive Buttons (what next) →
            GoTo (visit flow) / Handoff (agent) / Close (goodbye)

        Flow 3 - Site Visit Booking:
            Start → Send Message (intro) → Input (phone validation) →
            Input (date validation) → Interactive Buttons (time slot) →
            Action (save time) → Input (notes) → Send Message (summary) →
            Interactive Buttons (confirm y/n) → Condition (check) →
            Template (confirmation) → Delay → Send Message (confirmed) → Close
            OR → Send Message (cancelled) → GoTo (restart from Ask Phone)

        Usage from Odoo Shell:
            env['wa.chatbot.flow'].load_demo_real_estate_chatbot()
            # or with specific account:
            env['wa.chatbot.flow'].load_demo_real_estate_chatbot(account_id=1)

        Args:
            account_id: whatsapp.account record ID (optional, uses first available)

        Returns:
            dict: action to open the created chatbot form
        """
        
        chatbot = load_demo_real_estate_chatbot(self.env, account_id=account_id)
        return {
            'type': 'ir.actions.act_window',
            'name': chatbot.name,
            'res_model': 'wa.chatbot',
            'res_id': chatbot.id,
            'view_mode': 'form',
        }
