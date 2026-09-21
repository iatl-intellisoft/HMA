from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    custom_rate = fields.Float(
        string='Rate',
        digits=(16, 6),
        help='Exchange rate: units of company currency per 1 unit of the line currency.\n'
             'Auto-filled from Custom Currency Rates when the currency is selected; '
             'edit this field to override the rate for this specific line.',
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_custom_rate_for_line(self, date=None):
        """Return the custom exchange rate (company_currency / line_currency)
        for this line, or 0.0 if none is configured."""
        self.ensure_one()
        company_currency = self.company_id.currency_id
        if not self.currency_id or self.currency_id == company_currency:
            return 0.0
        if not date:
            date = self.date or fields.Date.context_today(self)
        return self.env['custom.currency.rate'].get_custom_rate(
            self.currency_id.id,
            company_currency.id,
            date=date,
        ) or 0.0

    # ------------------------------------------------------------------
    # Onchange: auto-fill custom_rate when currency / date changes
    # ------------------------------------------------------------------

    @api.onchange('currency_id', 'date')
    def _onchange_currency_custom_rate(self):
        """Auto-fill custom_rate from Custom Currency Rates on non-invoice
        journal entry lines whenever the currency or date is changed."""
        for line in self:
            if line.move_id.is_invoice(include_receipts=True):
                continue
            company_currency = line.company_id.currency_id
            if not line.currency_id or line.currency_id == company_currency:
                line.custom_rate = 0.0
                continue
            rate = line._get_custom_rate_for_line()
            if rate:
                line.custom_rate = rate

    # ------------------------------------------------------------------
    # Inverse: amount_currency → debit / credit
    # ------------------------------------------------------------------

    def _inverse_amount_currency(self):
        """When the user types an amount in the currency field of a journal
        entry line, compute debit/credit using custom_rate (if set on the
        line or from Custom Currency Rates), falling back to Odoo's standard
        currency_rate only when no custom rate exists.

        Invoice lines are still handled by the standard Odoo method.
        """
        for line in self:
            if line.move_id.is_invoice(include_receipts=True):
                # Standard Odoo handles invoice lines.
                super(AccountMoveLine, line)._inverse_amount_currency()
                continue

            company_currency = line.company_id.currency_id
            if (
                line.currency_id
                and line.currency_id != company_currency
                and not self.env.is_protected(self._fields['balance'], line)
            ):
                # Use the rate stored on the line; look it up if not set yet.
                rate = line.custom_rate or line._get_custom_rate_for_line()
                if rate:
                    # amount_currency (foreign) × rate = balance (company)
                    line.balance = company_currency.round(line.amount_currency * rate)
                elif line.currency_rate:
                    # Fallback: Odoo's standard exchange rate.
                    line.balance = company_currency.round(line.amount_currency / line.currency_rate)
            else:
                super(AccountMoveLine, line)._inverse_amount_currency()

    # ------------------------------------------------------------------
    # Compute: debit / credit → amount_currency
    # ------------------------------------------------------------------

    def _get_computed_amount_currency(self):
        self.ensure_one()

        company_currency = self.company_id.currency_id
        balance = self.debit - self.credit

        if not self.currency_id or self.currency_id == company_currency:
            return balance

        date = self.date or fields.Date.context_today(self)
        CustomRate = self.env['custom.currency.rate']
        move_lines = self.move_id.line_ids if self.move_id else self

        foreign_lines = move_lines.filtered(
            lambda l: l.currency_id and l.currency_id != company_currency
        )

        is_primary_foreign_line = foreign_lines and foreign_lines[0] == self

        if is_primary_foreign_line:
            # Use custom_rate on this line if set; otherwise standard Odoo rate.
            rate = self.custom_rate or self._get_custom_rate_for_line(date=date)
            if rate:
                return self.currency_id.round(balance / rate)
            return company_currency._convert(
                balance, self.currency_id, self.company_id, date, round=True,
            )

        source_line = False
        for line in foreign_lines:
            if line != self and line.amount_currency:
                source_line = line
                break

        if not source_line:
            rate = self.custom_rate or self._get_custom_rate_for_line(date=date)
            if rate:
                return self.currency_id.round(balance / rate)
            return company_currency._convert(
                balance, self.currency_id, self.company_id, date, round=True,
            )

        rate = CustomRate.get_custom_rate(source_line.currency_id.id, self.currency_id.id, date=date)
        if not rate:
            return 0.0

        sign = 1 if balance >= 0 else -1
        return self.currency_id.round(abs(source_line.amount_currency) * rate * sign)

    @api.depends('currency_id', 'debit', 'credit', 'move_id.date', 'date', 'custom_rate')
    def _compute_amount_currency(self):
        super()._compute_amount_currency()
        for line in self:
            if (
                not line.move_id.is_invoice(include_receipts=True)
                and line.currency_id
                and line.currency_id != line.company_id.currency_id
            ):
                new_amt = line._get_computed_amount_currency()
                if line.amount_currency != new_amt:
                    line.amount_currency = new_amt
