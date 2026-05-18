# -*- coding: utf-8 -*-

from odoo import models, fields, api,_

class Contract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Contract Extension'

    def compute_loan_amount(self, payslip, loan_type):
        result = 0
        for input in payslip.input_line_ids:
            if input.code == loan_type:
                result += input.amount
        return result