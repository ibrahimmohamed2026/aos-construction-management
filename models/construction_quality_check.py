# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ConstructionQualityCheck(models.Model):
    _name = 'construction.quality.check'
    _description = 'Quality Check'
    _inherit = ['mail.thread']

    name = fields.Char(required=True)
    ref = fields.Char(readonly=True, default='New')
    project_id = fields.Many2one('construction.project', required=True)
    work_order_id = fields.Many2one('construction.work.order', domain="[('project_id','=',project_id)]")
    wbs_id = fields.Many2one('construction.wbs', domain="[('project_id','=',project_id)]")
    check_date = fields.Date(default=fields.Date.today)
    inspector_id = fields.Many2one('res.users', string='Inspector')
    check_type = fields.Selection([
        ('material', 'Material Inspection'),
        ('workmanship', 'Workmanship'),
        ('structural', 'Structural'),
        ('safety', 'Safety'),
        ('final', 'Final Inspection'),
    ], default='workmanship')
    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('conditional', 'Conditional Pass'),
    ], tracking=True)
    remarks = fields.Text()
    corrective_action = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='draft', tracking=True)
    checklist_ids = fields.One2many('construction.quality.checklist', 'check_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ref', 'New') == 'New':
                vals['ref'] = self.env['ir.sequence'].next_by_code('construction.quality.check') or 'New'
        return super().create(vals_list)

    def action_start(self):
        self.state = 'in_progress'

    def action_pass(self):
        self.write({'state': 'completed', 'result': 'pass'})

    def action_fail(self):
        self.write({'state': 'failed', 'result': 'fail'})

    def action_reset(self):
        self.state = 'draft'


class ConstructionQualityChecklist(models.Model):
    _name = 'construction.quality.checklist'
    _description = 'Quality Checklist Item'

    check_id = fields.Many2one('construction.quality.check', ondelete='cascade')
    description = fields.Char(required=True)
    is_checked = fields.Boolean()
    remarks = fields.Char()
