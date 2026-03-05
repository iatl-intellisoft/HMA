# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HrLoanPostpone(models.Model):
    _name = 'hr.loan.postpone'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char('Reference',default=lambda self: _('New'), readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", store=True)
    loan_id = fields.Many2one('hr.loan', string="Loans",
                              domain="[('employee_id', '=', employee_id),('state','=','approve')]")
    loan_line_ids = fields.Many2many('hr.loan.line', string='Installments',
                                     domain="[('loan_id', '=', loan_id),('paid','=',False)]")
    amount = fields.Float('Amount', compute="_get_total_to_paid")
    state = fields.Selection([('draft', 'Draft'),
                              ('submit', 'Submit'),
                              ('cancel', 'Cancel')
                              ], string="State", default='draft', track_visibility='onchange', copy=False, )
    # move_id = fields.Many2one('account.move', string='Move', track_visibility='onchange')
    date = fields.Date(string="Date", default=datetime.today())
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)

    def _get_total_to_paid(self):
        """
        A method to get total paid loan amount
        """
        for loan in self:
            total_to_paid_amount = 0.00
            for line in loan.loan_line_ids:

                total_to_paid_amount += line.paid_amount
            loan.amount = total_to_paid_amount

    @api.model
    def create(self, vals):
        rec = super(HrLoanPostpone, self).create(vals)
        if not rec.loan_line_ids:
            raise ValidationError(_('Please add Lines To Postpone.'))

        loan = rec.loan_id.name
        rec.name = loan + self.env['ir.sequence'].get('loan.postpone') or ' '
        return rec

    def action_submit(self):
        """
        A method to Submit loan postpone
        """
        self.write({
            'state': 'submit'
        })

    def action_cancel(self):
        """
        A method to confirm loan postpone
        """
        self.write({
            'state': 'cancel'
        })

    def action_set_to_draft(self):
        """
        A method to return loan postpone to draft
        """
        self.write({
            'state': 'draft'
        })

