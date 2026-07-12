# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    warehouse_name_ids = fields.Many2many(
    comodel_name='stock.warehouse',
relation='hr_employee_warehouse_rel',
column1='employee_id',
column2='warehouse_id',
        string='المخازن المسموح بها',
        help='المخازن التي يسمح لهذا الموظف (أمين المخزن) برؤيتها وتصديق عملياتها.'
    )
