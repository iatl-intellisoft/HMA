# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from collections import defaultdict

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.tools.float_utils import float_compare, float_round, float_is_zero
from odoo.exceptions import UserError, AccessError, ValidationError


class StockMove(models.Model):
    _inherit = "stock.move"

    foreign_price_unit = fields.Float(
        'Foreign Unit Price',
        help="Technical field used to record the foreign product cost set by the user during a picking confirmation (when costing "
             "method used is 'average price' or 'real'). Value given in Foreign currency and in product uom.",
        copy=False)

    force_currency_id = fields.Many2one('res.currency', 'Force Currency',
                                        help='Use this currency instead of the product company currency'
                                        )

    rate = fields.Float(string='Accounting Rate')

    def _get_foreign_price_unit(self):
        """ Returns the unit foreign price to store on the quant """
        # self.ensure_one()
        if self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id:
            line = self.purchase_line_id
            order = line.order_id
            date_order = self.purchase_line_id.order_id.date_order
            date_approve = self.purchase_line_id.order_id.date_approve
            accounting_date = self.picking_id.accounting_date
            foreign_price_unit = line.price_unit
            if line.taxes_id:
                foreign_price_unit = line.taxes_id.with_context(round=False).compute_all(
                    foreign_price_unit, currency=line.order_id.currency_id, quantity=1.0)['total_void']
            if line.product_uom.id != line.product_id.uom_id.id:
                foreign_price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if line.product_id.force_currency_id and line.product_id.force_currency_id != order.currency_id:
                # The date must be today, and not the date of the move since the move move is still
                # in assigned state. However, the move date is the scheduled date until move is
                # done, then date of actual move processing. See:
                # https://github.com/odoo/odoo/blob/2f789b6863407e63f90b3a2d4cc3be09815f7002/addons/stock/models/stock_move.py#L36
                foreign_price_unit = order.currency_id._convert(
                    foreign_price_unit, line.product_id.force_currency_id, order.company_id,
                    accounting_date or date_approve or date_order or fields.Date.context_today(self), round=False)
            return foreign_price_unit
        else:
            foreign_price_unit = self.foreign_price_unit
            # If the move is a return, use the original move's price unit.
            if self.origin_returned_move_id and self.origin_returned_move_id.sudo().stock_valuation_layer_ids:
                foreign_price_unit = self.origin_returned_move_id.stock_valuation_layer_ids[-1].foreign_price_unit
            return not self.product_id.force_currency_id.is_zero(
                foreign_price_unit) and foreign_price_unit or self.product_id.foreign_standard_price

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id,
                                       credit_account_id, svl_id, description):
        """
        """

        company_currency = self.company_id.currency_id
        force_currency_id = self.product_id.force_currency_id
        company = self.company_id or self.env.company
        date = self.date

        # open below code if we would create exchange rate form stock accounting
        # if self._is_out() and force_currency_id and company_currency != force_currency_id:
        #     foreign_value = self.product_id.foreign_standard_price * self.quantity
        #     debit_value = force_currency_id.with_context(date=self.date).compute(foreign_value, company_currency)

        res = super(StockMove, self)._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value,
                                                                    debit_account_id,
                                                                    credit_account_id, svl_id, description)

        # stock_valuation = self.env['stock.valuation.layer'].browse(svl_id)
        if force_currency_id and company_currency != force_currency_id and len(res.keys()) != 0:

            debit_amount_currency = company_currency.with_context(date=self.date).sudo()._convert(abs(debit_value),
                                                                                                  force_currency_id,
                                                                                                  company,date)
            credit_amount_currency = company_currency.with_context(date=self.date).sudo()._convert(abs(credit_value),
                                                                                                   force_currency_id,
                                                                                                   company,date)
            debit_amount_currency = debit_amount_currency if debit_value > 0 else -debit_amount_currency
            credit_amount_currency = -credit_amount_currency if credit_value > 0 else credit_amount_currency

            res['debit_line_vals'].update(
                {'currency_id': force_currency_id.id, 'amount_currency': debit_amount_currency})
            res['credit_line_vals'].update(
                {'currency_id': force_currency_id.id, 'amount_currency': credit_amount_currency})

            if credit_value != debit_value:
                # for supplier returns of product in average costing method, in anglo saxon mode
                diff_amount = debit_value - credit_value
                diff_amount_currency = company_currency.with_context(date=self.date).sudo()._convert(abs(diff_amount),
                                                                                                     force_currency_id,date)
                diff_amount_currency = -diff_amount_currency if diff_amount > 0 else diff_amount_currency
                res['price_diff_line_vals'].update(
                    {'currency_id': force_currency_id.id, 'amount_currency': diff_amount_currency})

        return res

    def product_price_update_before_done(self, forced_qty=None):
        tmpl_dict = defaultdict(lambda: 0.0)
        lot_tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        std_foreign_price_update = {}
        std_price_update_lot = {}
        for move in self:
            if not move._is_in():
                continue
            if move.with_company(move.company_id).product_id.cost_method == 'standard':
                continue
            product_tot_qty_available = move.product_id.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[
                move.product_id.id]
            rounding = move.product_id.uom_id.rounding

            valued_move_lines = move._get_in_move_lines()
            quantity_by_lot = defaultdict(float)
            if forced_qty:
                quantity_by_lot[forced_qty[0]] += forced_qty[1]
            else:
                for valued_move_line in valued_move_lines:
                    quantity_by_lot[valued_move_line.lot_id] += valued_move_line.quantity_product_uom

            qty_done = move.product_uom._compute_quantity(move.quantity, move.product_id.uom_id)
            qty = forced_qty or qty_done
            move_cost = move._get_price_unit()
            print('+++++++++++++++++++++++++++++++++++++++++', move_cost)
            if float_is_zero(product_tot_qty_available, precision_rounding=rounding) \
                    or float_is_zero(product_tot_qty_available + move.product_qty, precision_rounding=rounding) \
                    or float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                new_std_price = next(iter(move_cost.values()))
                new_foreign_std_price = move._get_foreign_price_unit()
            else:
                # Get the standard price
                amount_unit = std_price_update.get(
                    (move.company_id.id, move.product_id.id)) or move.product_id.with_company(
                    move.company_id).standard_price
                new_std_price = ((amount_unit * product_tot_qty_available) + (next(iter(move_cost.values())) * qty)) / (
                        product_tot_qty_available + qty)
                Foreign_amount_unit = std_foreign_price_update.get(
                    (move.company_id.id, move.product_id.id)) or move.product_id.foreign_standard_price
                new_foreign_std_price = ((Foreign_amount_unit * product_tot_qty_available) + (
                        move._get_foreign_price_unit() * qty)) / (product_tot_qty_available + qty)
                tmpl_dict[move.product_id.id] += qty
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write(
                {'standard_price': new_std_price})
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price

            # Update the standard price of the lot
            if not move.product_id.lot_valuated:
                continue
            for lot, qty in quantity_by_lot.items():
                qty_avail = lot.sudo().with_company(move.company_id).quantity_svl + lot_tmpl_dict[lot.id]
                if float_is_zero(qty_avail, precision_rounding=rounding) \
                        or float_is_zero(qty_avail + qty, precision_rounding=rounding):
                    new_std_price = move_cost[lot]
                else:
                    # Get the standard price
                    amount_unit = std_price_update_lot.get((move.company_id.id, lot.id)) or lot.with_company(
                        move.company_id).standard_price
                    new_std_price = ((amount_unit * qty_avail) + (move_cost[lot] * qty)) / (qty_avail + qty)
                lot_tmpl_dict[lot.id] += qty
                tmpl_dict[move.product_id.id] += qty_done
                lot.with_company(move.company_id.id).with_context(
                    disable_auto_svl=True).sudo().standard_price = new_std_price
                std_price_update_lot[move.company_id.id, lot.id] = new_std_price
                move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write(
                    {'standard_price': new_std_price, 'foreign_standard_price': new_foreign_std_price})
                move.product_id.with_context(
                    disable_auto_svl=True).sudo().foreign_standard_price = new_foreign_std_price
                std_price_update[move.company_id.id, move.product_id.id] = new_std_price
                std_foreign_price_update[move.company_id.id, move.product_id.id] = new_foreign_std_price

    # def _create_in_svl(self, forced_quantity=None):
    #     """Create a `stock.valuation.layer` from `self`.
    #
    #     :param forced_quantity: under some circunstances, the quantity to value is different than
    #         the initial demand of the move (Default value = None)
    #     Override to update foreign cost
    #     """
    #     svl_vals_list = []
    #     for move in self:
    #         move = move.with_company(move.company_id.id)
    #         valued_move_lines = move._get_in_move_lines()
    #         valued_quantity = 0
    #         for valued_move_line in valued_move_lines:
    #             valued_quantity += valued_move_line.product_uom_id._compute_quantity(
    #                 valued_move_line.qty_done, move.product_id.uom_id)
    #         # May be negative (i.e. decrease an out move).
    #         price_unit = move._get_price_unit().get('price_unit', 0.0)
    #         unit_cost = abs(price_unit)
    #         # unit_cost = abs(move._get_price_unit())
    #         unit_foreign = abs(move._get_foreign_price_unit())
    #         if move.product_id.cost_method == 'standard':
    #             unit_cost = move.product_id.standard_price
    #             unit_foreign = move.product_id.foreign_standard_price
    #         svl_vals = move.product_id._prepare_in_svl_vals(
    #             forced_quantity or valued_quantity, unit_cost, unit_foreign)
    #         svl_vals.update(move._prepare_common_svl_vals())
    #         if forced_quantity:
    #             svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
    #         svl_vals_list.append(svl_vals)
    #     return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
    #

    def _get_in_svl_vals(self, forced_quantity):
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            lines = move._get_in_move_lines()
            quantities = defaultdict(float)
            price_unit = move._get_price_unit().get('price_unit', 0.0)
            unit_cost = abs(price_unit)
            unit_foreign = abs(move._get_foreign_price_unit())
            print('uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu', unit_foreign)
            if forced_quantity:
                quantities[forced_quantity[0]] += forced_quantity[1]
            else:
                for line in lines:
                    quantities[line.lot_id] += line.quantity_product_uom

            if move.product_id.lot_valuated:
                unit_cost_map = {lot: lot.standard_price for lot in move.lot_ids}
            else:
                unit_cost_map = {None: move.product_id.standard_price}

            if move.product_id.cost_method != 'standard':
                unit_cost_map = {None: move.product_id.standard_price}
                unit_foreign = move.product_id.foreign_standard_price
                print('---------------------------------------unit_foreign',unit_foreign, unit_cost_map)

            vals = []
            if move.product_id.lot_valuated:
                for lot_id, qty in quantities.items():
                    vals.append(
                        move.product_id._prepare_in_svl_vals(
                            qty,
                            abs(unit_cost_map.get(lot_id, move.product_id.standard_price)),
                            lot=lot_id,
                            unit_foreign=unit_foreign,
                            unit_cost=unit_cost_map.get(lot_id)
                        )
                    )
                    print('vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv', vals)
            else:
                total_qty = sum(quantities.values())
                vals = [
                    move.product_id._prepare_in_svl_vals(
                        total_qty,
                        abs(unit_cost_map.get(None, move.product_id.standard_price))
                    )
                ]
                print('@@@@@@@@@@@@@@@@@@@@@@@@@',vals)
            for val in vals:
                val.update(move._prepare_common_svl_vals())
                if forced_quantity:
                    val['description'] = _('Correction of %s (modification of past move)',
                                           move.picking_id.name or move.name)

            svl_vals_list += vals

        return svl_vals_list

    def _create_out_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        Override to update foreign cost 
        """
        svl_vals_list = []
        for move in self:
            # move = move.with_context(force_company=move.company_id.id)
            valued_move_lines = move._get_out_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(
                    valued_move_line.qty_done, move.product_id.uom_id)
            if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                continue
            svl_vals = move.product_id._prepare_out_svl_vals(
                forced_quantity or valued_quantity, move.company_id)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals[
                    'description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)

    def _prepare_common_svl_vals(self):
        """When a `stock.valuation.layer` is created from a `stock.move`, we can prepare a dict of
        common vals.

        :returns: the common values when creating a `stock.valuation.layer` from a `stock.move`
        :rtype: dict
        overwrite to add foreign_currency
        """
        self.ensure_one()
        values = super(StockMove, self)._prepare_common_svl_vals()
        if self.product_id.force_currency_id:
            values['force_currency_id'] = self.product_id.force_currency_id.id
        return values


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    accounting_date = fields.Date(string="Accounting Date")

    def action_get_account_moves(self):
        self.ensure_one()
        action_ref = self.env.ref('account.action_move_journal_line')
        if not action_ref:
            return False
        action_data = action_ref.read()[0]
        action_data['domain'] = [('id', 'in', [move.account_move_ids.id for move in self.move_ids_without_package])]
        return action_data

    @api.onchange("accounting_date")
    def _onchange_accounting_date(self):
        """
        """
        for move in self.move_ids_without_package:
            if move.force_currency_id and move.company_id.currency_id and self.accounting_date:
                rate = move.company_id.currency_id._get_conversion_rate(move.force_currency_id,
                                                                        move.company_id.currency_id, move.company_id,
                                                                        self.accounting_date)
                # move.rate = move.force_currency_id and move.force_currency_id.with_context(
                #     date=self.accounting_date, force_company=move.company_id.id).rate or 0
                move.rate = rate
            move.foreign_price_unit = move._get_foreign_price_unit()
            move.price_unit = move._get_price_unit()
