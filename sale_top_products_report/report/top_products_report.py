from odoo import models


class TopProductsReport(models.AbstractModel):
    _name = 'report.sale_top_products_report.report_top_products_template'
    _description = 'Top Selling Products Report'

    def _get_report_values(self, docids, data=None):
        data = data or {}
        date_from = data.get('date_from')
        date_to = data.get('date_to')

        domain = [
            ('order_id.state', 'in', ['sale', 'done']),
            ('order_id.date_order', '>=', date_from),
            ('order_id.date_order', '<=', date_to + ' 23:59:59'),
            ('qty_delivered', '>', 0),
        ]

        sol_obj = self.env['sale.order.line']
        grouped = sol_obj.read_group(
            domain=domain,
            fields=['product_id', 'qty_delivered:sum'],
            groupby=['product_id'],
            orderby='qty_delivered desc',
        )

        lines = []
        for i, rec in enumerate(grouped, start=1):
            if not rec.get('product_id'):
                continue
            product = self.env['product.product'].browse(rec['product_id'][0])
            lines.append({
                'rank': i,
                'product_name': product.display_name,
                'product_code': product.default_code or '',
                'total_qty': rec['qty_delivered'],
            })

        return {
            'doc_ids': docids,
            'doc_model': 'sale.top.products.wizard',
            'data': data,
            'lines': lines,
            'date_from': date_from,
            'date_to': date_to,
        }
