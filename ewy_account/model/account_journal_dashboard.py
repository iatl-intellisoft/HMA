from odoo import models
from odoo.tools import formatLang


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        super()._fill_bank_cash_dashboard_data(dashboard_data)

        bank_cash_journals = self.filtered(lambda j: j.type in ('bank', 'cash', 'credit'))
        company_currency = self.env.company.currency_id
        company_ids = tuple(self.env.companies.ids)

        for journal in bank_cash_journals:
            account = journal.default_account_id
            display_currency = account.second_currency_id or account.currency_id or company_currency

            if display_currency != company_currency:
                amls = self.env['account.move.line'].search([
                    ('account_id', '=', account.id),
                    ('parent_state', '=', 'posted'),
                    ('company_id', 'in', list(self.env.companies.ids)),
                ])
                gl_balance = 0.0
                for aml in amls:
                    if aml.currency_id and aml.currency_id == display_currency and aml.amount_currency:
                        gl_balance += aml.amount_currency
                    else:
                        gl_balance += company_currency._convert(
                            aml.balance, display_currency, self.env.company, aml.date
                        )
            else:
                self.env.cr.execute("""
                    SELECT COALESCE(SUM(aml.balance), 0.0)
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    WHERE aml.account_id = %s
                      AND am.state = 'posted'
                      AND aml.company_id IN %s
                """, (account.id, company_ids))
                gl_balance = self.env.cr.fetchone()[0] or 0.0

            dashboard_data[journal.id]['gl_balance'] = formatLang(
                self.env, gl_balance, currency_obj=display_currency
            )