from odoo import models, fields


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('chargily', "Chargily")], ondelete={'chargily': 'set default'}
    )

    api_url = fields.Char(string="Chargily API URL", default="https://pay.chargily.com/api/v2/payment-links")
    api_key = fields.Char(string="Chargily API Key", help="Enter your Chargily API Key")