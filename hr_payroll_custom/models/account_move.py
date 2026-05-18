# -*- coding: utf-8 -*-

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class AccountMove(models.Model):

    _inherit = 'account.move'
    gm_exist = fields.Boolean('GM Exist', default=True)
    bank_id = fields.Many2one('res.bank',string='Bank') 
