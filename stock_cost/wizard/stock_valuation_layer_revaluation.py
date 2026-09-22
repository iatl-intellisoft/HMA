# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, AccessError
from odoo.tools.float_utils import float_compare, float_round, float_is_zero


class StockValuationLayerRevaluation(models.TransientModel):
    _inherit = "stock.valuation.layer.revaluation"

    current_foreign_value_svl = fields.Float(
        "Current Value", related="product_id.foreign_value_svl", currency_field='force_currency_id')

    # foreign_added_value = fields.Monetary("Added value", required=True)
    new_foreign_value = fields.Monetary(
        "New Foreign value", compute='_compute_new_value', currency_field='force_currency_id')
    new_foreign_value_by_qty = fields.Monetary(
        "New Foreing value by quantity", compute='_compute_new_value', currency_field='force_currency_id')
    force_currency_id = fields.Many2one('res.currency', 'Force Currency',
                                        help='Use this currency instead of the product company currency', related='product_id.force_currency_id')

    @api.depends('current_value_svl', 'current_quantity_svl', 'added_value')
    def _compute_new_value(self):
        for reval in self:
            reval.new_value = reval.current_value_svl + reval.added_value
            reval.new_foreign_value = reval.current_foreign_value_svl + reval.added_value
            if not float_is_zero(reval.current_quantity_svl, precision_rounding=self.product_id.uom_id.rounding):
                reval.new_value_by_qty = reval.new_value / reval.current_quantity_svl
                reval.new_foreign_value_by_qty = reval.new_foreign_value / reval.current_quantity_svl
            else:
                reval.new_value_by_qty = 0.0
                reval.new_foreign_value_by_qty = 0.0


    # @api.model
    # def default_get(self, fields):
    #     res = super(StockValuationLayerRevaluation, self).default_get(fields)
    #     print("--res", res)
    #     # if 'added_value' in fields:
    #     #     product_or_template = self.env['product.product'].browse(res['product_id'])

    #     #     res['added_value'] = product_or_template.foreign_standard_price
    #     product_or_template = self.env['product.product'].browse(res['product_id'])
    #     res['force_currency_id'] = product_or_template.force_currency_id.id

    #     return res


    def action_validate_revaluation(self):
        """ Revaluate the stock for `self.product_id` in `self.company_id`.

        - Change the stardard price with the new valuation by product unit.
        - Create a manual stock valuation layer with the `added_value` of `self`.
        - Distribute the `added_value` on the remaining_value of layers still in stock (with a remaining quantity)
        - If the Inventory Valuation of the product category is automated, create
        related account move.
        """
        self.ensure_one()
        if self.currency_id.is_zero(self.added_value):
            raise UserError(
                _("The added value doesn't have any impact on the stock valuation"))

        product_id = self.product_id.with_company(self.company_id)

        remaining_svls = self.env['stock.valuation.layer'].search([
            ('product_id', '=', product_id.id),
            ('remaining_qty', '>', 0),
            ('company_id', '=', self.company_id.id),
        ])

        # Create a manual stock valuation layer
        if self.reason:
            description = _("Manual Stock Valuation: %s.", self.reason)
        else:
            description = _("Manual Stock Valuation: No Reason Given.")
        if product_id.categ_id.property_cost_method == 'average':
            description += _(
                " Product Foreign cost updated from %(previous)s to %(new_cost)s.",
                previous=product_id.foreign_standard_price,
                new_cost=product_id.foreign_standard_price + self.added_value / self.current_quantity_svl
            )
        company_currency = product_id.currency_id
        force_currency_id = self.force_currency_id or product_id.force_currency_id
        date = self.date or fields.Date.today()
        if force_currency_id and force_currency_id != company_currency:
            value = force_currency_id.with_context(date=date).sudo().compute(self.added_value, company_currency)
        else: 
            value = self.added_value
        revaluation_svl_vals = {
            'company_id': self.company_id.id,
            'product_id': product_id.id,
            'description': description,
            'value': value,
            'foreign_value': self.added_value,
            'force_currency_id': self.force_currency_id and self.force_currency_id.id or False,
            'quantity': 0,
        }

        remaining_qty = sum(remaining_svls.mapped('remaining_qty'))
        foreign_remaining_value = self.added_value
        remaining_value = value
        remaining_value_unit_cost = self.currency_id.round(
            remaining_value / remaining_qty)
        remaining_foreign_value_unit_cost = self.force_currency_id.round(
            foreign_remaining_value / remaining_qty)
        for svl in remaining_svls:
            if float_is_zero(svl.remaining_qty - remaining_qty, precision_rounding=self.product_id.uom_id.rounding):
                svl.remaining_value += remaining_value
                svl.foreign_remaining_value += foreign_remaining_value
            else:
                taken_remaining_value = remaining_value_unit_cost * svl.remaining_qty
                svl.remaining_value += taken_remaining_value
                remaining_value -= taken_remaining_value
                remaining_qty -= svl.remaining_qty
                ## for foreign
                taken_foreign_remaining_value = remaining_foreign_value_unit_cost * svl.remaining_qty
                svl.foreign_remaining_value += foreign_remaining_value
                foreign_remaining_value -= taken_foreign_remaining_value

        revaluation_svl = self.env['stock.valuation.layer'].create(
            revaluation_svl_vals)

        # Update the stardard price in case of AVCO
        if product_id.categ_id.property_cost_method == 'average':
            product_id.with_context(
                disable_auto_svl=True).standard_price += value / self.current_quantity_svl
            product_id.with_context(
                disable_auto_svl=True).foreign_standard_price += self.added_value / self.current_quantity_svl

        # If the Inventory Valuation of the product category is automated, create related account move.
        if self.property_valuation != 'real_time':
            return True

        accounts = product_id.product_tmpl_id.get_product_accounts()

        if self.added_value < 0:
            debit_account_id = self.account_id.id
            credit_account_id = accounts.get(
                'stock_valuation') and accounts['stock_valuation'].id
        else:
            debit_account_id = accounts.get(
                'stock_valuation') and accounts['stock_valuation'].id
            credit_account_id = self.account_id.id

        currency_id = False
        amount_currency = False
        if force_currency_id and force_currency_id != company_currency:
            amount_currency = abs(self.added_value)
            currency_id = force_currency_id.id
        else:
            amount = abs(value)
        move_vals = {
            'journal_id': self.account_journal_id.id or accounts['stock_journal'].id,
            'company_id': self.company_id.id,
            'ref': _("Revaluation of %s", product_id.display_name),
            'stock_valuation_layer_ids': [(6, None, [revaluation_svl.id])],
            'date': self.date or fields.Date.today(),
            'move_type': 'entry',
            'line_ids': [(0, 0, {
                'name': _('%(user)s changed stock valuation from  %(previous)s to %(new_value)s - %(product)s',
                          user=self.env.user.name,
                          previous=self.current_foreign_value_svl,
                          new_value=self.current_foreign_value_svl + self.added_value,
                          product=product_id.display_name,
                          ),
                'account_id': debit_account_id,
                'debit': abs(value),
                'currency_id': currency_id,
                'amount_currency': amount_currency,
                'credit': 0,
                'product_id': product_id.id,
            }), (0, 0, {
                'name': _('%(user)s changed stock valuation from  %(previous)s to %(new_value)s - %(product)s',
                          user=self.env.user.name,
                          previous=self.current_foreign_value_svl,
                          new_value=self.current_foreign_value_svl + self.added_value,
                          product=product_id.display_name,
                          ),
                'account_id': credit_account_id,
                'debit': 0,
                'credit': abs(value),
                'currency_id': currency_id,
                'amount_currency': amount_currency * -1,
                'product_id': product_id.id,
            })],
        }
        account_move = self.env['account.move'].create(move_vals)
        account_move._post()

        return True
