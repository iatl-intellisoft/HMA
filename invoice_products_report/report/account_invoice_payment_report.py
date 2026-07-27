from odoo import api, models


class InvoiceProductsPdf(models.AbstractModel):
    _name = 'report.invoice_products_report.invoice_products_pdf'
    _description = 'Invoice Products PDF'

    @api.model
    def _get_report_values(self, docids, data=None):

        wizard = self.env['invoice.report.wizard'].browse(docids)

        domain = [
            ('invoice_date', '>=', wizard.date_from),
            ('invoice_date', '<=', wizard.date_to),
            ('state', '=', 'posted') if wizard.only_posted else ('id', '!=', 0),
        ]

        if wizard.move_type != 'all':
            domain.append(('move_type', '=', wizard.move_type))
        else:
            domain.append(('move_type', 'in', ['out_invoice', 'in_invoice']))

        if wizard.partner_id:
            domain.append(('partner_id', '=', wizard.partner_id.id))

        invoices = self.env['account.move'].search(
            domain,
            order='invoice_date,name'
        )

        if wizard.product_id:
            invoices = invoices.filtered(
                lambda m: any(
                    l.product_id == wizard.product_id
                    for l in m.invoice_line_ids.filtered(
                        lambda x: not x.display_type
                    )
                )
            )

        total_qty = 0
    total_products_amount = 0
    
    grand_total = 0
    grand_paid = 0
    grand_due = 0
    
    invoice_data = []
    
    for inv in invoices:
        invoice_qty = 0
        invoice_products_amount = 0
    
        for line in inv.invoice_line_ids.filtered(
            lambda x: not x.display_type
        ):
    
            if wizard.product_id and line.product_id != wizard.product_id:
                continue
    
            invoice_qty += line.quantity
            invoice_products_amount += line.price_subtotal
    
        paid_amount = inv.amount_total - inv.amount_residual
    
        invoice_data.append({
            'invoice': inv,
            'qty': invoice_qty,
            'products_amount': invoice_products_amount,
            'total': inv.amount_total,
            'paid': paid_amount,
            'due': inv.amount_residual,
        })
    
        total_qty += invoice_qty
        total_products_amount += invoice_products_amount
    
        grand_total += inv.amount_total
        grand_paid += paid_amount
        grand_due += inv.amount_residual
    return {
        'doc_ids': wizard.ids,
        'doc_model': 'invoice.report.wizard',
        'docs': wizard,
        'invoice_data': invoice_data,
    
        'total_qty': total_qty,
        'total_products_amount': total_products_amount,
    
        'grand_total': grand_total,
        'grand_paid': grand_paid,
        'grand_due': grand_due,
    }
