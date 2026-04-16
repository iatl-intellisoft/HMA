# -*- coding: utf-8 -*-

from odoo import fields, models


class HRSalaryRule(models.Model):
    """"""
    _inherit = "hr.salary.rule"

    use_type = fields.Selection(selection_add=[('loan', 'Loan')])
