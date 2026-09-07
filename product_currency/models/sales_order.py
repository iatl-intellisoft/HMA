# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL International Pvt. Ltd.
#    Copyright (C) 2018-TODAY Tech-Receptives(<http://www.iatl-sd.com>).
#
###############################################################################
from itertools import chain
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError


# class SaleOrderLine(models.Model):
#     _inherit = "sale.order.line"

# def _get_display_price(self, product):
#     old_price = super(SaleOrderLine, self)._get_display_price(product)
#     from_currency = self.product_id.force_currency_id or self.order_id.company_id.currency_id
#     new_price = from_currency.compute(old_price, self.order_id.pricelist_id.currency_id)
#     return old_price
#

class PriceList(models.Model):
    _inherit = 'product.pricelist'

    sales_team = fields.Many2many('crm.team', 'product_pricelist_crm_team_rel',
                                  'pricelist_id', 'saleteam_id', string='Sales Team')
    #
    # def _compute_price_rule(self, products_qty_partner, date=False, uom_id=False):
    #     """ Low-level method - Mono pricelist, multi products
    #     Returns: dict{product_id: (price, suitable_rule) for the given pricelist}
    #
    #     Date in context can be a date, datetime, ...
    #
    #         :param products_qty_partner: list of typles products, quantity, partner
    #         :param datetime date: validity date
    #         :param ID uom_id: intermediate unit of measure
    #     """
    #     self.ensure_one()
    #     if not date:
    #         date = self._context.get('date') or fields.Datetime.now()
    #     if not uom_id and self._context.get('uom'):
    #         uom_id = self._context['uom']
    #     if uom_id:
    #         # rebrowse with uom if given
    #         products = [item[0].with_context(uom=uom_id) for item in products_qty_partner]
    #         products_qty_partner = [(products[index], data_struct[1], data_struct[2]) for index, data_struct in
    #                                 enumerate(products_qty_partner)]
    #     else:
    #         products = [item[0] for item in products_qty_partner]
    #
    #     if not products:
    #         return {}
    #
    #     categ_ids = {}
    #     for p in products:
    #         categ = p.categ_id
    #         while categ:
    #             categ_ids[categ.id] = True
    #             categ = categ.parent_id
    #     categ_ids = list(categ_ids)
    #
    #     is_product_template = products[0]._name == "product.template"
    #     if is_product_template:
    #         prod_tmpl_ids = [tmpl.id for tmpl in products]
    #         # all variants of all products
    #         prod_ids = [p.id for p in
    #                     list(chain.from_iterable([t.product_variant_ids for t in products]))]
    #     else:
    #         prod_ids = [product.id for product in products]
    #         prod_tmpl_ids = [product.product_tmpl_id.id for product in products]
    #
    #     items = self._compute_price_rule_get_items(products_qty_partner, date, uom_id, prod_tmpl_ids, prod_ids,
    #                                                categ_ids)
    #
    #     results = {}
    #     for product, qty, partner in products_qty_partner:
    #         results[product.id] = 0.0
    #         suitable_rule = False
    #
    #         # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
    #         # An intermediary unit price may be computed according to a different UoM, in
    #         # which case the price_uom_id contains that UoM.
    #         # The final price will be converted to match `qty_uom_id`.
    #         qty_uom_id = self._context.get('uom') or product.uom_id.id
    #         qty_in_product_uom = qty
    #         if qty_uom_id != product.uom_id.id:
    #             try:
    #                 qty_in_product_uom = self.env['uom.uom'].browse([self._context['uom']])._compute_quantity(qty,
    #                                                                                                           product.uom_id)
    #             except UserError:
    #                 # Ignored - incompatible UoM in context, use default product UoM
    #                 pass
    #
    #         # if Public user try to access standard price from website sale, need to call price_compute.
    #         # TDE SURPRISE: product can actually be a template
    #         price = product.price_compute('list_price')[product.id]
    #
    #         price_uom = self.env['uom.uom'].browse([qty_uom_id])
    #         for rule in items:
    #             if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
    #                 continue
    #             if is_product_template:
    #                 if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
    #                     continue
    #                 if rule.product_id and not (
    #                         product.product_variant_count == 1 and product.product_variant_id.id == rule.product_id.id):
    #                     # product rule acceptable on template if has only one variant
    #                     continue
    #             else:
    #                 if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
    #                     continue
    #                 if rule.product_id and product.id != rule.product_id.id:
    #                     continue
    #
    #             if rule.categ_id:
    #                 cat = product.categ_id
    #                 while cat:
    #                     if cat.id == rule.categ_id.id:
    #                         break
    #                     cat = cat.parent_id
    #                 if not cat:
    #                     continue
    #
    #             if rule.base == 'pricelist' and rule.base_pricelist_id:
    #                 price_tmp = \
    #                     rule.base_pricelist_id._compute_price_rule([(product, qty, partner)], date, uom_id)[product.id][
    #                         0]  # TDE: 0 = price, 1 = rule
    #                 price = rule.base_pricelist_id.currency_id.with_context(sale=True)._convert(price_tmp, self.currency_id, self.env.company,
    #                                                                     date, round=False)
    #             else:
    #                 # if base option is public price take sale price else cost price of product
    #                 # price_compute returns the price in the context UoM, i.e. qty_uom_id
    #                 price = product.price_compute(rule.base)[product.id]
    #
    #             if price is not False:
    #                 price = rule._compute_price(price, price_uom, product, quantity=qty, partner=partner)
    #                 suitable_rule = rule
    #             break
    #         # Final price conversion into pricelist currency
    #         if suitable_rule and suitable_rule.compute_price != 'fixed' and suitable_rule.base != 'pricelist':
    #             if suitable_rule.base == 'standard_price':
    #                 cur = product.cost_currency_id
    #             else:
    #                 cur = product.force_currency_id
    #             price = cur.with_context(sale=True)._convert(price, self.currency_id, self.env.user.company_id, date,
    #                                                          round=False)
    #         if not suitable_rule:
    #             cur = product.force_currency_id
    #             price = cur.with_context(sale=True)._convert(price, self.currency_id, self.env.company, date,
    #                                                          round=False)
    #
    #         results[product.id] = (price, suitable_rule and suitable_rule.id or False)
    #
    #     return results
    #
