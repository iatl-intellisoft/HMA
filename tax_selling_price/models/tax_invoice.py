from odoo import models, fields ,api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tax_price = fields.Float(string="Tax Price")

class TaxInvoice(models.Model):
    _name = 'tax.invoice'
    _description = 'Tax Invoice'

    reference = fields.Char(string="Reference")
    date = fields.Date(string="Date", default=fields.Date.today)
    customer_id = fields.Many2one('res.partner', string="Customer")

    line_ids = fields.One2many('tax.invoice.line', 'invoice_id', string="Product Lines")

    total_amount = fields.Float(string="Total Amount", compute="_compute_totals")
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

    def _create_invoices(self, grouped=False, final=False, date=None):
        invoices = super()._create_invoices(grouped, final, date)

        for order in self:
            tax_invoice = self.env['tax.invoice'].create({
                'reference': order.name,
                'customer_id': order.partner_id.id,
            })

            for line in order.order_line:
                tax_invoice.line_ids.create({
                    'invoice_id': tax_invoice.id,
                    'product_id': line.product_id.product_tmpl_id.id,
                    'label': line.name,
                    'quantity': line.product_uom_qty,
                    'unit_price': line.product_id.product_tmpl_id.tax_price,   
                })

        return invoices