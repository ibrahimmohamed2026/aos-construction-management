# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ConstructionProject(models.Model):
    _name = 'construction.project'
    _description = 'Construction Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    ref = fields.Char('Project Code', readonly=True, default='New')
    client_id = fields.Many2one('res.partner', string='Client', tracking=True)
    site_manager_id = fields.Many2one('res.users', string='Site Manager')
    project_manager_id = fields.Many2one('res.users', string='Project Manager')
    start_date = fields.Date()
    end_date = fields.Date()
    contract_value = fields.Monetary(currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)
    location = fields.Char()
    description = fields.Text()

    # Smart button counts
    boq_count = fields.Integer(compute='_compute_counts')
    wbs_count = fields.Integer(compute='_compute_counts')
    work_order_count = fields.Integer(compute='_compute_counts')
    material_requisition_count = fields.Integer(compute='_compute_counts')
    subcontract_count = fields.Integer(compute='_compute_counts')
    billing_count = fields.Integer(compute='_compute_counts')
    quality_check_count = fields.Integer(compute='_compute_counts')
    expense_count = fields.Integer(compute='_compute_counts')

    total_billed = fields.Monetary(compute='_compute_financials', currency_field='currency_id')
    total_expenses = fields.Monetary(compute='_compute_financials', currency_field='currency_id')
    progress = fields.Float(compute='_compute_progress', string='Overall Progress %')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code('construction.project') or 'New'
        return super().create(vals_list)

    def _compute_counts(self):
        for rec in self:
            rec.boq_count = self.env['construction.boq'].search_count([('project_id', '=', rec.id)])
            rec.wbs_count = self.env['construction.wbs'].search_count([('project_id', '=', rec.id)])
            rec.work_order_count = self.env['construction.work.order'].search_count([('project_id', '=', rec.id)])
            rec.material_requisition_count = self.env['construction.material.requisition'].search_count([('project_id', '=', rec.id)])
            rec.subcontract_count = self.env['construction.subcontract'].search_count([('project_id', '=', rec.id)])
            rec.billing_count = self.env['construction.ra.billing'].search_count([('project_id', '=', rec.id)])
            rec.quality_check_count = self.env['construction.quality.check'].search_count([('project_id', '=', rec.id)])
            rec.expense_count = self.env['construction.expense'].search_count([('project_id', '=', rec.id)])

    def _compute_financials(self):
        for rec in self:
            billings = self.env['construction.ra.billing'].search([('project_id', '=', rec.id), ('state', '=', 'approved')])
            rec.total_billed = sum(billings.mapped('total_amount'))
            expenses = self.env['construction.expense'].search([('project_id', '=', rec.id), ('state', '=', 'approved')])
            rec.total_expenses = sum(expenses.mapped('amount'))

    def _compute_progress(self):
        for rec in self:
            wbs = self.env['construction.wbs'].search([('project_id', '=', rec.id)])
            rec.progress = sum(wbs.mapped('progress')) / len(wbs) if wbs else 0.0

    def action_activate(self):
        self.state = 'active'

    def action_hold(self):
        self.state = 'on_hold'

    def action_complete(self):
        self.state = 'completed'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_reset(self):
        self.state = 'draft'

    def action_view_boq(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'BOQ',
            'res_model': 'construction.boq',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_wbs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'WBS Phases',
            'res_model': 'construction.wbs',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_work_orders(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Work Orders',
            'res_model': 'construction.work.order',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_requisitions(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Material Requisitions',
            'res_model': 'construction.material.requisition',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_subcontracts(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Subcontracts',
            'res_model': 'construction.subcontract',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_billing(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'RA Billing',
            'res_model': 'construction.ra.billing',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_quality(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quality Checks',
            'res_model': 'construction.quality.check',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_expenses(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Expenses',
            'res_model': 'construction.expense',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
