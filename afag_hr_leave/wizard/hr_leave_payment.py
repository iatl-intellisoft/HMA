from datetime import date

from odoo import fields, models, api, _
from odoo.fields import Command


class HRLeavePayment(models.TransientModel):
    _name = 'hr.leave.payment'

    journal_id = fields.Many2one('account.journal')
    debit_account_id = fields.Many2one('account.account')
    credit_account_id = fields.Many2one('account.account')
    
    is_purchased = fields.Boolean()
    is_paid = fields.Boolean()

    @api.onchange('journal_id')
    def on_change_journal_id(self):
        for rec in self:
            rec.debit_account_id = rec.journal_id.default_account_id.id

    def action_confirm(self):

        timenow = date.today()

        journal_id = self.journal_id.id
        debit_account_id = self.debit_account_id.id
        credit_account_id = self.credit_account_id.id


        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')

        if active_id and active_model:
            # Browse the active record
            leave_rec = self.env[active_model].browse(active_id)

            contract = leave_rec.employee_id.contract_id
            if contract:
                basic = contract.wage
                housing = contract.l10n_sa_housing_allowance
                transportation = contract.l10n_sa_transportation_allowance

                leave_compensation = ((basic + housing + transportation) / 30) * leave_rec.number_of_days
                partner_id = leave_rec.employee_id.work_contact_id.id

                move = self.env['account.move'].create(
                    {
                        'move_type': 'entry',
                        # 'partner_id': loan.employee_id.user_partner_id.id,
                        # 'partner_id': loan.employee_id.address_id.id,
                        # 'date': (fields.Date.today() + timedelta(days=-20)).strftime('%Y-%m-%d'),
                        'date': timenow,
                        'ref': '%s Payment' %leave_rec.name,
                        'journal_id': journal_id,
                        'line_ids': [
                            Command.create({'debit': leave_compensation, 'credit': 0, 'account_id': debit_account_id,
                                            'partner_id': partner_id, 'name': leave_rec.name}),
                            Command.create(
                                {'debit': 0, 'credit': leave_compensation, 'account_id': credit_account_id, 'name': leave_rec.name}),
                        ],
                    })

                leave_rec.move_id = move.id if move else False
                if self.is_purchased:
                    leave_rec.is_purchased = True if move else False
                else:
                    leave_rec.is_paid = True if move else False



