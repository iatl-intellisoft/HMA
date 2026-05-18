# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class Employee(models.Model):
    """
    A class to contain employee age field and penalty
    """
    _inherit = 'hr.employee'

    age = fields.Integer(string="Age", compute='_compute_age', store=False)

    @api.depends('birthday')
    def _compute_age(self):
        """
        A method to calculate employee age
        """
        for employee in self:
            if employee.birthday is not None:
                date = fields.date.today()
                employee.age = relativedelta(date, employee.birthday).years


class ResConfigSettings(models.TransientModel):
    """"""
    _inherit = 'res.config.settings'
