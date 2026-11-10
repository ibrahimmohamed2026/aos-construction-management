# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ConstructionRABilling(models.Model):
    _name = 'construction.ra.billing'
    _description = 'Running Account Billing'
    _inherit = ['mail.thread']

    name = fields.Char(required=True)
    ref = fields.Char(readonly=True, default='New')
    ra_number = fields.Integer('RA No.', readonly=True)
    project_id = fields.Many2one('construction.project', required=True)
    billing_date = fields.Date(default=fields.Date.today)
    billing_period_start = fields.Date()
    billing_period_end = fields.Date()
    line_ids = fields.One2many('construction.ra.billing.line', 'billing_id')
    total_amount = fields.Monetary(compute='_compute_total', store=True, currency_field='currency_id')
    previous_billed = fields.Monetary(currency_field='currency_id')
    net_amount = fields.Monetary(compute='_compute_net', store=True, currency_field='currency_id')
    retention_percent = fields.Float('Retention %', default=5.0)
    retention_amount = fields.Monetary(compute='_compute_retention', store=True, currency_field='currency_id')
    net_payable = fields.Monetary(compute='_compute_payable', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='project_id.currency_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    ], default='draft', tracking=True)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code('construction.ra.billing') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    @api.depends('total_amount', 'previous_billed')
    def _compute_net(self):
        for rec in self:
            rec.net_amount = rec.total_amount - rec.previous_billed

    @api.depends('net_amount', 'retention_percent')
    def _compute_retention(self):
        for rec in self:
            rec.retention_amount = rec.net_amount * (rec.retention_percent / 100)

    @api.depends('net_amount', 'retention_amount')
    def _compute_payable(self):
        for rec in self:
            rec.net_payable = rec.net_amount - rec.retention_amount

    def action_submit(self):
        self.state = 'submitted'

    def action_approve(self):
        self.state = 'approved'

    def action_pay(self):
        self.state = 'paid'

    def action_reset(self):
        self.state = 'draft'


class ConstructionRABillingLine(models.Model):
    _name = 'construction.ra.billing.line'
    _description = 'RA Billing Line'

    billing_id = fields.Many2one('construction.ra.billing', ondelete='cascade')
    boq_line_description = fields.Char('Description', required=True)
    work_type = fields.Selection([
        ('civil', 'Civil'),
        ('structural', 'Structural'),
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing/MEP'),
        ('finishing', 'Finishing'),
        ('external', 'External Works'),
        ('other', 'Other'),
    ], default='civil')
    uom_id = fields.Many2one('uom.uom')
    boq_qty = fields.Float('BOQ Qty', digits=(12, 3))
    qty_previous = fields.Float('Prev. Qty', digits=(12, 3))
    qty_current = fields.Float('Current Qty', digits=(12, 3))
    qty_cumulative = fields.Float(compute='_compute_cumulative', store=True, digits=(12, 3))
    unit_rate = fields.Monetary(currency_field='currency_id')
    amount = fields.Monetary(compute='_compute_amount', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='billing_id.currency_id')

    @api.depends('qty_previous', 'qty_current')
    def _compute_cumulative(self):
        for rec in self:
            rec.qty_cumulative = rec.qty_previous + rec.qty_current

    @api.depends('qty_current', 'unit_rate')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.qty_current * rec.unit_rate


class ConstructionProgressBilling(models.Model):
    _name = 'construction.progress.billing'
    _description = 'Progress Billing'
    _inherit = ['mail.thread']

    name = fields.Char(required=True)
    ref = fields.Char(readonly=True, default='New')
    project_id = fields.Many2one('construction.project', required=True)
    billing_date = fields.Date(default=fields.Date.today)
    contract_value = fields.Monetary(related='project_id.contract_value', currency_field='currency_id')
    percent_complete = fields.Float('% Complete')
    amount_earned = fields.Monetary(compute='_compute_earned', store=True, currency_field='currency_id')
    amount_previously_billed = fields.Monetary(currency_field='currency_id')
    amount_this_period = fields.Monetary(compute='_compute_this_period', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='project_id.currency_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('invoiced', 'Invoiced'),
    ], default='draft', tracking=True)
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code('construction.progress.billing') or 'New'
        return super().create(vals_list)

    @api.depends('contract_value', 'percent_complete')
    def _compute_earned(self):
        for rec in self:
            rec.amount_earned = rec.contract_value * (rec.percent_complete / 100)

    @api.depends('amount_earned', 'amount_previously_billed')
    def _compute_this_period(self):
        for rec in self:
            rec.amount_this_period = rec.amount_earned - rec.amount_previously_billed

    def action_approve(self):
        self.state = 'approved'

    def action_invoice(self):
        self.state = 'invoiced'

    def action_reset(self):
        self.state = 'draft'
