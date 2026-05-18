# -*- coding: utf-8 -*-
from odoo import fields, models


class CheckDimension(models.Model):
    _name = "check.dimension"
    _description = "Check Dimension"

    name = fields.Char(string='Name', )
    font_size = fields.Integer(string='Font size', )
    partner_x = fields.Integer(string="Partner Width")
    partner_y = fields.Integer(string='Partner High', )
    ac_payee_x = fields.Integer(string="A/c payee Width")
    ac_payee_y = fields.Integer(string='A/c payee High', )
    check_amount_in_words_x = fields.Integer(string='Check Amount In Words Width', )
    check_amount_in_words_y = fields.Integer(string='Check Amount In Words High', )
    amount_x = fields.Integer(string=u'Amount Width', )
    amount_y = fields.Integer(string='Amount High', )
    date_x = fields.Integer(string='Date Width', )
    date_y = fields.Integer(string='Date High', )
    account_holder_width = fields.Integer('Name Width')
    money_text_width = fields.Integer('Money Area Width')
    money_text_height = fields.Integer('Money Area Height')
    type = fields.Selection([('mm', 'millimeter (mm)'), ('px', 'pixel (px)')], string='Type', default='mm')
