# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Always display the quotation in the company's own currency,
    # regardless of which pricelist is selected.
    currency_id = fields.Many2one(
        'res.currency',
        compute='_compute_currency_id',
        store=True,
        readonly=False,
        ondelete='restrict',
    )

    sale_currency_rate = fields.Float(
        "Sale Currency Rate",
        compute='_compute_sale_currency_rate',
        store=True,
        digits=(12, 6),
        readonly=True,
        help='The sale rate of the pricelist currency relative to the company currency '
             'at the date of the order.',
    )

    @api.depends('company_id', 'pricelist_id')
    def _compute_currency_id(self):
        """Force the order currency to always be the company currency."""
        for order in self:
            order.currency_id = order.company_id.currency_id

    @api.depends('pricelist_id', 'date_order', 'company_id')
    def _compute_sale_currency_rate(self):
        """
        Show the sale rate of the pricelist currency against the company currency.
        This is informational — 1.0 when pricelist is already in company currency.
        """
        for order in self:
            pricelist_currency = (
                order.pricelist_id.currency_id if order.pricelist_id
                else order.company_id.currency_id
            )
            if pricelist_currency == order.company_id.currency_id:
                order.sale_currency_rate = 1.0
            else:
                order.sale_currency_rate = (
                    self.env['res.currency'].sudo()._get_conversion_sale_rate(
                        order.company_id.currency_id,
                        pricelist_currency,
                        order.company_id,
                        order.date_order or fields.Datetime.now(),
                    ) or 1.0
                )


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_display_price(self):
        """
        Return the price in company currency, converted at the sale rate to the
        pricelist currency.

        Because order.currency_id is now forced to the company currency, we pass
        pricelist_currency explicitly so the sale-rate conversion still applies:
            company_currency._convert(price, pricelist_currency)
            = price × (rates[company] / rates[pricelist])
        e.g. 100 USD × 550 SDG/USD = 55,000 SDG
        """
        price = super()._get_display_price()
        company_currency = self.order_id.company_id.currency_id
        pricelist = self.order_id.pricelist_id
        pricelist_currency = pricelist.currency_id if pricelist else company_currency

        return company_currency.with_context(sale=True)._convert(
            price,
            pricelist_currency,
            self.order_id.company_id,
            self.order_id.date_order or fields.Date.today(),
            round=False,
        )


class PriceList(models.Model):
    _inherit = 'product.pricelist'

    def _compute_price_rule(
            self, products, quantity, currency=None, uom=None, date=False, compute_price=True,
            **kwargs
    ):
        """ Low-level method - Mono pricelist, multi products
        Returns: dict{product_id: (price, suitable_rule) for the given pricelist}

        Note: self and self.ensure_one()

        :param products: recordset of products (product.product/product.template)
        :param float quantity: quantity of products requested (in given uom)
        :param currency: record of currency (res.currency)
                         note: currency.ensure_one()
        :param uom: unit of measure (uom.uom record)
            If not specified, prices returned are expressed in product uoms
        :param date: date to use for price computation and currency conversions
        :type date: date or datetime
        :param bool compute_price: whether the price should be computed (default: True)

        :returns: product_id: (price, pricelist_rule)
        :rtype: dict
        """
        self and self.ensure_one()  # self is at most one record

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.ensure_one()

        if not products:
            return {}

        if not date:
            # Used to fetch pricelist rules and currency rates
            date = fields.Datetime.now()

        # Fetch all rules potentially matching specified products/templates/categories and date
        rules = self._get_applicable_rules(products, date, **kwargs)

        results = {}
        for product in products:
            suitable_rule = self.env['product.pricelist.item']

            product_uom = product.uom_id
            target_uom = uom or product_uom  # If no uom is specified, fall back on the product uom

            # Compute quantity in product uom because pricelist rules are specified
            # w.r.t product default UoM (min_quantity, price_surchage, ...)
            if target_uom != product_uom:
                qty_in_product_uom = target_uom._compute_quantity(
                    quantity, product_uom, raise_if_failure=False
                )
            else:
                qty_in_product_uom = quantity

            for rule in rules:
                if rule._is_applicable_for(product, qty_in_product_uom):
                    suitable_rule = rule
                    break

            if compute_price:
                price = suitable_rule._compute_price(product, quantity, target_uom, date=date, currency=currency)
            else:
                # Skip price computation when only the rule is requested.
                price = 0.0
            results[product.id] = (price, suitable_rule.id)

        return results


class PricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    def _compute_base_price(self, product, quantity, uom, date, currency):
        """ Compute the base price for a given rule

        :param product: recordset of product (product.product/product.template)
        :param float qty: quantity of products requested (in given uom)
        :param uom: unit of measure (uom.uom record)
        :param datetime date: date to use for price computation and currency conversions
        :param currency: currency in which the returned price must be expressed

        :returns: base price, expressed in provided pricelist currency
        :rtype: float
        """
        currency.ensure_one()

        rule_base = self.base or 'list_price'
        if rule_base == 'pricelist' and self.base_pricelist_id:
            price = self.base_pricelist_id._get_product_price(
                product, quantity, currency=self.base_pricelist_id.currency_id, uom=uom, date=date
            )
            src_currency = self.base_pricelist_id.currency_id
        elif rule_base == "standard_price":
            src_currency = product.cost_currency_id
            price = product._price_compute(rule_base, uom=uom, date=date)[product.id]
        else:  # list_price
            src_currency = product.currency_id
            price = product._price_compute(rule_base, uom=uom, date=date)[product.id]

        if src_currency != currency:
            price = src_currency.with_context(sale=True)._convert(price, currency, self.env.company, date, round=False)
        return price


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _price_compute(self, price_type, uom=None, currency=None, company=None, date=False):
        company = company or self.env.company
        date = date or fields.Date.context_today(self)

        self = self.with_company(company)
        if price_type == 'standard_price':
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            self = self.sudo()

        prices = dict.fromkeys(self.ids, 0.0)
        for template in self:
            price = template[price_type] or 0.0
            price_currency = template.currency_id
            if price_type == 'standard_price':
                if not price and template.product_variant_ids:
                    price = template.product_variant_ids[0].standard_price
                price_currency = template.cost_currency_id
            elif price_type == 'list_price':
                price += template._get_attributes_extra_price()

            if uom:
                price = template.uom_id._compute_price(price, uom)

            # Convert from current user company currency to asked one
            # This is right cause a field cannot be in more than one currency
            if currency:
                price = price_currency.with_context(sale=True)._convert(price, currency, company, date)

            prices[template.id] = price
        return prices


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _price_compute(self, price_type, uom=None, currency=None, company=None, date=False):
        company = company or self.env.company
        date = date or fields.Date.context_today(self)

        self = self.with_company(company)
        if price_type == 'standard_price':
            # standard_price field can only be seen by users in base.group_user
            # Thus, in order to compute the sale price from the cost for users not in this group
            # We fetch the standard price as the superuser
            self = self.sudo()

        prices = dict.fromkeys(self.ids, 0.0)
        for product in self:
            price = product[price_type] or 0.0
            price_currency = product.currency_id
            if price_type == 'standard_price':
                price_currency = product.cost_currency_id
            elif price_type == 'list_price':
                price += product._get_attributes_extra_price()

            if uom:
                price = product.uom_id._compute_price(price, uom)

            # Convert from current user company currency to asked one
            # This is right cause a field cannot be in more than one currency
            if currency:
                price = price_currency.with_context(sale=True)._convert(price, currency, company, date)

            prices[product.id] = price

        return prices