class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'


    def _compute_price(self, product, quantity, uom, date, currency=None):
        """Compute the unit price of a product in the context of a pricelist application.

        Note: self and self.ensure_one()

        :param product: recordset of product (product.product/product.template)
        :param float qty: quantity of products requested (in given uom)
        :param uom: unit of measure (uom.uom record)
        :param datetime date: date to use for price computation and currency conversions
        :param currency: currency (for the case where self is empty)

        :returns: price according to pricelist rule or the product price, expressed in the param
                  currency, the pricelist currency or the company currency
        :rtype: float
        """
        self and self.ensure_one()  # self is at most one record
        product.ensure_one()
        uom.ensure_one()

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.ensure_one()

        # Pricelist specific values are specified according to product UoM
        # and must be multiplied according to the factor between uoms
        product_uom = product.uom_id
        if product_uom != uom:
            convert = lambda p: product_uom.with_context(sale=True)._compute_price(p, uom)
        else:
            convert = lambda p: p

        if self.compute_price == 'fixed':
            price = convert(self.fixed_price)
        elif self.compute_price == 'percentage':
            base_price = self._compute_base_price(product, quantity, uom, date, currency)
            price = (base_price - (base_price * (self.percent_price / 100))) or 0.0
        elif self.compute_price == 'formula':
            base_price = self._compute_base_price(product, quantity, uom, date, currency)
            # complete formula
            price_limit = base_price
            discount = self.price_discount if self.base != 'standard_price' else -self.price_markup
            price = base_price - (base_price * (discount / 100))
            if self.price_round:
                price = tools.float_round(price, precision_rounding=self.price_round)

            if self.price_surcharge:
                price += convert(self.price_surcharge)

            if self.price_min_margin:
                price = max(price, price_limit + convert(self.price_min_margin))

            if self.price_max_margin:
                price = min(price, price_limit + convert(self.price_max_margin))
        else:  # empty self, or extended pricelist price computation logic
            price = self._compute_base_price(product, quantity, uom, date, currency)

        return price
