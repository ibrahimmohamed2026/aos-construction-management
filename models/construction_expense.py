# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ConstructionExpense(models.Model):
    _name = 'construction.expense'
    _description = 'Construction Expense'
    _inherit = ['mail.thread']

    name = fields.Char(required=True)
    ref = fields.Char(readonly=True, default='New')
    project_id = fields.Many2one('construction.project', required=True)
    wbs_id = fields.Many2one('construction.wbs', domain="[('project_id','=',project_id)]")
    date = fields.Date(default=fields.Date.today)
    category = fields.Selection([
        ('material', 'Materials'),
        ('labour', 'Labour'),
        ('equipment', 'Equipment'),
        ('subcontract', 'Subcontract'),
        ('overhead', 'Overhead'),
        ('other', 'Other'),
    ], required=True, default='material')
    amount = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='project_id.currency_id')
    employee_id = fields.Many2one('res.users', string='Incurred By')
    approved_by = fields.Many2one('res.users')
    description = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code('construction.expense') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        self.state = 'submitted'

    def action_approve(self):
        self.write({'state': 'approved', 'approved_by': self.env.user.id})

    def action_reject(self):
        self.state = 'rejected'

    def action_reset(self):
        self.state = 'draft'
