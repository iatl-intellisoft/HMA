# -*- coding: utf-8 -*-
from odoo import models


class BankBalanceReport(models.AbstractModel):
    _name = 'report.bank_balance_report.report_bank_balance_document'
    _description = 'Bank Balance PDF Report'

    def _get_report_values(self, docids, data=None):
        wizard = self.env['bank.balance.wizard'].browse(docids)
        report_data, grand_total = wizard._compute_report_data()
        return {
            'doc_ids': docids,
            'doc_model': 'bank.balance.wizard',
            'docs': wizard,
            'report_data': report_data,
            'grand_total': grand_total,
            'date_from': wizard.date_from,
            'date_to': wizard.date_to,
            'show_details': wizard.show_details,
        }
