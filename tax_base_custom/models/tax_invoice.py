from odoo import models, fields ,api
 

class TaxInvoice(models.Model):
    _name = 'tax.invoice'
    _description = 'Tax Invoice'
 
    reference = fields.Many2one('sale.order',string="Invoice")
    invoice_id = fields.Many2one('account.move',string="Invoice")
    date = fields.Date(string="Date", default=fields.Date.today)
    customer_id = fields.Many2one('res.partner', string="Customer")

    line_ids = fields.One2many('tax.invoice.line', 'invoice_id', string="Product Lines")

    total_amount = fields.Float(string="Total Amount", compute="_compute_totals",store=True)
    tax_amount = fields.Float(string="Tax Amount", compute="_compute_totals")
    due_amount = fields.Float(string="Due Amount", compute="_compute_totals")

    @api.depends('line_ids.total_price', 'line_ids.tax')
    def _compute_totals(self):
        for rec in self:
            total = sum(line.total_price for line in rec.line_ids)
            tax = sum(line.total_price * (line.tax.amount / 100) for line in rec.line_ids if line.tax)

            rec.total_amount = total
            rec.tax_amount = tax
            rec.due_amount = total + tax

class TaxInvoiceLine(models.Model):
    _name = 'tax.invoice.line'
    _description = 'Tax Invoice Line'

    invoice_id = fields.Many2one('tax.invoice')

    product_id = fields.Many2one('product.template', string="Product")
    label = fields.Char(string="Label")
    quantity = fields.Float(string="Quantity", default=1)
    unit_price = fields.Float(string="Unit Price")
    tax = fields.Many2one('account.tax', string="Tax")

    total_price = fields.Float(string="Total Price", compute="_compute_total")

    @api.depends('quantity', 'unit_price')
    def _compute_total(self):
        for rec in self:
            rec.total_price = rec.quantity * rec.unit_price


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_create_tax_invoice(self):
        return self.env.ref('tax_base_custom.action_report_tax_invoice').report_action(self)

    def _create_invoices(self, grouped=False, final=False, date=None):
        invoices = super()._create_invoices(grouped, final, date)

        for order in self:
            tax_invoice = self.env['tax.invoice'].create({
                'reference': order.id,
                'invoice_id': order.invoice_ids.id,
                'customer_id': order.partner_id.id,

            })

            for line in order.order_line:
                tax_invoice.line_ids.create({
                    'invoice_id': tax_invoice.id,
                    'product_id': line.product_id.product_tmpl_id.id,
                    'label': line.name,
                    'quantity': line.product_uom_qty,
                    'tax': line.tax_id.id,
                    'unit_price': line.product_id.product_tmpl_id.tax_base_amount,   
                })

        return invoices
# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'

#     tax_base_amount = fields.Float(
#         string='Tax Price'
#     )
#     @api.onchange('product_id')
#     def _onchange_product_id_tax_base(self):
#         for line in self:
#             if line.product_id:
#                 line.tax_base_amount = line.product_id.tax_base_amount


#     def create(self, vals_list):
#         for vals in vals_list:
#             product_id = vals.get('product_id')

#             # لو ما في قيمة، جيبها من المنتج
#             if product_id and not vals.get('tax_base_amount'):
#                 product = self.env['product.product'].browse(product_id)
#                 vals['tax_base_amount'] = product.tax_base_amount or 0.0

#         return super().create(vals_list)
 
