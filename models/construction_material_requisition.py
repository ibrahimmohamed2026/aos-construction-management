# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ConstructionMaterialRequisition(models.Model):
    _name = 'construction.material.requisition'
    _description = 'Material Requisition'
    _inherit = ['mail.thread']

    name = fields.Char(required=True)
    ref = fields.Char(readonly=True, default='New')
    project_id = fields.Many2one('construction.project', required=True)
    work_order_id = fields.Many2one('construction.work.order', domain="[('project_id','=',project_id)]")
    date_requested = fields.Date(default=fields.Date.today)
    date_required = fields.Date()
    requested_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    approved_by = fields.Many2one('res.users')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)
    line_ids = fields.One2many('construction.material.requisition.line', 'requisition_id')
    total_estimated_cost = fields.Monetary(compute='_compute_total', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='project_id.currency_id')
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code('construction.material.requisition') or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.subtotal')
    def _compute_total(self):
        for rec in self:
            rec.total_estimated_cost = sum(rec.line_ids.mapped('subtotal'))

    def action_submit(self):
        self.state = 'submitted'

    def action_approve(self):
        self.write({'state': 'approved', 'approved_by': self.env.user.id})

    def action_receive(self):
        self.state = 'received'

    def action_cancel(self):
        self.state = 'cancelled'

    def action_reset(self):
        self.state = 'draft'


class ConstructionMaterialRequisitionLine(models.Model):
    _name = 'construction.material.requisition.line'
    _description = 'Material Requisition Line'

    requisition_id = fields.Many2one('construction.material.requisition', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Material')
    description = fields.Char()
    uom_id = fields.Many2one('uom.uom', string='UOM')
    qty_requested = fields.Float(digits=(12, 3))
    qty_approved = fields.Float(digits=(12, 3))
    qty_received = fields.Float(digits=(12, 3))
    unit_price = fields.Monetary(currency_field='currency_id')
    subtotal = fields.Monetary(compute='_compute_subtotal', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='requisition_id.currency_id')

    @api.depends('qty_requested', 'unit_price')
    def _compute_subtotal(self):
        for rec in self:
            rec.subtotal = rec.qty_requested * rec.unit_price

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name
            self.uom_id = self.product_id.uom_id
            self.unit_price = self.product_id.standard_price
