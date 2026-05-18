# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    payments_count = fields.Integer(compute='_compute_payment_number', string='Number of Payments', default=0)
    draft_payments_sum = fields.Float('Draft Payments Sum', compute='_compute_payment_number')
    reconciled_payment_ids = fields.Many2many('account.payment', 'account_payment_account_move_rel', 'account_move_id',
                                              'account_payment_id',
                                              help="Payments that have been reconciled with these invoices.")


    def button_open_payments(self):
        return {
            'name': _('Payments'),
            'view_mode': 'list,form',
            'res_model': 'account.payment',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {'create': False},
            'domain': [('invoice_id', '=', self.id)],
        }

    def _compute_payment_number(self):
        payment_ids = self.env['account.payment'].search(
            ['|', ('invoice_id', '=', self.id), ('id', 'in', self.reconciled_payment_ids.ids)])
        self.payments_count = len(payment_ids)
        self.draft_payments_sum = sum(payment_ids.filtered(lambda r: r.state == 'draft').mapped('amount'))

    def action_register_payment(self):
        ''' Open the account.payment.register wizard to pay the selected journal entries.
        :return: An action opening the account.payment.register wizard.
        '''
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
                'from_wizard': True,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }


class AccountRegisterPayments(models.TransientModel):
    _inherit = "account.payment.register"

    invoice_ids = fields.Many2one('account.move.line')

    def _create_payments(self):
        payments = super(AccountRegisterPayments, self)._create_payments()
        invoice_id = self.line_ids[0].move_id
        for payment in payments:
            payment.invoice_id = invoice_id

        return payments


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    invoice_id = fields.Many2one('account.move', store=True)
    # reconciled_invoice_ids = fields.Many2many('account.move',
    #                                           'account_payment_account_move_rel', 'account_payment_id',
    #                                           'account_move_id',
    #                                           search='_search_reconciled_invoice_ids',
    #                                           compute='_compute_stat_buttons_from_reconciliation',
    #                                           help="Invoices whose journal items have been reconciled with these payments.",
    #                                           compute_sudo=True,)

    def button_draft(self):
        for payment in self:
            if payment.move_id.state == 'posted':
                payment.move_id.line_ids.filtered(lambda l: l.reconciled).remove_move_reconcile()
            super(AccountPayment, payment).button_draft()

    def action_post(self):
        for payment in self:
            if self._context.get('from_wizard') and payment.journal_id.post_at_bank:
                payment.write({'state': 'draft'})
                continue
            else:
                return super(AccountPayment, self).action_post()



        # domain = [
        #     ('account_type', 'in', ('asset_receivable', 'liability_payable')),
        #     ('reconciled', '=', False),
        # ]
        #
        # for payment in self:
        #     if payment.state != 'paid' or not payment.invoice_id:
        #         continue
        #
        #     invoice_lines = payment.invoice_id.line_ids.filtered_domain(domain)
        #     payment_lines = payment.move_id.line_ids.filtered_domain(domain)
        #
        #     for account in payment_lines.account_id:
        #         (payment_lines + invoice_lines).filtered_domain([
        #             ('account_id', '=', account.id),
        #             ('reconciled', '=', False),
        #         ]).reconcile()

