# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class Employee(models.Model):
    """
    A class to contain employee age field and penalty
    """
    _inherit = 'hr.employee'

    bank_id = fields.Many2one('res.bank', related='bank_account_id.bank_id', readonly=False,store=True) 



class ResourceCalender(models.Model):
    _inherit = 'resource.calendar'


    number_of_days = fields.Float(string="Number Of Days")    