# -*- coding: utf-8 -*-
#############################################################################
#
#
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import babel
from datetime import datetime, time
from datetime import date
from odoo import fields, models, tools, api, _
from odoo.fields import Command
from odoo.exceptions import ValidationError




class HRLoanPayment(models.Model):
    """" Calculate the date and make payslip done """
    _name = 'hr.loan.payment'

    name = fields.Char(default='New')
    employee_id = fields.Many2one('hr.employee')
    loan_id = fields.Many2one('hr.loan')
    loan_amount = fields.Float(related='loan_id.total_amount', store=True)
    loan_remaining = fields.Float(compute='_compute_balance_amount', store=True)
    journal_id = fields.Many2one('account.journal')
    move_id = fields.Many2one('account.move')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
    ],default='draft',string='State', tracking=True)

    @api.depends('loan_id')
    def _compute_balance_amount(self):
        for rec in self:
            rec.loan_remaining = rec.loan_id.balance_amount

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].get('hr.loan.payment.seq') or 'New'
        return super(HRLoanPayment, self).create(values)

    def action_confirm(self):
        for rec in self:
            if not rec.journal_id:
                raise ValidationError(_('Please specify a journal first.'))

            amount = rec.loan_remaining
            loan_name = rec.loan_id.name
            partner_id = rec.employee_id.user_partner_id.id
            journal_id = rec.journal_id.id

            debit_account_id  = rec.journal_id.default_account_id.id
            credit_account_id = rec.loan_id.employee_account_id.id

            timenow = date.today()

            move = self.env['account.move'].create(
                {
                    'move_type': 'entry',
                    # 'partner_id': loan.employee_id.user_partner_id.id,
                    # 'partner_id': loan.employee_id.address_id.id,
                    # 'date': (fields.Date.today() + timedelta(days=-20)).strftime('%Y-%m-%d'),
                    'date': timenow,
                    'ref': loan_name,
                    'journal_id': journal_id,
                    'line_ids': [
                        Command.create({'debit': amount, 'credit': 0, 'account_id': debit_account_id,
                                         'name': loan_name}),
                        Command.create(
                            {'debit': 0, 'credit': amount, 'account_id': credit_account_id, 'name': loan_name, 'partner_id': partner_id,}),
                    ],
                })

            move.action_post()
            rec.move_id = move.id

            for line in rec.loan_id.loan_lines:
                line.paid = True
            rec.loan_id._compute_total_amount()

            rec.write({'state': 'confirm'})
