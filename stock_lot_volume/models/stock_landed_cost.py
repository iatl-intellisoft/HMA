# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class StockLandedCostLine(models.Model):
    _inherit = 'stock.landed.cost.lines'

    split_method = fields.Selection(
        selection_add=[('by_lot_volume', 'By Lot Volume')],
        ondelete={'by_lot_volume': 'cascade'},
    )


class StockValuationAdjustmentLines(models.Model):
    _inherit = 'stock.valuation.adjustment.lines'

    lot_volume = fields.Float(
        'Lot Volume (CBM)',
        default=0.0,
        digits='Volume',
        help="Sum of lot volumes (CBM) associated with this stock move, used for "
             "the 'By Lot Volume' landed cost split method.",
    )


class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    def get_valuation_lines(self):
        """Extend valuation lines to include lot_volume for each stock move."""
        lines = super().get_valuation_lines()
        for vals in lines:
            move = self.env['stock.move'].browse(vals['move_id'])
            # Sum the volumes of all lots on the move lines for this move
            lot_volume = sum(
                ml.lot_id.volume
                for ml in move.move_line_ids
                if ml.lot_id and ml.lot_id.volume
            )
            vals['lot_volume'] = lot_volume
        return lines

    def compute_landed_cost(self):
        AdjustementLines = self.env['stock.valuation.adjustment.lines']
        AdjustementLines.search([('cost_id', 'in', self.ids)]).unlink()

        towrite_dict = {}
        for cost in self.filtered(lambda cost: cost._get_targeted_move_ids()):
            cost = cost.with_company(cost.company_id)
            rounding = cost.currency_id.rounding
            total_qty = 0.0
            total_cost = 0.0
            total_weight = 0.0
            total_volume = 0.0
            total_lot_volume = 0.0
            total_line = 0.0
            all_val_line_values = cost.get_valuation_lines()
            for val_line_values in all_val_line_values:
                for cost_line in cost.cost_lines:
                    val_line_values.update({'cost_id': cost.id, 'cost_line_id': cost_line.id})
                    self.env['stock.valuation.adjustment.lines'].create(val_line_values)
                total_qty += val_line_values.get('quantity', 0.0)
                total_weight += val_line_values.get('weight', 0.0)
                total_volume += val_line_values.get('volume', 0.0)
                total_lot_volume += val_line_values.get('lot_volume', 0.0)

                former_cost = val_line_values.get('former_cost', 0.0)
                # round this because former_cost on the valuation lines is also rounded
                total_cost += cost.currency_id.round(former_cost)

                total_line += 1

            for line in cost.cost_lines:
                value_split = 0.0
                for valuation in cost.valuation_adjustment_lines:
                    value = 0.0
                    if valuation.cost_line_id and valuation.cost_line_id.id == line.id:
                        if line.split_method == 'by_quantity' and total_qty:
                            per_unit = (line.price_unit / total_qty)
                            value = valuation.quantity * per_unit
                        elif line.split_method == 'by_weight' and total_weight:
                            per_unit = (line.price_unit / total_weight)
                            value = valuation.weight * per_unit
                        elif line.split_method == 'by_volume' and total_volume:
                            per_unit = (line.price_unit / total_volume)
                            value = valuation.volume * per_unit
                        elif line.split_method == 'by_lot_volume' and total_lot_volume:
                            per_unit = (line.price_unit / total_lot_volume)
                            value = valuation.lot_volume * per_unit
                        elif line.split_method == 'equal':
                            value = (line.price_unit / total_line)
                        elif line.split_method == 'by_current_cost_price' and total_cost:
                            per_unit = (line.price_unit / total_cost)
                            value = valuation.former_cost * per_unit
                        else:
                            value = (line.price_unit / total_line)

                        if rounding:
                            value = tools.float_round(
                                value,
                                precision_rounding=rounding,
                                rounding_method='HALF-UP',
                            )
                            value_split += value

                        if valuation.id not in towrite_dict:
                            towrite_dict[valuation.id] = value
                        else:
                            towrite_dict[valuation.id] += value
                rounding_diff = cost.currency_id.round(line.price_unit - value_split)
                if not cost.currency_id.is_zero(rounding_diff):
                    towrite_dict[max(towrite_dict.keys())] += rounding_diff
        for key, value in towrite_dict.items():
            AdjustementLines.browse(key).write({'additional_landed_cost': value})
        return True
