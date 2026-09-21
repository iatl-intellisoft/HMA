from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _inverse_amount_currency(self):
        """When the user types an amount in the currency field:
        - Invoices/receipts: delegate to standard Odoo (no change).
        - Non-invoice journal entries with a foreign currency: convert
          amount_currency → balance using the custom rate when one is
          configured; otherwise fall back to Odoo's standard currency_rate.
        - Same-currency lines: delegate to standard Odoo.
        """
        for line in self:
            company_currency = line.company_id.currency_id

            if line.move_id.is_invoice(include_receipts=True):
                # Standard Odoo handles invoice lines.
                super(AccountMoveLine, line)._inverse_amount_currency()

            elif (
                line.currency_id
                and line.currency_id != company_currency
                and not self.env.is_protected(self._fields['balance'], line)
            ):
                # Non-invoice line with a foreign currency.
                # Try to find a custom rate (foreign → company currency).
                date = line.date or fields.Date.context_today(line)
                custom_rate = self.env['custom.currency.rate'].get_custom_rate(
                    line.currency_id.id,
                    company_currency.id,
                    date=date,
                )
                if custom_rate:
                    # amount_currency (foreign) × rate = balance (company)
                    line.balance = company_currency.round(line.amount_currency * custom_rate)
                elif line.currency_rate:
                    # Fallback: use Odoo's standard exchange rate.
                    line.balance = company_currency.round(line.amount_currency / line.currency_rate)

            else:
                # Same currency or protected — standard Odoo handles it.
                super(AccountMoveLine, line)._inverse_amount_currency()

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
            return company_currency._convert(
                balance,
                self.currency_id,
                self.company_id,
                date,
                round=True,
            )

        source_line = False
        for line in foreign_lines:
            if line != self and line.amount_currency:
                source_line = line
                break

        if not source_line:
            return company_currency._convert(balance, self.currency_id, self.company_id, date, round=True)

        rate = CustomRate.get_custom_rate(source_line.currency_id.id, self.currency_id.id, date=date)

        if not rate:
            return 0.0

        sign = 1 if balance >= 0 else -1
        return self.currency_id.round(abs(source_line.amount_currency) * rate * sign)

    @api.depends('currency_id', 'debit', 'credit', 'move_id.date', 'date')
    def _compute_amount_currency(self):
        super()._compute_amount_currency()
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True) and line.currency_id and line.currency_id != line.company_id.currency_id:
                new_amt = line._get_computed_amount_currency()
                if line.amount_currency != new_amt:
                    line.amount_currency = new_amt