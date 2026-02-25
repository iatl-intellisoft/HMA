from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # def unlink(self):
    #     if self.state != 'draft':
    #         raise UserError(
    #             _("You cannot delete a payment that is already posted."))
    #     # if any(rec.move_name for rec in self):
    #     #     raise UserError(_('It is not allowed to delete a payment that already created a journal entry since it would create a gap in the numbering. You should create the journal entry again and cancel it thanks to a regular revert.'))
    #     for rec in self:
    #         rec.reconciled_invoice_ids = False
    #     return super(AccountPayment, self).unlink()

    def button_journal_get_entries(self):
        line = self.env['account.move.line'].search([('payment_id', 'in', self.ids)])
        return {
            'name': _('Journal Entries'),
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('line_ids', 'in', line.ids)],
        }


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    journal_id = fields.Many2one('account.journal', store=True, readonly=False,
                                 compute='_compute_journal_id',
                                 domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash'))]")

    @api.model
    def default_get(self, fields_list):
        # OVERRIDE
        res = super().default_get(fields_list)

        if self._context.get('active_model') == 'account.move':
            lines = self.env['account.move'].browse(self._context.get('active_ids', [])).line_ids
        elif self._context.get('active_model') == 'account.move.line':
            lines = self.env['account.move.line'].browse(self._context.get('active_ids', []))
        else:
            raise UserError(_(
                "The register payment wizard should only be called on account.move or account.move.line records."
            ))

        # Keep lines having a residual amount to pay.
        available_lines = self.env['account.move.line']
        valid_account_types = self.env['account.payment']._get_valid_payment_account_types()
        for line in lines.filtered(lambda r: r.display_type not in ('product', 'rounding')):
            if line.move_id.state != 'posted':
                raise UserError(_("You can only register payment for posted journal entries."))

            if line.account_type not in valid_account_types:
                continue
            if line.currency_id:
                print('line.currency_id.is_zero(line.amount_residual_currency)',
                      line.currency_id.is_zero(line.amount_residual_currency))
                if line.currency_id.is_zero(line.amount_residual_currency):
                    continue
            else:
                if line.company_currency_id.is_zero(line.amount_residual):
                    continue
            available_lines |= line

        # Check.
        if not available_lines:
            raise UserError(_(
                "You can't register a payment because there is nothing left to pay on the selected journal items."))
        if len(lines.company_id) > 1:
            raise UserError(_("You can't create payments for entries belonging to different companies."))
        if len(set(available_lines.mapped('account_type'))) > 1:
            raise UserError(
                _("You can't register payments for journal items being either all inbound, either all outbound."))

        res['line_ids'] = [(6, 0, available_lines.ids)]

        return res

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard(batch_result)
        payment_vals['destination_account_id'] = \
        self.line_ids.filtered(lambda r: r.display_type not in ('product', 'rounding'))[
            0].account_id.id,
        # payment_vals['move_id'] = self.line_ids.move_id.id

        return payment_vals

    # def _create_payment_vals_from_wizard(self, batch_result):
    #     payment_vals = {
    #         'date': self.payment_date,
    #         'amount': self.amount,
    #         'payment_type': self.payment_type,
    #         'partner_type': self.partner_type,
    #         'memo': self.communication,
    #         'journal_id': self.journal_id.id,
    #         'company_id': self.company_id.id,
    #         'currency_id': self.currency_id.id,
    #         'partner_id': self.partner_id.id,
    #         'partner_bank_id': self.partner_bank_id.id,
    #         'payment_method_line_id': self.payment_method_line_id.id,
    #         'destination_account_id': self.line_ids.filtered(lambda r: r.display_type not in ('product', 'rounding'))[
    #             0].account_id.id,
    #         'write_off_line_vals': [],
    #     }
    #
    #     if self.payment_difference_handling == 'reconcile':
    #         if self.early_payment_discount_mode:
    #             epd_aml_values_list = []
    #             for aml in batch_result['lines']:
    #                 if aml.move_id._is_eligible_for_early_payment_discount(self.currency_id, self.payment_date):
    #                     epd_aml_values_list.append({
    #                         'aml': aml,
    #                         'amount_currency': -aml.amount_residual_currency,
    #                         'balance': aml.currency_id._convert(-aml.amount_residual_currency, aml.company_currency_id, date=self.payment_date),
    #                     })
    #
    #             open_amount_currency = self.payment_difference * (-1 if self.payment_type == 'outbound' else 1)
    #             open_balance = self.currency_id._convert(open_amount_currency, self.company_id.currency_id, self.company_id, self.payment_date)
    #             early_payment_values = self.env['account.move']._get_invoice_counterpart_amls_for_early_payment_discount(epd_aml_values_list, open_balance)
    #             for aml_values_list in early_payment_values.values():
    #                 payment_vals['write_off_line_vals'] += aml_values_list
    #
    #         elif not self.currency_id.is_zero(self.payment_difference):
    #
    #             if self.writeoff_is_exchange_account:
    #                 # Force the rate when computing the 'balance' only when the payment has a foreign currency.
    #                 # If not, the rate is forced during the reconciliation to put the difference directly on the
    #                 # exchange difference.
    #                 if self.currency_id != self.company_currency_id:
    #                     payment_vals['force_balance'] = sum(batch_result['lines'].mapped('amount_residual'))
    #             else:
    #                 if self.payment_type == 'inbound':
    #                     # Receive money.
    #                     write_off_amount_currency = self.payment_difference
    #                 else:  # if self.payment_type == 'outbound':
    #                     # Send money.
    #                     write_off_amount_currency = -self.payment_difference
    #
    #                 payment_vals['write_off_line_vals'].append({
    #                     'name': self.writeoff_label,
    #                     'account_id': self.writeoff_account_id.id,
    #                     'partner_id': self.partner_id.id,
    #                     'currency_id': self.currency_id.id,
    #                     'amount_currency': write_off_amount_currency,
    #                     'balance': self.currency_id._convert(write_off_amount_currency, self.company_id.currency_id, self.company_id, self.payment_date),
    #                 })
    #
    #     return payment_vals

    # def _create_payment_vals_from_batch(self, batch_result):
    #     batch_values = self._get_wizard_values_from_batch(batch_result)
    #     return {
    #         'date': self.payment_date,
    #         'amount': batch_values['source_amount_currency'],
    #         'payment_type': batch_values['payment_type'],
    #         'partner_type': batch_values['partner_type'],
    #         'ref': self._get_batch_communication(batch_result),
    #         'journal_id': self.journal_id.id,
    #         'currency_id': batch_values['source_currency_id'],
    #         'partner_id': batch_values['partner_id'],
    #         'partner_bank_id': batch_result['key_values']['partner_bank_id'],
    #         'payment_method_id': self.payment_method_id.id,
    #         'destination_account_id': batch_result['lines'].filtered(
    #             lambda r: r.display_type not in ('product', 'rounding')).account_id.id
    #     }
