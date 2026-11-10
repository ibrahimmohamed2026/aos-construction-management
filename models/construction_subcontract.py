# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ConstructionSubcontract(models.Model):
    _name = 'construction.subcontract'
    _description = 'Subcontract'
    _inherit = ['mail.thread']

    name = fields.Char(required=True)
    ref = fields.Char(readonly=True, default='New')
    project_id = fields.Many2one('construction.project', required=True)
    wbs_id = fields.Many2one('construction.wbs', domain="[('project_id','=',project_id)]")
    subcontractor_id = fields.Many2one('res.partner', string='Subcontractor', required=True)
    scope_of_work = fields.Text()
    contract_value = fields.Monetary(currency_field='currency_id')
    amount_paid = fields.Monetary(currency_field='currency_id')
    amount_remaining = fields.Monetary(compute='_compute_remaining', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='project_id.currency_id')
    start_date = fields.Date()
    end_date = fields.Date()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
    ], default='draft', tracking=True)
    payment_terms = fields.Text()
    retention_percent = fields.Float('Retention %', default=10.0)
    retention_amount = fields.Monetary(compute='_compute_retention', currency_field='currency_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code('construction.subcontract') or 'New'
        return super().create(vals_list)

    @api.depends('contract_value', 'amount_paid')
    def _compute_remaining(self):
        for rec in self:
            rec.amount_remaining = rec.contract_value - rec.amount_paid

    @api.depends('contract_value', 'retention_percent')
    def _compute_retention(self):
        for rec in self:
            rec.retention_amount = rec.contract_value * (rec.retention_percent / 100)

    def action_activate(self):
        self.state = 'active'

    def action_complete(self):
        self.state = 'completed'

    def action_terminate(self):
        self.state = 'terminated'

    def action_reset(self):
        self.state = 'draft'
