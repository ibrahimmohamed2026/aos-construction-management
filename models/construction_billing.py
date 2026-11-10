# -*- coding: utf-8 -*-
from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


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
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company, index=True,
    )
    invoice_id = fields.Many2one(
        'account.move', string='Customer Invoice', readonly=True, copy=False,
        domain=[('move_type', '=', 'out_invoice')],
    )
    invoice_state = fields.Selection(related='invoice_id.state', string='Invoice Status', readonly=True)
    invoice_payment_state = fields.Selection(related='invoice_id.payment_state', string='Invoice Payment Status', readonly=True)
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

    @api.depends('total_amount')
    def _compute_net(self):
        for rec in self:
            # Quantities are cumulative: prior certified quantities are removed
            # per BOQ line, so subtracting previous_billed here would double-deduct.
            rec.net_amount = rec.total_amount

    @api.depends('net_amount', 'retention_percent')
    def _compute_retention(self):
        for rec in self:
            rec.retention_amount = rec.net_amount * (rec.retention_percent / 100)

    @api.depends('net_amount', 'retention_amount')
    def _compute_payable(self):
        for rec in self:
            rec.net_payable = rec.net_amount - rec.retention_amount

    def write(self, vals):
        protected_fields = {
            'project_id', 'billing_date', 'billing_period_start',
            'billing_period_end', 'line_ids', 'previous_billed',
            'retention_percent', 'company_id',
        }
        if protected_fields.intersection(vals) and any(self.mapped('invoice_id')):
            raise UserError('Financial details cannot be changed after a customer invoice has been created.')
        return super().write(vals)

    def unlink(self):
        if any(self.mapped('invoice_id')):
            raise UserError('An RA billing linked to a customer invoice cannot be deleted.')
        return super().unlink()

    def action_submit(self):
        self.state = 'submitted'

    def action_approve(self):
        self.state = 'approved'

    def action_create_invoice(self):
        """Create one draft customer invoice for an approved RA billing."""
        self.ensure_one()
        billing = self

        if billing.state != 'approved':
            raise UserError('Only an approved RA billing can be invoiced.')
        if billing.invoice_id:
            return billing.action_view_invoice()
        if not billing.project_id.client_id:
            raise UserError('Set a customer on the construction project before invoicing.')
        if not billing.line_ids:
            raise UserError('Add at least one billing line before creating the invoice.')

        # Serialize invoice creation for this RA record to avoid duplicate invoices
        # when two accounting users click the button at nearly the same time.
        self.env.cr.execute(
            'SELECT id FROM construction_ra_billing WHERE id = %s FOR UPDATE',
            (billing.id,),
        )
        billing.invalidate_recordset(['invoice_id'])
        if billing.invoice_id:
            return billing.action_view_invoice()

        company = billing.company_id
        invoice_lines = []
        for line in billing.line_ids:
            if not line.qty_current:
                continue
            if line.qty_previous < 0 or line.qty_current < line.qty_previous or line.unit_rate < 0:
                raise UserError('Billing quantities and unit rates must not be negative.')
            if not line.revenue_account_id:
                raise UserError(
                    'Select an income account for every non-zero billing line: %s'
                    % line.boq_line_description
                )
            if company not in line.revenue_account_id.company_ids:
                raise UserError(
                    'The income account on "%s" does not belong to the current company.'
                    % line.boq_line_description
                )
            if line.revenue_account_id.account_type not in ('income', 'income_other'):
                raise UserError(
                    'The account on "%s" must be an income account.'
                    % line.boq_line_description
                )

            invalid_taxes = line.tax_ids.filtered(
                lambda tax: tax.company_id != company or tax.type_tax_use != 'sale'
            )
            if invalid_taxes:
                raise UserError(
                    'Only customer taxes belonging to the billing company can be used on "%s".'
                    % line.boq_line_description
                )

            invoice_lines.append(Command.create({
                'name': line.boq_line_description,
                'quantity': line.qty_period,
                'price_unit': line.unit_rate,
                'account_id': line.revenue_account_id.id,
                'tax_ids': [Command.set(line.tax_ids.ids)],
            }))

        if not invoice_lines:
            raise UserError('There are no billing lines with a current quantity to invoice.')

        invoice = self.env['account.move'].with_company(company).create({
            'move_type': 'out_invoice',
            'partner_id': billing.project_id.client_id.id,
            'company_id': company.id,
            'currency_id': billing.currency_id.id,
            'invoice_date': billing.billing_date or fields.Date.context_today(billing),
            'invoice_origin': '%s - %s' % (billing.ref, billing.project_id.name),
            'ref': billing.ref,
            'invoice_line_ids': invoice_lines,
        })
        billing.invoice_id = invoice
        billing.message_post(
            body='Draft customer invoice %s created in Odoo Accounting.'
            % invoice.display_name
        )
        return billing.action_view_invoice()

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError('No customer invoice is linked to this RA billing.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Customer Invoice',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
            'target': 'current',
        }

    def action_pay(self):
        for billing in self:
            if not billing.invoice_id or billing.invoice_id.state != 'posted':
                raise UserError('The linked customer invoice must be posted before payment can be confirmed.')
            if billing.invoice_id.payment_state != 'paid':
                raise UserError('The linked customer invoice is not fully paid in Odoo Accounting.')
            billing.state = 'paid'

    def action_reset(self):
        for billing in self:
            if billing.invoice_id:
                raise UserError('A billing linked to an invoice cannot be reset. Cancel the draft invoice first.')
            billing.state = 'draft'


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
    qty_cumulative = fields.Float('Cumulative Qty', compute='_compute_cumulative', store=True, digits=(12, 3))
    qty_period = fields.Float('Current Period Qty', compute='_compute_period_qty', store=True, digits=(12, 3))
    unit_rate = fields.Monetary(currency_field='currency_id')
    amount = fields.Monetary(compute='_compute_amount', store=True, currency_field='currency_id')
    revenue_account_id = fields.Many2one(
        'account.account', string='Income Account',
        domain="[('account_type', 'in', ('income', 'income_other')), ('company_ids', 'in', [company_id])]",
    )
    tax_ids = fields.Many2many(
        'account.tax', string='Customer Taxes',
        domain="[('type_tax_use', '=', 'sale'), ('company_id', '=', company_id)]",
    )
    company_id = fields.Many2one(
        'res.company', related='billing_id.company_id', readonly=True,
    )
    currency_id = fields.Many2one('res.currency', related='billing_id.currency_id')

    @api.model_create_multi
    def create(self, vals_list):
        billing_ids = [vals.get('billing_id') for vals in vals_list if vals.get('billing_id')]
        if billing_ids and self.env['construction.ra.billing'].browse(billing_ids).filtered('invoice_id'):
            raise UserError('You cannot add billing lines after the customer invoice has been created.')
        return super().create(vals_list)

    def write(self, vals):
        if any(self.mapped('billing_id.invoice_id')):
            raise UserError('You cannot edit billing lines after the customer invoice has been created.')
        return super().write(vals)

    def unlink(self):
        if any(self.mapped('billing_id.invoice_id')):
            raise UserError('You cannot delete billing lines after the customer invoice has been created.')
        return super().unlink()

    @api.depends('qty_current')
    def _compute_cumulative(self):
        for rec in self:
            rec.qty_cumulative = rec.qty_current

    @api.depends('qty_previous', 'qty_current')
    def _compute_period_qty(self):
        for rec in self:
            rec.qty_period = rec.qty_current - rec.qty_previous

    @api.depends('qty_period', 'unit_rate')
    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.qty_period * rec.unit_rate

    @api.constrains('qty_previous', 'qty_current')
    def _check_cumulative_quantities(self):
        for rec in self:
            if rec.qty_previous < 0 or rec.qty_current < 0:
                raise ValidationError('Cumulative quantities cannot be negative.')
            if rec.qty_current < rec.qty_previous:
                raise ValidationError(
                    'The current cumulative quantity cannot be less than the previously certified quantity.'
                )


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
