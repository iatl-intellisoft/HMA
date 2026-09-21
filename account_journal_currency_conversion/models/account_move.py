from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    custom_rate = fields.Float(
        string='Exchange Rate',
        digits=(16, 6),
        copy=False,
        help='Exchange rate used for this journal entry: units of company currency '
             'per 1 unit of the foreign currency.\n'
             'Auto-filled from Custom Currency Rates when a foreign-currency line is '
             'added. Edit to override for this specific entry.',
    )

    @api.onchange('custom_rate')
    def _onchange_custom_rate(self):
        """When the user edits Exchange Rate on the form, immediately update
        every non-company-currency line in the entry.

        Direction logic:
        - Line has amount_currency set but balance=0 → user typed the foreign
          amount; recalculate balance (→ debit/credit) using the new rate.
        - Line already has a balance → user typed debit/credit; recalculate
          amount_currency using the new rate.
        """
        if self.is_invoice(include_receipts=True) or not self.custom_rate:
            return
        company_currency = self.company_id.currency_id
        for line in self.line_ids:
            if not line.currency_id or line.currency_id == company_currency:
                continue
            if line.amount_currency and not line.balance:
                # Foreign amount was entered → compute balance → debit/credit
                line.balance = company_currency.round(
                    line.amount_currency * self.custom_rate
                )
            elif line.balance:
                # Debit/credit was entered → recompute amount_currency
                new_amt = line._get_computed_amount_currency()
                if line.amount_currency != new_amt:
                    line.amount_currency = new_amt
