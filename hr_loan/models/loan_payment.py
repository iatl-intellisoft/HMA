from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HrLoanPayment(models.Model):
    """"""
    _name = 'loan.payment'
    _inherit = ['mail.thread']
    _description = "Loan Payments as voucher"

    name = fields.Char(string="Reference", required=False, )
    # reference = fields.Char('Reference')
    employee_id = fields.Many2one('hr.employee', string="Employee", store=True)
    loan_id = fields.Many2one('hr.loan', string="Loans",
                              domain="[('employee_id', '=', employee_id),('state','=','approve')]")
    loan_line_ids = fields.Many2many('hr.loan.line', string='Installments',
                                     domain="[('loan_id', '=', loan_id),('paid','=',False)]")
    amount = fields.Float('Amount', compute="_get_total_to_paid")
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Confirmed'),
                              ('approve', 'Approved'),
                              ('paid', 'Paid'),
                              ('cancel', 'Cancel')
                              ], string="State", default='draft', track_visibility='onchange', copy=False, )
    move_id = fields.Many2one('account.move', string='Move', track_visibility='onchange')
    date = fields.Date(string="Date", default=datetime.today())
    journal_id = fields.Many2one('account.journal', string="Journal", domain=[('type', '=', 'sale')])
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

    def action_confirmed(self):
        """
        A method to confirm loan payment
        """
        self.write({
            'state': 'confirmed'
        })

    def action_cancel(self):
        """
        A method to cancel loan payment
        """
        self.write({
            'state': 'cancel'
        })

    def action_approve(self):
        """
        A method to approve loan payment
        """
        if not self.loan_id.loan_type.emp_account_id or not self.loan_id.loan_type.treasury_account_id:
            raise UserError(_( "You must enter employee account & Treasury account and journal to approve "))
        if not self.loan_line_ids:
            raise UserError(_('You must compute Loan Request before Approved'))
        for payment in self:
            journal_id = payment.journal_id.id
            emp_partner = payment.employee_id.work_contact_id.id
            if not emp_partner:
                raise ValidationError(_('Please add Partner for this Employee.'))
            line = [(0, 0, {

                'partner_id': emp_partner,
                'name': payment.name or " ",
                'account_id': payment.loan_id.loan_type.emp_account_id.id,
                'price_unit': payment.amount,
                'quantity': 1,

            })]
            vals = {

                'date': payment.date,
                'partner_id': emp_partner,
                'journal_id': journal_id,
                'move_type': 'out_receipt',
                'payment_id': self.id,
                # 'ref': payment.name,
                'invoice_line_ids': line,

            }

            move_id = self.env['account.move'].sudo().create(vals)
            self.write({'state': "approve", 'move_id': move_id.id})
            # payment.loan_line_ids.write({'paid': True})
        return True

    @api.model
    def create(self, values):
        """
        Inherit create method to ensure loan lines was created and then create sequence
        """
        res = super(HrLoanPayment, self).create(values)
        if not res.loan_line_ids:
            raise ValidationError(_('Please add Lines Installments.'))

        loan = res.loan_id.name
        res.name = loan + self.env['ir.sequence'].get('loan.payment') or ' '

        return res

    def unlink(self):
        """
        A method to delete loan payment
        """
        for payment in self:
            if payment.state not in ('draft',):
                raise UserError(_('You can not delete record not in draft state.'))
        return super(HrLoanPayment, self).unlink()
