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
        """When the user edits Exchange Rate on the form, immediately recalculate
        amount_currency for every non-company-currency line in the entry."""
        if self.is_invoice(include_receipts=True):
            return
        company_currency = self.company_id.currency_id
        for line in self.line_ids:
            if line.currency_id and line.currency_id != company_currency:
                new_amt = line._get_computed_amount_currency()
                if line.amount_currency != new_amt:
                    line.amount_currency = new_amt
