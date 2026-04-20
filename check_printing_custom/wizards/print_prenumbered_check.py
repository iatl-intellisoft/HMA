# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PrintPreNumberedCheck(models.TransientModel):
    _inherit = "print.prenumbered.checks"

    PRINTERS = [('cheque', 'Cheque Printer'), ('normal', 'Normal Printer')]

    def _account_payment(self):
        # for rec in self :
        if 'payment_ids' in self.env.context:
            payments = self.env['account.payment'].browse(self.env.context['payment_ids'])
            return payments
        else:
            return

    reason_id = fields.Many2one('check.printing.reason', string='Printing Reason', ondelete='set null', )
    reprinting = fields.Boolean(string='Reprinting', related="reason_id.reprinting")
    payment_id = fields.Many2one('account.payment', string='payment', ondelete='set null', default=_account_payment)
    check_first_print = fields.Boolean(string='Technical field to check first print',
                                       related="payment_id.check_first_print")
    lang_id = fields.Many2one('res.lang', string='Language',
                              help="Language from the website when lead has been created")
    printer = fields.Selection(PRINTERS, 'Printer Type')

    # @api.multi
    def print_checks(self):
        check_number = int(self.next_check_number)
        payments = self.env['account.payment'].browse(self.env.context['payment_ids'])
        payments.filtered(lambda r: r.state == 'draft').action_post()
        # payments.filtered(lambda r: r.state not in ('sent', 'cancelled')).write({'state': 'sent'})
        payments.write({'check_first_print': True})
        #if not payments.journal_id.bank_id.id or not payments.journal_id.bank_id.check_dimension_id.id:
            #raise ValidationError(_("This payment journal has no bank or bank has no dimension!!"))
        if self.reason_id and not self.reason_id.reprinting:
            check_number += 1
            for payment in payments:
                if payment.journal_id.check_manual_sequencing:
                    payment.journal_id.check_sequence_id.sudo().number_next_actual = check_number + 1
                payment.check_number = check_number

        self.env['check.printing.log'].create({
            'payment_id': payments.id,
            'reason_id': self.reason_id.id if self.reason_id else False,
            'check_no': check_number,
        })

        lan = self.lang_id.code
        return payments.with_context({'printer': self.printer}).do_print_checks(lan)
