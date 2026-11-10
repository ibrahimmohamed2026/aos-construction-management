# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ConstructionBOQ(models.Model):
    _name = 'construction.boq'
    _description = 'Bill of Quantities'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, default='New BOQ')
    ref = fields.Char(readonly=True, default='New')
    project_id = fields.Many2one('construction.project', required=True, ondelete='cascade')
    date = fields.Date(default=fields.Date.today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('revised', 'Revised'),
    ], default='draft', tracking=True)
    line_ids = fields.One2many('construction.boq.line', 'boq_id', string='BOQ Lines')
    total_amount = fields.Monetary(compute='_compute_total', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='project_id.currency_id')
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code('construction.boq') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    def action_approve(self):
        self.state = 'approved'

    def action_revise(self):
        self.state = 'revised'

    def action_reset(self):
        self.state = 'draft'

    def action_print_boq(self):
        return self.env.ref('aos_construction_management.action_report_boq').report_action(self)


class ConstructionBOQLine(models.Model):
    _name = 'construction.boq.line'
    _description = 'BOQ Line'
    _order = 'sequence, id'

    boq_id = fields.Many2one('construction.boq', ondelete='cascade')
    sequence = fields.Integer(default=10)
    item_no = fields.Char('Item No.')
    description = fields.Char(required=True)
    work_type = fields.Selection([
        ('civil', 'Civil'),
        ('structural', 'Structural'),
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing/MEP'),
        ('finishing', 'Finishing'),
        ('external', 'External Works'),
        ('other', 'Other'),
    ], default='civil')
    uom_id = fields.Many2one('uom.uom', string='UOM')
    qty = fields.Float(digits=(12, 3))
    unit_rate = fields.Monetary(currency_field='currency_id')
    amount = fields.Monetary(compute='_compute_amount', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='boq_id.currency_id')
    wbs_id = fields.Many2one('construction.wbs', string='WBS Phase')
    is_section = fields.Boolean('Section Header')

    @api.depends('qty', 'unit_rate', 'is_section')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.qty * rec.unit_rate if not rec.is_section else 0.0
