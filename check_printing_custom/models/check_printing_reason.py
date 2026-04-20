# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CheckPrintingReason(models.Model):
    _name = "check.printing.reason"
    _description = 'Check Printing Reason'

    name = fields.Char(string='Name')
    reprinting = fields.Boolean(string='Reprinting', default=1)
