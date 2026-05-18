'''
Created on April 2, 2022

@author: Mutwkil Faisal
'''
from odoo import models, fields, api, _


class HolidaysAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    last_update = fields.Date('Last Update')