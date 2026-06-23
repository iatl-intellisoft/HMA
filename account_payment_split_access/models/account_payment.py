from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # ── Context-flag fields (one per split menu) ──────────────────────────

    customer_cash_payment = fields.Boolean(compute="_compute_split_flags")
    customer_bank_payment = fields.Boolean(compute="_compute_split_flags")
    vendor_cash_payment   = fields.Boolean(compute="_compute_split_flags")
    vendor_bank_payment   = fields.Boolean(compute="_compute_split_flags")

    # Convenience: resolved journal type from context ('cash'|'bank'|False)
    split_journal_type = fields.Char(compute="_compute_split_flags")

    def _compute_split_flags(self):
        ctx = self.env.context
        ccp = bool(ctx.get("customer_cash_payment"))
        cbp = bool(ctx.get("customer_bank_payment"))
        vcp = bool(ctx.get("vendor_cash_payment"))
        vbp = bool(ctx.get("vendor_bank_payment"))

        if ccp or vcp:
            jtype = "cash"
        elif cbp or vbp:
            jtype = "bank"
        else:
            jtype = False

        for rec in self:
            rec.customer_cash_payment = ccp
            rec.customer_bank_payment = cbp
            rec.vendor_cash_payment   = vcp
            rec.vendor_bank_payment   = vbp
            rec.split_journal_type    = jtype

    # ── Pre-fill journal on new record ───────────────────────────────────

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        ctx  = self.env.context

        if ctx.get("customer_cash_payment") or ctx.get("vendor_cash_payment"):
            jtype = "cash"
        elif ctx.get("customer_bank_payment") or ctx.get("vendor_bank_payment"):
            jtype = "bank"
        else:
            return vals

        journal = self.env["account.journal"].search(
            [("type", "=", jtype)], limit=1
        )
        if journal:
            vals["journal_id"] = journal.id

        return vals
