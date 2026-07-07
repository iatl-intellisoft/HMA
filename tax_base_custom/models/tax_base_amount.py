from odoo import models, fields, api
 
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tax_base_amount = fields.Float(
        string='Tax Base Amount'
    )
 
class ProductProduct(models.Model):
    _inherit = 'product.product'

    tax_base_amount = fields.Float(
        related='product_tmpl_id.tax_base_amount',
        store=True,
        readonly=False
    )
class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_create_tax_invoice(self):
        return self.env.ref('tax_base_custom.action_report_tax_invoice').report_action(self)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def action_create_tax_invoice(self):
        return self.env.ref('tax_base_custom.action_report_tax_invoice').report_action(self)

    tax_base_amount = fields.Float(
        string='Tax Base Amount'
    )
    @api.onchange('product_id')
    def _onchange_product_id_tax_base(self):
        for line in self:
            if line.product_id:
                line.tax_base_amount = line.product_id.tax_base_amount


    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         product_id = vals.get('product_id')
    #         if product_id and not vals.get('tax_base_amount'):
    #             product = self.env['product.product'].browse(product_id)
    #             vals['tax_base_amount'] = product.tax_base_amount or 0.0

    #     return super().create(vals_list)
    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        for vals in vals_list:
            product_id = vals.get("product_id")

            if product_id and not vals.get("tax_base_amount"):
                product = self.env["product.product"].browse(product_id)
                vals["tax_base_amount"] = product.tax_base_amount or 0.0

        return super().create(vals_list)
 


# class AccountTax(models.Model):
#     _inherit = 'account.tax'

#     def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        
#         if self.env.context.get('tax_base_amount'):
#             base_amount = self.env.context['tax_base_amount']

#         return super()._compute_amount(base_amount, price_unit, quantity, product, partner)


# # class AccountMoveLine(models.Model):
# #     _inherit = 'account.move.line'

# #     def _get_computed_taxes(self):
# #         self.ensure_one()

# #         return self.tax_ids.with_context(
# #             tax_base_amount=self.tax_base_amount
# #         )
