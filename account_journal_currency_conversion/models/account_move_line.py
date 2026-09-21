from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.onchange('amount_currency', 'currency_id')
    def _inverse_amount_currency(self):
        for line in self:
            if line.move_id.is_invoice(include_receipts=True):
                super(AccountMoveLine, line)._inverse_amount_currency()
                continue

            company_currency = line.company_id.currency_id

            if line.currency_id == company_currency:
                if line.balance != line.amount_currency:
                    line.balance = line.amount_currency

            elif not line.debit and not line.credit:
                if line.amount_currency and line.currency_rate:
                    line.balance = line.company_id.currency_id.round(
                        line.amount_currency / line.currency_rate
                    )

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
            if (
                not line.move_id.is_invoice(include_receipts=True)
                and line.currency_id
                and line.currency_id != line.company_id.currency_id
                and (line.debit or line.credit)
            ):
                new_amt = line._get_computed_amount_currency()
                if line.amount_currency != new_amt:
                    line.amount_currency = new_amt