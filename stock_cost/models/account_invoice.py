# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    # -------------------------------------------------------------------------
    # COGS METHODS
    # -------------------------------------------------------------------------

    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        ''' 
        overwrite to add price exchange difference
        '''
        # res = super(AccountMove, self)._stock_account_prepare_anglo_saxon_out_lines_vals()
        lines_vals_list = []
        for move in self:
            if not move.is_sale_document(include_receipts=True) or not move.company_id.anglo_saxon_accounting:
                continue
            date = move.invoice_date or fields.Date.today()
            for line in move.invoice_line_ids:

                # Filter out lines being not eligible for COGS.
                if line.product_id.type != 'product' or line.product_id.valuation != 'real_time':
                    continue

                # Retrieve accounts needed to generate the COGS.
                accounts = (
                    line.product_id.product_tmpl_id
                    .with_context(force_company=line.company_id.id)
                    .get_product_accounts(fiscal_pos=move.fiscal_position_id)
                )
                debit_interim_account = accounts['stock_output']
                credit_expense_account = accounts['expense'] or self.journal_id.default_account_id
                if not debit_interim_account or not credit_expense_account:
                    continue

                # Compute accounting fields.
                sign = -1 if move.move_type == 'out_refund' else 1
                price_unit = line._stock_account_get_anglo_saxon_price_unit()
                balance = sign * line.quantity * price_unit

                # currency
                company = line.company_id
                company_currency = line.product_id.currency_id
                force_currency_id = line.product_id.force_currency_id
                amount_currency = 0
                currency = force_currency_id and force_currency_id.id or False
                if force_currency_id:
                    amount_currency = company_currency.with_context(date=date)._convert(abs(balance), force_currency_id,
                                                                                          company, date, round=False)
                # Add interim account line.
                lines_vals_list.append({
                    'name': line.name[:64],
                    'move_id': move.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.quantity,
                    'price_unit': price_unit,
                    'debit': balance < 0.0 and -balance or 0.0,
                    'credit': balance > 0.0 and balance or 0.0,
                    'account_id': debit_interim_account.id,
                    'exclude_from_invoice_tab': True,
                    'is_anglo_saxon_line': True,
                })

                # Add expense account line.
                lines_vals_list.append({
                    'name': line.name[:64],
                    'move_id': move.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.quantity,
                    'price_unit': -price_unit,
                    'debit': balance > 0.0 and balance or 0.0,
                    'credit': balance < 0.0 and -balance or 0.0,
                    'account_id': credit_expense_account.id,
                    'analytic_account_id': line.analytic_account_id.id,
                    'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                    'exclude_from_invoice_tab': True,
                    'is_anglo_saxon_line': True,
                })

                # update to add exchange difference
                # check if there is exchange price difference

                # get foreign standard price
                qty = line.quantity
                product = line.product_id
                foreign_price_unit = product.with_context(
                    force_company=company.id).foreign_standard_price
                # :Warning: Needs validation !!
                exp_price_unit = force_currency_id.with_context(date=date)._convert(foreign_price_unit, company_currency,
                                                                                    company, date, round=False)
                
                diff = exp_price_unit - price_unit
                if diff != 0:
                    diff_price = abs(diff)
                    diff_amount_curr = company_currency.with_context(date=date)._convert(abs(diff * qty),
                                                                                         force_currency_id, company, date, round=False)
                    diff_total = sign * diff_price * qty
                    price_diff_account = product.property_account_creditor_price_difference or product.categ_id.property_account_creditor_price_difference_categ
                    foreign_price_diff_account = product.categ_id.property_stock_account_currency_adjustment
                    if diff > 0:
                        cacc = price_diff_account
                        dacc = foreign_price_diff_account
                    elif diff < 0:
                        dacc = price_diff_account
                        cacc = foreign_price_diff_account
                    if not price_diff_account:
                        raise UserError(_(
                            'Configuration error. Please configure the price difference account on the product or its category to process this operation.'))
                    if not foreign_price_diff_account:
                        raise UserError(_(
                            'Configuration error. Please configure the Stock Currency Adjustment Account on the product category %s to process this operation.') % product.categ_id.name)

                    # Add price exchange account line.
                    lines_vals_list.append({
                        'name': line.name[:64],
                        'move_id': move.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom_id.id,
                        'quantity': line.quantity,
                        'price_unit': - diff_price,
                        'debit': diff_total < 0.0 and -diff_total or 0.0,
                        'credit': diff_total > 0.0 and diff_total or 0.0,
                        'account_id': cacc.id,
                        'analytic_account_id': line.analytic_account_id.id,
                        'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                        'exclude_from_invoice_tab': True,
                        'is_anglo_saxon_line': True,
                    })

                    # Add stock Currency Adjustment account line.
                    lines_vals_list.append({
                        'name': line.name[:64],
                        'move_id': move.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom_id.id,
                        'quantity': line.quantity,
                        'price_unit': diff_price,
                        'debit': diff_total > 0.0 and diff_total or 0.0,
                        'credit': diff_total < 0.0 and -diff_total or 0.0,
                        'account_id': dacc.id,
                        'analytic_account_id': line.analytic_account_id.id,
                        'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                        'exclude_from_invoice_tab': True,
                        'is_anglo_saxon_line': True,
                    })

        return lines_vals_list

