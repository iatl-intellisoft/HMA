# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    log_ids = fields.One2many('check.printing.log', 'payment_id', string='log', )
    log_number = fields.Integer(compute='_compute_log_number')
    beneficiary = fields.Char(string="Beneficiary", compute="_onchange_partner_id", store=True, readonly=False)
    amount_in_words_arabic = fields.Char("Amount in Words Arabic", compute="_onchange_amount", store=True,
                                         readonly=False)
    check_first_print = fields.Boolean(string='Technical field Check first print')

    @api.depends('payment_method_id', 'amount', 'currency_id')
    def _onchange_amount(self):
        for pay in self:
            if pay.currency_id and pay.payment_method_id.code == 'check_printing':
                pay.amount_in_words_arabic = pay.currency_id.with_context(lang='ar_001').amount_to_text(
            pay.amount) if pay.currency_id else False

    @api.depends('partner_id')
    def _onchange_partner_id(self):
        # self.ensure_one()
        for rec in self:
            if rec.partner_id:
                rec.beneficiary = rec.partner_id.name

    @api.depends('log_ids')
    def _compute_log_number(self):
        for record in self:
            record.log_number = len(record.log_ids)

    # @api.multi
    def print_checks(self):
        """  override to handle Manual Numbering:- must appear wizard and check sequence must be read only"""
        self = self.filtered(lambda r: r.payment_method_id.code == 'check_printing' and r.state != 'reconciled')

        if len(self) == 0:
            raise UserError(_("Payments to print as a checks must have 'Check' selected as payment method and "
                              "not have already been reconciled"))
        if any(payment.journal_id != self[0].journal_id for payment in self):
            raise UserError(_("In order to print multiple checks at once, they must belong to the same bank journal."))

        if not self[0].journal_id.check_manual_sequencing:
            # The wizard asks for the number printed on the first pre-printed check
            # so payments are attributed the number of the check the'll be printed on.
            last_printed_check = self.search([
                ('journal_id', '=', self[0].journal_id.id),
                ('check_number', '!=', 0)], order="check_number desc", limit=1)
            next_check_number = last_printed_check and int(last_printed_check.check_number) + 1 or 1
        else:
            next_check_number = self[0].check_number
        return {
            'name': _('Print Pre-numbered Checks'),
            'type': 'ir.actions.act_window',
            'res_model': 'print.prenumbered.checks',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'payment_ids': self.ids,
                'default_next_check_number': next_check_number,
            }
        }

    # @api.multi
    def do_print_checks(self, language=None):
        printer = self._context.get('printer', False)
        if self:
            datas = {
                'ids': [],
                'model': 'account.payment',
                'form': self.id,
                'language': language
            }

            if printer and printer == 'cheque':
                return self.env.ref('check_printing_custom.check_special').report_action(self,
                                                                                         datas)
            elif printer and printer == 'normal':
                return self.env.ref('check_printing_custom.check_a4').report_action(self,
                                                                                    datas)
        return super(AccountPayment, self).do_print_checks(language)
