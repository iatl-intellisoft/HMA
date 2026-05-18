# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrOvertimeConfig(models.Model):
    _name = 'hr.overtime.config'
    _description = 'saudi hr overtime configuration'

    overtime_equation = fields.Text( 'Overtime Equation')

    _rec_name = 'overtime_equation'
