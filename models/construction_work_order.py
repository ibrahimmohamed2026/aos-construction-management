# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ConstructionWorkOrder(models.Model):
    _name = 'construction.work.order'
    _description = 'Work Order'
    _inherit = ['mail.thread']

    name = fields.Char(required=True)
    ref = fields.Char(readonly=True, default='New')
    project_id = fields.Many2one('construction.project', required=True)
    wbs_id = fields.Many2one('construction.wbs', string='WBS Phase', domain="[('project_id','=',project_id)]")
    foreman_id = fields.Many2one('res.users', string='Foreman')
    planned_start = fields.Date()
    planned_end = fields.Date()
    actual_start = fields.Date()
    actual_end = fields.Date()
    description = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)
    material_requisition_ids = fields.One2many('construction.material.requisition', 'work_order_id')
    planned_cost = fields.Monetary(currency_field='currency_id')
    actual_cost = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='project_id.currency_id')
    priority = fields.Selection([('0', 'Normal'), ('1', 'High'), ('2', 'Urgent')], default='0')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code('construction.work.order') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        self.state = 'confirmed'

    def action_start(self):
        self.write({'state': 'in_progress', 'actual_start': fields.Date.today()})

    def action_done(self):
        self.write({'state': 'done', 'actual_end': fields.Date.today()})

    def action_cancel(self):
        self.state = 'cancelled'

    def action_reset(self):
        self.state = 'draft'
