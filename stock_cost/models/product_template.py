# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero, float_repr
from odoo.tools import float_is_zero, float_repr, float_round, float_compare


class ProductCategory(models.Model):
    _inherit = 'product.category'

    property_stock_account_currency_adjustment = fields.Many2one(
        'account.account', 'Stock Currency Adjustment Account', company_dependent=True,
        help="""Used in case of Stock adjustment due to currency rate difference""")

class ProductTemplate(models.Model):
    _inherit = "product.template"

    force_currency_id = fields.Many2one('res.currency', 'Force Currency')

    foreign_standard_price = fields.Float(
        'Foreign Cost', compute='_compute_foreign_standard_price',
        inverse='_set_foreign_standard_price', search='_search_foreign_standard_price',
        digits='Product Price', groups="stock_cost.group_product_cost",
        help="Cost used for stock valuation in standard price and as a first price to set in average/FIFO.")

    @api.depends('foreign_standard_price', 'standard_price')
    def _compute_deff_amount(self):
        for rec in self:
            rec.deff_amount = rec.standard_price - rec.foreign_standard_price

    @api.depends('product_variant_ids', 'product_variant_ids.standard_price')
    def _compute_foreign_standard_price(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.foreign_standard_price = template.product_variant_ids.foreign_standard_price
        for template in (self - unique_variants):
            template.foreign_standard_price = 0.0

    def _set_foreign_standard_price(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.foreign_standard_price = self.foreign_standard_price

    def _search_foreign_standard_price(self, operator, value):
        products = self.env['product.product'].search([('foreign_standard_price', operator, value)], limit=None)
        return [('id', 'in', products.mapped('product_tmpl_id').ids)]

    def price_compute(self, price_type, uom=False, currency=False, company=None):
        # TDE FIXME: delegate to template or not ? fields are reencoded here ...
        # compatibility about context keys used a bit everywhere in the code
        if not uom and self._context.get('uom'):
            uom = self.env['uom.uom'].browse(self._context['uom'])
        if not currency and self._context.get('currency'):
            currency = self.env['res.currency'].browse(self._context['currency'])

        templates = self
        if price_type in ['standard_price', 'foreign_standard_price']:
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            templates = self.with_company(company).sudo()
        if not company:
            company = self.env.company
        date = self.env.context.get('date') or fields.Date.today()

        prices = dict.fromkeys(self.ids, 0.0)
        for template in templates:
            prices[template.id] = template[price_type] or 0.0
            # yes, there can be attribute values for product template if it's not a variant YET
            # (see field product.attribute create_variant)
            if price_type == 'list_price' and self._context.get('current_attributes_price_extra'):
                # we have a list of price_extra that comes from the attribute values, we need to sum all that
                prices[template.id] += sum(self._context.get('current_attributes_price_extra'))

            if uom:
                prices[template.id] = template.uom_id._compute_price(prices[template.id], uom)

            # Convert from current user company currency to asked one
            # This is right cause a field cannot be in more than one currency
            if currency:
                prices[template.id] = template.currency_id._convert(prices[template.id], currency, company, date)

        return prices

    def write(self, vals):
        """
        Overwrite to add chatter
        """
        ARROW_RIGHT = '<span aria-label="Changed" class="fa fa-long-arrow-alt-right" role="img" title="Changed"></span>'
        for template in self:
            count = 0
            msg = '<ul>'
            if 'foreign_standard_price' in vals and 'standard_price' not in vals:
                company_currency = template.currency_id
                force_currency_id = template.force_currency_id
                standard_price = force_currency_id.with_context(
                    date=fields.Date.today()).sudo().compute(vals['foreign_standard_price'], company_currency)
                standard_price = company_currency.round(standard_price)
                vals['standard_price'] = standard_price
            if 'foreign_standard_price' in vals and vals['foreign_standard_price'] != template.foreign_standard_price:
                msg += '<li>%s: %s %s %s </li>' % (
                    'Foreign Cost', template.foreign_standard_price, ARROW_RIGHT, vals['foreign_standard_price'])
                count += 1
            if 'standard_price' in vals and vals['standard_price'] != template.standard_price:
                msg += '<li>%s: %s %s %s </li>' % (
                    'Cost', template.standard_price, ARROW_RIGHT, vals['standard_price'])
                count += 1
            msg += '</ul>'
            super(ProductTemplate, template).write(vals)
            if count > 0 and not self.env.context.get('tracking_disable', False):
                template.message_post(body=msg)

        return True

    def change_price(self):
        """ Changes the Standard Price of Product and creates an account move accordingly. """
        # self.ensure_one()
        if self._context['active_model'] == 'product.template':
            products = self.env['product.template'].browse(self._context['active_ids']).product_variant_ids
        else:
            products = self.env['product.product'].browse(self._context['active_ids'])
        for pro in products:

            pro.write({'foreign_standard_price': pro.foreign_standard_price})
        # products._change_foreign_standard_price(self.new_price, counterpart_account_id=self.counterpart_account_id.id)
        return {'type': 'ir.actions.act_window_close'}


class ProductProduct(models.Model):
    _inherit = "product.product"

    foreign_standard_price = fields.Float(
        'Foreign Cost', company_dependent=True,
        digits='Product Price',
        groups="stock_cost.group_product_cost",
        help="Cost used for stock valuation in standard price and as a first price to set in average/fifo. "
             "Also used as a base price for pricelists. "
             "Expressed in the default unit of measure of the product.")
    foreign_value_svl = fields.Float(compute='_compute_value_svl', compute_sudo=True)


    def write(self, vals):
        if 'foreign_standard_price' in vals and not self.env.context.get('disable_auto_svl'):
            self.filtered(lambda p: p.cost_method != 'fifo')._change_foreign_standard_price(
                vals['foreign_standard_price'])
        ARROW_RIGHT = '<span aria-label="Changed" class="fa fa-long-arrow-alt-right" role="img" title="Changed"></span>'
        for product in self:
            count = 0
            msg = '<ul>'
            if 'foreign_standard_price' in vals and 'standard_price' not in vals:
                company_currency = product.currency_id
                force_currency_id = product.force_currency_id
                # standard_price = force_currency_id.with_context(
                #     date=fields.Date.today()).sudo().compute(vals['foreign_standard_price'], company_currency)
                standard_price = force_currency_id._convert(
                    from_amount=vals['foreign_standard_price'],
                    to_currency=company_currency,
                    company=self.company_id,
                    date=fields.Date.today()
                )

                standard_price = company_currency.round(standard_price)
                vals['standard_price'] = standard_price
            if 'foreign_standard_price' in vals and vals['foreign_standard_price'] != product.foreign_standard_price:
                msg += '<li>%s: %s %s %s </li>' % (
                    'Foreign Cost', product.foreign_standard_price, ARROW_RIGHT, vals['foreign_standard_price'])
                count += 1
            if 'standard_price' in vals and vals['standard_price'] != product.standard_price:
                msg += '<li>%s: %s %s %s </li>' % (
                    'Cost', product.standard_price, ARROW_RIGHT, vals['standard_price'])
                count += 1
            msg += '</ul>'
            super(ProductProduct, product).write(vals)
            if count > 0 and not self.env.context.get('tracking_disable', False):
                product.message_post(body=msg)

        return True

    # def _prepare_valuation_layer_field_values(self, aggregates):
    #     self.ensure_one()
    #
    #     value_sum, quantity_sum, foreign_value = aggregates
    #
    #     value_svl = self.env.company.currency_id.round(value_sum)
    #     avg_cost = 0
    #     if not float_is_zero(quantity_sum, precision_rounding=self.uom_id.rounding):
    #         avg_cost = value_svl / quantity_sum
    #
    #     return {
    #         "value_svl": value_svl,
    #         "quantity_svl": quantity_sum,
    #         "avg_cost": avg_cost,
    #         "total_value": avg_cost * self.sudo(False).qty_available if avg_cost else 0,
    #         "foreign_value_svl": foreign_value,
    #     }

    @api.depends('stock_valuation_layer_ids')
    @api.depends_context('to_date', 'company')
    def _compute_value_svl(self):
        self.company_currency_id = self.env.company.currency_id

        # الحصول على القيم المجمعة من _get_valuation_layer_groups
        valuation_layer_groups = self._get_valuation_layer_groups()  # [(product, value, quantity), ...]

        # تحويل القائمة إلى dictionary لكل منتج
        group_mapping = {product: (value, quantity) for product, value, quantity in valuation_layer_groups}

        for product in self:
            value, quantity = group_mapping.get(product._origin, (0.0, 0.0))

            # حساب foreign_value_svl من stock_valuation_layer_ids إذا كان force_currency_id موجود
            foreign_value = 0.0
            if product.force_currency_id:
                # اجمع كل foreign_value من الـ stock valuation layers قبل to_date إذا موجود
                to_date = self.env.context.get('to_date')
                svl = product.stock_valuation_layer_ids
                if to_date:
                    to_date_dt = fields.Datetime.to_datetime(to_date)
                    svl = svl.filtered(lambda l: l.create_date <= to_date_dt)
                foreign_value = sum(svl.mapped('foreign_value'))
                foreign_value = product.force_currency_id.round(foreign_value)

            product.foreign_value_svl = foreign_value

            # تحديث value_svl و quantity_svl باستخدام _prepare_valuation_layer_field_values
            vals = product._prepare_valuation_layer_field_values((value, quantity))
            product.update(vals)
    # @api.depends('stock_valuation_layer_ids')
    # @api.depends_context('to_date', 'company')
    # def _compute_value_svl(self):
    #     """ Overwrite to compute foreign_value_svl
    #     Compute `value_svl` and `quantity_svl` and `foreign_value_svl`."""
    #     company_id = self.env.company.id
    #     domain = [
    #         ('product_id', 'in', self.ids),
    #         ('company_id', '=', company_id),
    #     ]
    #     if self.env.context.get('to_date'):
    #         to_date = fields.Datetime.to_datetime(self.env.context['to_date'])
    #         domain.append(('create_date', '<=', to_date))
    #     groups = self.env['stock.valuation.layer'].read_group(
    #         domain, ['value:sum', 'foreign_value:sum', 'quantity:sum'], ['product_id'])
    #     products = self.browse()
    #     for group in groups:
    #         product = self.browse(group['product_id'][0])
    #         product.value_svl = self.env.company.currency_id.round(
    #             group['value'])
    #         product.quantity_svl = group['quantity']
    #         product.foreign_value_svl = product.force_currency_id and product.force_currency_id.round(
    #             group['foreign_value'])
    #         products |= product
    #     remaining = (self - products)
    #     remaining.value_svl = 0
    #     remaining.foreign_value_svl = 0
    #     remaining.quantity_svl = 0

    # -------------------------------------------------------------------------
    # SVL creation helpers
    # -------------------------------------------------------------------------
    def _prepare_in_svl_vals(self, quantity, unit_cost, lot=False, foreign_price_unit=False):
        """Prepare the values for a stock valuation layer created by a receipt.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :param unit_cost: the unit cost to value `quantity`
        :return: values to use in a call to create
        :rtype: dict
        """
        self.ensure_one()
        foreign_price_unit = foreign_price_unit if foreign_price_unit else self.foreign_standard_price

        company_id = self.env.context.get('force_company', self.env.company.id)
        company = self.env['res.company'].browse(company_id)
        value = company.currency_id.round(unit_cost * quantity)
        return {
            'product_id': self.id,
            'value': value,
            'unit_cost': unit_cost,
            'quantity': quantity,
            'remaining_qty': quantity,
            'remaining_value': value,
            'company_id': company_id,
            'lot_id': lot.id if lot else False,
            'foreign_value': quantity * foreign_price_unit,
            'foreign_price_unit': foreign_price_unit,
            'force_currency_id': self.force_currency_id.id,
        }

    def _prepare_out_svl_vals(self, quantity, company, lot=False):
        """Prepare the values for a stock valuation layer created by a delivery.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :return: values to use in a call to create
        :rtype: dict
        """
        self.ensure_one()
        company_id = self.env.context.get('force_company', self.env.company.id)
        company = self.env['res.company'].browse(company_id)
        currency = company.currency_id
        # Quantity is negative for out valuation layers.
        quantity = -1 * quantity
        cost = self.standard_price
        if lot and lot.sudo().stock_valuation_layer_ids:
            cost = lot.standard_price
        vals = {
            'product_id': self.id,
            'value': currency.round(quantity * cost),
            'unit_cost': cost,
            'quantity': quantity,
            'foreign_value': quantity * self.foreign_standard_price,
            'foreign_price_unit': self.foreign_standard_price,
            'force_currency_id': self.force_currency_id.id,
            'lot_id': lot.id if lot else False,
        }
        fifo_vals = self._run_fifo(abs(quantity), company, lot=lot)
        vals['remaining_qty'] = fifo_vals.get('remaining_qty')
        # In case of AVCO, fix rounding issue of standard price when needed.
        if self.product_tmpl_id.cost_method == 'average' and not float_is_zero(self.quantity_svl,
                                                                               precision_rounding=self.uom_id.rounding):
            rounding_error = currency.round(
                (cost * self.quantity_svl - self.value_svl) * abs(quantity / self.quantity_svl)
            )

            # If it is bigger than the (smallest number of the currency * quantity) / 2,
            # then it isn't a rounding error but a stock valuation error, we shouldn't fix it under the hood ...
            threshold = currency.round(max((abs(quantity) * currency.rounding) / 2, currency.rounding))
            foreign_currency = self.force_currency_id
            foreign_rounding_error = foreign_currency.round(
                self.foreign_standard_price * self.quantity_svl - self.foreign_value_svl
            )
            if foreign_rounding_error and abs(foreign_rounding_error) <= (
                    abs(quantity) * foreign_currency.rounding
            ) / 2:
                vals['foreign_value'] += foreign_rounding_error
            if rounding_error and abs(rounding_error) <= threshold:
                vals['value'] += rounding_error
                vals['rounding_adjustment'] = '\nRounding Adjustment: %s%s %s' % (
                    '+' if rounding_error > 0 else '',
                    float_repr(rounding_error, precision_digits=currency.decimal_places),
                    currency.symbol
                )
        if self.product_tmpl_id.cost_method == 'fifo':
            vals.update(fifo_vals)
        return vals

    # def _prepare_out_svl_vals(self, quantity, company, lot=False):
    #     self.ensure_one()
    #
    #     # Quantity is negative for out valuation layers.
    #     quantity = -1 * quantity
    #
    #     vals = {
    #         'product_id': self.id,
    #         'value': quantity * self.standard_price,
    #         'unit_cost': self.standard_price,
    #         'quantity': quantity,
    #         'foreign_value': quantity * self.foreign_standard_price,
    #         'foreign_price_unit': self.foreign_standard_price,
    #         'force_currency_id': self.force_currency_id.id,
    #     }
    #
    #     if self.cost_method in ('average', 'fifo'):
    #         fifo_vals = self._run_fifo(abs(quantity), company)
    #         vals['remaining_qty'] = fifo_vals.get('remaining_qty')
    #
    #         if self.cost_method == 'average':
    #             currency = self.env.company.currency_id
    #             rounding_error = currency.round(
    #                 self.standard_price * self.quantity_svl - self.value_svl
    #             )
    #             if rounding_error and abs(rounding_error) <= (abs(quantity) * currency.rounding) / 2:
    #                 vals['value'] += rounding_error
    #
    #             foreign_currency = self.force_currency_id
    #             foreign_rounding_error = foreign_currency.round(
    #                 self.foreign_standard_price * self.quantity_svl - self.foreign_value_svl
    #             )
    #             if foreign_rounding_error and abs(foreign_rounding_error) <= (
    #                     abs(quantity) * foreign_currency.rounding
    #             ) / 2:
    #                 vals['foreign_value'] += foreign_rounding_error
    #
    #         if self.cost_method == 'fifo':
    #             vals.update(fifo_vals)
    #
    #     return vals

    def _change_foreign_standard_price(self, new_price):
        """Helper to create the stock valuation layers and the account moves
        after an update of standard price.
        we defined new function for forign price to make sure the new price is foreign cost and not standard price
        as in _change_standard_price as this called in write function

        :param new_price: new foreign standard price
        """
        # Handle stock valuation layers.

        if self.filtered(lambda p: p.valuation == 'real_time') and not self.env['stock.valuation.layer'].check_access_rights('read', raise_exception=False):
            raise UserError(
                _("You cannot update the cost of a product in automated valuation as it leads to the creation of a journal entry, for which you don't have the access rights."))

        svl_vals_list = []
        company_id = self.env.company
        for product in self:
            if product.cost_method not in ('standard', 'average'):
                continue
            quantity_svl = product.sudo().quantity_svl
            if float_is_zero(quantity_svl, precision_rounding=product.uom_id.rounding):
                continue
            diff = new_price - product.foreign_standard_price
            # transfer from force_currency to company currency
            company_currency = product.currency_id
            force_currency_id = product.force_currency_id
            date = self.env.context.get('date') or fields.Date.today()
            new_company_price = force_currency_id.with_context(date=fields.Date.today()).sudo()._convert(new_price, company_currency, product.company_id, date)
            company_currency_diff = new_company_price - product.standard_price
            value = company_id.currency_id.round(quantity_svl * company_currency_diff)
            foreign_value = force_currency_id.round(quantity_svl * diff)
            if force_currency_id.is_zero(foreign_value):
                continue


            svl_vals = {
                'company_id': company_id.id,
                'product_id': product.id,
                'description': _('Product value manually modified (from %s to %s)') % (product.foreign_standard_price, new_price),
                'value': value,
                'foreign_value': foreign_value,
                'force_currency_id': force_currency_id and force_currency_id.id or False,
                'quantity': 0,
            }
            svl_vals_list.append(svl_vals)
        stock_valuation_layers = self.env['stock.valuation.layer'].sudo().create(
            svl_vals_list)

        # Handle account moves.
        product_accounts = {
            product.id: product.product_tmpl_id.get_product_accounts() for product in self}
        am_vals_list = []
        for stock_valuation_layer in stock_valuation_layers:
            product = stock_valuation_layer.product_id
            value = stock_valuation_layer.value
            amount_currency = 0
            currency_id = False

            if product.type != 'product' or product.valuation != 'real_time':
                continue

            # Sanity check.
            if not product_accounts[product.id].get('expense'):
                raise UserError(
                    _('You must set a counterpart account on your product category.'))
            if not product_accounts[product.id].get('stock_valuation'):
                raise UserError(
                    _('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))

            if value < 0:
                debit_account_id = product_accounts[product.id]['expense'].id
                credit_account_id = product_accounts[product.id]['stock_valuation'].id
            else:
                debit_account_id = product_accounts[product.id]['stock_valuation'].id
                credit_account_id = product_accounts[product.id]['expense'].id

            if force_currency_id and force_currency_id != company_currency:
                amount_currency = abs(foreign_value)
                currency_id = force_currency_id.id
                amount = force_currency_id.with_context(date=fields.Date.today()).sudo().compute(
                    abs(foreign_value), company_currency)
            else:
                amount = abs(value)

            move_vals = {
                'journal_id': product_accounts[product.id]['stock_journal'].id,
                'company_id': company_id.id,
                'ref': product.default_code,
                'stock_valuation_layer_ids': [(6, None, [stock_valuation_layer.id])],
                'move_type': 'entry',
                'line_ids': [(0, 0, {
                    'name': _('User %s changed cost from %s to %s - %s') % (self.env.user.name, product.foreign_standard_price, new_price, product.display_name),
                    'account_id': debit_account_id,
                    'debit': abs(value),
                    'credit': 0,
                    'currency_id': currency_id,
                    'amount_currency': amount_currency,
                    'product_id': product.id,
                }), (0, 0, {
                    'name': _('User %s changed cost from %s to %s - %s') % (self.env.user.name, product.foreign_standard_price, new_price, product.display_name),
                    'account_id': credit_account_id,
                    'debit': 0,
                    'credit': abs(value),
                    'currency_id': currency_id,
                    'amount_currency': amount_currency * -1,
                    'product_id': product.id,
                })],
            }
            am_vals_list.append(move_vals)

        account_moves = self.env['account.move'].sudo().create(am_vals_list)
        if account_moves:
            account_moves._post()

    def _change_standard_price(self, new_price):
        """Overwrite to prevent create svl based on change in standard price, we need this for foreign cost and/
        we can not control as it is called from write function
        """
        # Handle stock valuation layers.

        # if self.filtered(lambda p: p.valuation == 'real_time') and not self.env['stock.valuation.layer'].check_access_rights('read', raise_exception=False):
        #     raise UserError(
        #         _("You cannot update the cost of a product in automated valuation as it leads to the creation of a journal entry, for which you don't have the access rights."))

        # svl_vals_list = []
        # company_id = self.env.company
        # for product in self:
        #     if product.cost_method not in ('standard', 'average'):
        #         continue
        #     quantity_svl = product.sudo().quantity_svl
        #     if float_is_zero(quantity_svl, precision_rounding=product.uom_id.rounding):
        #         continue
        #     diff = new_price - product.standard_price
        #     value = company_id.currency_id.round(quantity_svl * diff)
        #     if company_id.currency_id.is_zero(value):
        #         continue

        #     svl_vals = {
        #         'company_id': company_id.id,
        #         'product_id': product.id,
        #         'description': _('Product value manually modified (from %s to %s)') % (product.standard_price, new_price),
        #         'value': value,
        #         'quantity': 0,
        #     }
        #     svl_vals_list.append(svl_vals)
        # stock_valuation_layers = self.env['stock.valuation.layer'].sudo().create(
        #     svl_vals_list)

        # # Handle account moves.
        # product_accounts = {
        #     product.id: product.product_tmpl_id.get_product_accounts() for product in self}
        # am_vals_list = []
        # for stock_valuation_layer in stock_valuation_layers:
        #     product = stock_valuation_layer.product_id
        #     value = stock_valuation_layer.value

        #     if product.type != 'product' or product.valuation != 'real_time':
        #         continue

        #     # Sanity check.
        #     if not product_accounts[product.id].get('expense'):
        #         raise UserError(
        #             _('You must set a counterpart account on your product category.'))
        #     if not product_accounts[product.id].get('stock_valuation'):
        #         raise UserError(
        #             _('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))

        #     if value < 0:
        #         debit_account_id = product_accounts[product.id]['expense'].id
        #         credit_account_id = product_accounts[product.id]['stock_valuation'].id
        #     else:
        #         debit_account_id = product_accounts[product.id]['stock_valuation'].id
        #         credit_account_id = product_accounts[product.id]['expense'].id

        #     move_vals = {
        #         'journal_id': product_accounts[product.id]['stock_journal'].id,
        #         'company_id': company_id.id,
        #         'ref': product.default_code,
        #         'stock_valuation_layer_ids': [(6, None, [stock_valuation_layer.id])],
        #         'move_type': 'entry',
        #         'line_ids': [(0, 0, {
        #             'name': _(
        #                 '%(user)s changed cost from %(previous)s to %(new_price)s - %(product)s',
        #                 user=self.env.user.name,
        #                 previous=product.standard_price,
        #                 new_price=new_price,
        #                 product=product.display_name
        #             ),
        #             'account_id': debit_account_id,
        #             'debit': abs(value),
        #             'credit': 0,
        #             'product_id': product.id,
        #         }), (0, 0, {
        #             'name': _(
        #                 '%(user)s changed cost from %(previous)s to %(new_price)s - %(product)s',
        #                 user=self.env.user.name,
        #                 previous=product.standard_price,
        #                 new_price=new_price,
        #                 product=product.display_name
        #             ),
        #             'account_id': credit_account_id,
        #             'debit': 0,
        #             'credit': abs(value),
        #             'product_id': product.id,
        #         })],
        #     }
        #     am_vals_list.append(move_vals)

        # account_moves = self.env['account.move'].sudo().create(am_vals_list)
        # if account_moves:
        #     account_moves._post()
        return True
    def _run_fifo(self, quantity, company, lot=False):
        self.ensure_one()

        # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
        qty_to_take_on_candidates = quantity
        candidates = self._get_fifo_candidates(company, lot=lot)
        new_standard_price = 0
        new_foreign_standard_price = 0
        tmp_value = 0  # to accumulate the value taken on the candidates
        foreign_tmp_value = 0  # to accumulate the value taken on the candidates
        for candidate in candidates:
            qty_taken_on_candidate = self._get_qty_taken_on_candidate(qty_to_take_on_candidates, candidate)

            candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
            new_standard_price = candidate_unit_cost
            value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
            value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)

            new_remaining_value = candidate.remaining_value - value_taken_on_candidate
            # update foreign value
            candidate_foreign_unit_cost = candidate.foreign_remaining_value / candidate.remaining_qty
            new_foreign_standard_price = candidate_foreign_unit_cost
            foreign_value_taken_on_candidate = qty_taken_on_candidate * \
                                               candidate_foreign_unit_cost
            foreign_value_taken_on_candidate = candidate.product_id.force_currency_id.round(
                foreign_value_taken_on_candidate)
            new_foreign_remaining_value = candidate.foreign_remaining_value - \
                                          foreign_value_taken_on_candidate
            candidate_vals = {
                'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                'remaining_value': new_remaining_value,
                'foreign_remaining_value': new_foreign_remaining_value,
            }

            candidate.write(candidate_vals)

            qty_to_take_on_candidates -= qty_taken_on_candidate
            tmp_value += value_taken_on_candidate
            foreign_tmp_value += foreign_value_taken_on_candidate
            if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                if float_is_zero(candidate.remaining_qty, precision_rounding=self.uom_id.rounding):
                    next_candidates = candidates.filtered(lambda svl: svl.remaining_qty > 0)
                    new_standard_price = next_candidates and next_candidates[0].unit_cost or new_standard_price
                    new_foreing_standard_price = next_candidates and next_candidates[0].foreign_price_unit or new_foreign_standard_price
                break

        # Update the standard price with the price of the last used candidate, if any.
        if new_standard_price and self.cost_method == 'fifo':
                self.sudo().with_company(company.id).with_context(
                    disable_auto_svl=True).standard_price = new_standard_price
                # Update the foreign price with the price of the last used candidate, if any.
        if new_foreign_standard_price and self.cost_method == 'fifo':
            self.sudo().with_company(company.id).with_context(
                disable_auto_svl=True).foreign_standard_price = new_foreign_standard_price

        # If there's still quantity to value but we're out of candidates, we fall in the
        # negative stock use case. We chose to value the out move at the price of the
        # last out and a correction entry will be made once `_fifo_vacuum` is called.
        vals = {}
        if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
            vals = {
                'value': -tmp_value,
                'unit_cost': tmp_value / quantity,
                'foreign_value': -foreign_tmp_value,
                'foreign_price_unit': foreign_tmp_value / quantity,
            }
        else:
            assert qty_to_take_on_candidates > 0
            last_fifo_price = new_standard_price or self.standard_price
            last_fifo_foreign_price = new_foreign_standard_price or self.foreign_standard_price
            negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
            tmp_value += abs(negative_stock_value)
            vals = {
                'remaining_qty': -qty_to_take_on_candidates,
                'value': -tmp_value,
                'unit_cost': last_fifo_price,
                'foreign_value': -foreign_tmp_value,
                'foreign_price_unit': last_fifo_foreign_price,
            }
        return vals


    # def _run_fifo(self, quantity, company):
    #     self.ensure_one()
    #
    #     # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
    #     qty_to_take_on_candidates = quantity
    #     candidates = self.env['stock.valuation.layer'].sudo().search([
    #         ('product_id', '=', self.id),
    #         ('remaining_qty', '>', 0),
    #         ('company_id', '=', company.id),
    #     ])
    #     new_standard_price = 0
    #     new_foreign_standard_price = 0
    #     tmp_value = 0  # to accumulate the value taken on the candidates
    #     foreign_tmp_value = 0  # to accumulate the value taken on the candidates
    #     for candidate in candidates:
    #         qty_taken_on_candidate = min(qty_to_take_on_candidates, candidate.remaining_qty)
    #
    #         candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
    #         new_standard_price = candidate_unit_cost
    #         value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
    #         value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
    #         new_remaining_value = candidate.remaining_value - value_taken_on_candidate
    #         # update foreign value
    #         candidate_foreign_unit_cost = candidate.foreign_remaining_value / candidate.remaining_qty
    #         new_foreign_standard_price = candidate_foreign_unit_cost
    #         foreign_value_taken_on_candidate = qty_taken_on_candidate * \
    #             candidate_foreign_unit_cost
    #         foreign_value_taken_on_candidate = candidate.product_id.force_currency_id.round(
    #             foreign_value_taken_on_candidate)
    #         new_foreign_remaining_value = candidate.foreign_remaining_value - \
    #             foreign_value_taken_on_candidate
    #
    #         candidate_vals = {
    #             'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
    #             'remaining_value': new_remaining_value,
    #             'foreign_remaining_value': new_foreign_remaining_value,
    #         }
    #
    #         candidate.write(candidate_vals)
    #
    #         qty_to_take_on_candidates -= qty_taken_on_candidate
    #         tmp_value += value_taken_on_candidate
    #
    #         foreign_tmp_value += foreign_value_taken_on_candidate
    #         if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
    #             if float_is_zero(candidate.remaining_qty, precision_rounding=self.uom_id.rounding):
    #                 next_candidates = candidates.filtered(lambda svl: svl.remaining_qty > 0)
    #                 new_standard_price = next_candidates and next_candidates[0].unit_cost or new_standard_price
    #                 new_foreing_standard_price = next_candidates and next_candidates[0].foreign_price_unit or new_foreign_standard_price
    #             break
    #
    #     # Update the standard price with the price of the last used candidate, if any.
    #     if new_standard_price and self.cost_method == 'fifo':
    #         self.sudo().with_company(company.id).with_context(disable_auto_svl=True).standard_price = new_standard_price
    #
    #
    #     # Update the foreign price with the price of the last used candidate, if any.
    #     if new_foreign_standard_price and self.cost_method == 'fifo':
    #         self.sudo().with_company(company.id).with_context(disable_auto_svl=True).foreign_standard_price = new_foreign_standard_price
    #
    #     # If there's still quantity to value but we're out of candidates, we fall in the
    #     # negative stock use case. We chose to value the out move at the price of the
    #     # last out and a correction entry will be made once `_fifo_vacuum` is called.
    #     vals = {}
    #     if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
    #         vals = {
    #             'value': -tmp_value,
    #             'unit_cost': tmp_value / quantity,
    #             'foreign_value': -foreign_tmp_value,
    #             'foreign_price_unit': foreign_tmp_value / quantity,
    #         }
    #     else:
    #         assert qty_to_take_on_candidates > 0
    #         last_fifo_price = new_standard_price or self.standard_price
    #         last_fifo_foreign_price = new_foreign_standard_price or self.foreign_standard_price
    #         negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
    #         tmp_value += abs(negative_stock_value)
    #         vals = {
    #             'remaining_qty': -qty_to_take_on_candidates,
    #             'value': -tmp_value,
    #             'unit_cost': last_fifo_price,
    #             'foreign_value': -foreign_tmp_value,
    #             'foreign_price_unit': last_fifo_foreign_price,
    #         }
    #     return vals

    def _run_fifo_vacuum(self, company=None):
        """Compensate layer valued at an estimated price with the price of future receipts
        if any. If the estimated price is equals to the real price, no layer is created but
        the original layer is marked as compensated.

        :param company: recordset of `res.company` to limit the execution of the vacuum
        """
        if company is None:
            company = self.env.company
        for rec in self:
            rec.ensure_one()
            svls_to_vacuum = rec.env['stock.valuation.layer'].sudo().search([
                ('product_id', '=', rec.id),
                ('remaining_qty', '<', 0),
                ('stock_move_id', '!=', False),
                ('company_id', '=', company.id),
            ], order='create_date, id')
            for svl_to_vacuum in svls_to_vacuum:
                domain = [
                    ('company_id', '=', svl_to_vacuum.company_id.id),
                    ('product_id', '=', rec.id),
                    ('remaining_qty', '>', 0),
                    '|',
                    ('create_date', '>', svl_to_vacuum.create_date),
                    '&',
                    ('create_date', '=', svl_to_vacuum.create_date),
                    ('id', '>', svl_to_vacuum.id)
                ]
                candidates = rec.env['stock.valuation.layer'].sudo().search(domain)
                if not candidates:
                    break
                qty_to_take_on_candidates = abs(svl_to_vacuum.remaining_qty)
                qty_taken_on_candidates = 0
                tmp_value = 0
                foreign_tmp_value = 0
                for candidate in candidates:
                    qty_taken_on_candidate = min(candidate.remaining_qty, qty_to_take_on_candidates)
                    qty_taken_on_candidates += qty_taken_on_candidate

                    candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
                    value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
                    value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
                    new_remaining_value = candidate.remaining_value - value_taken_on_candidate

                    # update foreign value
                    candidate_foreign_unit_cost = candidate.foreign_remaining_value / candidate.remaining_qty
                    foreign_value_taken_on_candidate = qty_taken_on_candidate * candidate_foreign_unit_cost
                    foreign_value_taken_on_candidate = candidate.product_id.force_currency_id.round(
                        foreign_value_taken_on_candidate)
                    new_foreign_remaining_value = candidate.foreign_remaining_value - \
                        foreign_value_taken_on_candidate

                    candidate_vals = {
                        'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                        'remaining_value': new_remaining_value,
                        'foreign_remaining_value': new_foreign_remaining_value,
                    }
                    candidate.write(candidate_vals)

                    qty_to_take_on_candidates -= qty_taken_on_candidate
                    tmp_value += value_taken_on_candidate
                    foreign_tmp_value += foreign_value_taken_on_candidate
                    if float_is_zero(qty_to_take_on_candidates, precision_rounding=rec.uom_id.rounding):
                        break

                # Get the estimated value we will correct.
                remaining_value_before_vacuum = svl_to_vacuum.unit_cost * qty_taken_on_candidates
                new_remaining_qty = svl_to_vacuum.remaining_qty + qty_taken_on_candidates
                corrected_value = remaining_value_before_vacuum - tmp_value
                # Get the estimated foreign value we will correct
                foreign_remaining_value_before_vacuum = svl_to_vacuum.foreign_price_unit * qty_taken_on_candidates
                foreign_corrected_value = foreign_remaining_value_before_vacuum - foreign_tmp_value
                svl_to_vacuum.write({
                    'remaining_qty': new_remaining_qty,
                })

                # Don't create a layer or an accounting entry if the corrected value is zero.
                if svl_to_vacuum.currency_id.is_zero(corrected_value):
                    continue

                corrected_value = svl_to_vacuum.currency_id.round(corrected_value)
                foreign_corrected_value = svl_to_vacuum.product_id.force_currency_id.round(
                    foreign_corrected_value)
                move = svl_to_vacuum.stock_move_id
                vals = {
                    'product_id': rec.id,
                    'value': corrected_value,
                    'unit_cost': 0,
                    'foreign_value': foreign_corrected_value,
                    'foreign_price_unit': 0,
                    'force_currency_id': rec.force_currency_id and rec.force_currency_id.id or False,
                    'quantity': 0,
                    'remaining_qty': 0,
                    'stock_move_id': move.id,
                    'company_id': move.company_id.id,
                    'description': 'Revaluation of %s (negative inventory)' % move.picking_id.name or move.name,
                    'stock_valuation_layer_id': svl_to_vacuum.id,
                }
                vacuum_svl = rec.env['stock.valuation.layer'].sudo().create(vals)

                # Create the account move.
                if rec.valuation != 'real_time':
                    continue
                vacuum_svl.stock_move_id._account_entry_move(
                    vacuum_svl.quantity, vacuum_svl.description, vacuum_svl.id, vacuum_svl.value
                )
                # Create the related expense entry
                rec._create_fifo_vacuum_anglo_saxon_expense_entry(vacuum_svl, svl_to_vacuum)

                # If some negative stock were fixed, we need to recompute the standard price.
                product = rec.with_company(company.id)
                if product.cost_method == 'average' and not float_is_zero(product.quantity_svl, precision_rounding=rec.uom_id.rounding):
                    product.sudo().with_context(disable_auto_svl=True).write({'standard_price': product.value_svl / product.quantity_svl,
                         'foreign_standard_price': product.foreign_value_svl / product.quantity_svl})



    # -------------------------------------------------------------------------
    # Anglo saxon helpers
    # -------------------------------------------------------------------------

    def price_compute(self, price_type, uom=False, currency=False, company=None):
        # TDE FIXME: delegate to template or not ? fields are reencoded here ...
        # compatibility about context keys used a bit everywhere in the code
        if not uom and self._context.get('uom'):
            uom = self.env['uom.uom'].browse(self._context['uom'])
        if not currency and self._context.get('currency'):
            currency = self.env['res.currency'].browse(self._context['currency'])

        products = self
        if price_type in ['standard_price', 'foreign_standard_price']:
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            products = self.with_company(company or self.env.company).sudo()

        prices = dict.fromkeys(self.ids, 0.0)
        for product in products:
            prices[product.id] = product[price_type] or 0.0
            if price_type == 'list_price':
                prices[product.id] += product.price_extra
                # we need to add the price from the attributes that do not generate variants
                # (see field product.attribute create_variant)
                if self._context.get('no_variant_attributes_price_extra'):
                    # we have a list of price_extra that comes from the attribute values, we need to sum all that
                    prices[product.id] += sum(self._context.get('no_variant_attributes_price_extra'))

            if uom:
                prices[product.id] = product.uom_id._compute_price(prices[product.id], uom)

            # Convert from current user company currency to asked one
            # This is right cause a field cannot be in more than one currency
            if currency:
                prices[product.id] = product.currency_id._convert(
                    prices[product.id], currency, product.company_id, fields.Date.today())

        return prices


class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    base = fields.Selection([
        ('list_price', 'Public Price'),
        ('standard_price', 'Cost'),
        ('pricelist', 'Other Pricelist'),
        ('foreign_standard_price', 'Foreign Cost')
    ], "Based on",
        default='list_price', required=True,
        help='Base price for computation.\n'
             'Public Price: The base price will be the Sale/public Price.\n'
             'Cost Price : The base price will be the cost price.\n'
             'Other Pricelist : Computation of the base price based on another Pricelist.')
