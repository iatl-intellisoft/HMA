# -*- coding: utf-8 -*-
from odoo import models, api


class CheckPrintingA4(models.AbstractModel):
    _name = 'report.check_printing_custom.a4_check_print_template'

    @api.model
    def _get_report_values(self, docids, data=None):
        payment = self.env['account.payment'].browse(data.get('form'))
        check_dimension_id = payment.journal_id.bank_id.check_dimension_id
        dimension_type = payment.journal_id.bank_id.check_dimension_id.type
        lang_dir = self.env['res.lang'].search([('code', 'like', data['language'])])[0].direction
        if lang_dir == 'rtl':
            return {
                'doc_ids': self.ids,
                'docs': payment,
                'x_partner': str(-check_dimension_id.partner_x) + str(dimension_type),
                'y_partner': str(check_dimension_id.partner_y) + str(dimension_type),
                'x_amount_word': str(-check_dimension_id.check_amount_in_words_x) + str(dimension_type),
                'y_amount_word': str(check_dimension_id.check_amount_in_words_y) + str(dimension_type),
                'x_amount': str(check_dimension_id.amount_x) + str(dimension_type),
                'y_amount': str(check_dimension_id.amount_y) + str(dimension_type),
                'x_date': str(check_dimension_id.date_x) + str(dimension_type),
                'y_date': str(check_dimension_id.date_y) + str(dimension_type),
                'font_size': str(check_dimension_id.font_size),
                'account_holder_width': str(check_dimension_id.account_holder_width) + str(dimension_type),
                'money_text_width': str(check_dimension_id.money_text_width) + str(dimension_type),
                'money_text_height': str(check_dimension_id.money_text_height) + str(dimension_type),
                'align_text': 'right',
                'language': data['language']
            }

        if lang_dir == 'ltr':
            return {
                'doc_ids': self.ids,
                'docs': payment,
                'x_partner': str(check_dimension_id.partner_x) + str(dimension_type),
                'y_partner': str(check_dimension_id.partner_y) + str(dimension_type),
                'x_amount_word': str(check_dimension_id.check_amount_in_words_x) + str(dimension_type),
                'y_amount_word': str(check_dimension_id.check_amount_in_words_y) + str(dimension_type),
                'x_amount': str(check_dimension_id.amount_x) + str(dimension_type),
                'y_amount': str(check_dimension_id.amount_y) + str(dimension_type),
                'x_date': str(check_dimension_id.date_x) + str(dimension_type),
                'y_date': str(check_dimension_id.date_y) + str(dimension_type),
                'font_size': str(check_dimension_id.font_size),
                'account_holder_width': str(check_dimension_id.account_holder_width) + str(dimension_type),
                'money_text_width': str(check_dimension_id.money_text_width) + str(dimension_type),
                'money_text_height': str(check_dimension_id.money_text_height) + str(dimension_type),
                'align_text': 'left',
                'language': data['language']
            }
