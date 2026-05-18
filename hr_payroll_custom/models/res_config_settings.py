# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):

    _inherit = 'res.config.settings'
   
    first_employee_id = fields.Many2one('hr.employee', string='first employee sign consider',related="company_id.first_employee_id", ondelete='set null', readonly=False)
    second_employee_id = fields.Many2one('hr.employee', string='second employee sign consider',related="company_id.second_employee_id", ondelete='set null', readonly=False)


class Company(models.Model):
    _inherit = 'res.company'

    first_employee_id = fields.Many2one('hr.employee', string='First employee sign consider', ondelete='set null' )
    second_employee_id = fields.Many2one('hr.employee', string='Second employee sign consider', ondelete='set null' )
