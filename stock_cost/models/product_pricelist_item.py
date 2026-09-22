# -*- coding: utf-8 -*-

from odoo import models


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    def _compute_base_price(self, product, quantity, uom, date, currency):
        """Override to handle foreign_standard_price as a pricelist base.

        The standard _compute_base_price falls through to the else/list_price
        branch for unknown base values and uses product.currency_id (company
        currency) as the source currency.  But foreign_standard_price is stored
        in product.force_currency_id (e.g. EUR), so the conversion must start
        from that currency instead of the company currency.
        """
        if self.base != 'foreign_standard_price':
            return super()._compute_base_price(product, quantity, uom, date, currency)

        force_currency = product.force_currency_id
        if not force_currency:
            # No foreign currency configured – fall back to standard_price path
            return super()._compute_base_price(product, quantity, uom, date, currency)

        price = product.foreign_standard_price

        # Apply UoM conversion (same as the standard path)
        product_uom = product.uom_id
        if uom and product_uom != uom:
            price = product_uom._compute_price(price, uom)

        # Convert from force_currency (e.g. EUR) → pricelist currency
        if force_currency != currency:
            price = force_currency._convert(
                price, currency, self.env.company, date, round=False
            )

        return price
