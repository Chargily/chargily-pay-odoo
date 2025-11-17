# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import hashlib
import logging
import json
from werkzeug.exceptions import Forbidden
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ChargilyController(http.Controller):
    _webhook_url = '/payment/chargily/webhook'

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def chargily_webhook(self, **data):
        """ Process the notification data sent by Chargily to the webhook. """
        try:
            signature = request.httprequest.headers.get('signature')
            if not signature:
                _logger.warning("🚨 Received webhook with missing signature!")
                return http.Response("Missing signature", status=403)

            chargily_provider = request.env['payment.provider'].sudo().search([('code', '=', 'chargily')], limit=1)
            api_key = chargily_provider.api_key if chargily_provider else None

            if not api_key:
                _logger.warning("⚠️ Chargily API key not found in payment provider settings!")
                return http.Response("API key not found", status=403)

            raw_payload = request.httprequest.data.decode('utf-8')

            computed_signature = hmac.new(
                api_key.encode('utf-8'),
                raw_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, computed_signature):
                _logger.warning("❌ Signature mismatch! Received: %s | Computed: %s", signature, computed_signature)
                return http.Response("Invalid signature", status=403)

            json_data = json.loads(raw_payload)
            metadata = json_data.get("data", {}).get("metadata", [])

            reference = metadata[0].get("reference") if metadata else None
            _logger.info(f"📩 Extracted reference: {reference}")

            if reference:
                tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)], limit=1)
                
                if tx_sudo:
                    event_type = json_data.get("type")
                    if event_type == "checkout.paid":
                        tx_sudo._set_done(state_message="Payment completed")
                        _logger.info(f"✅ Transaction {reference} marked as PAID")
                        if tx_sudo.sale_order_ids and tx_sudo.sale_order_ids.state in ['draft', 'sent']:
                            tx_sudo.sale_order_ids.action_confirm()
                            for order in tx_sudo.sale_order_ids:
                                if not order.invoice_ids:  # Avoid duplicate invoices
                                    invoice = order._create_invoices()
                                    invoice.action_post()  # Validate the invoice
                                    _logger.info(f"🧾 Invoice {invoice.name} created and posted for Order {order.name}")

                    elif event_type in ["checkout.failed", "checkout.expired"]:
                        tx_sudo._set_error(state_message="Payment Failed")
                        _logger.info(f"❌ Transaction {reference} marked as FAILED")
                    elif event_type == "checkout.canceled":
                        tx_sudo._set_canceled(state_message="Payment Canceled")
                        _logger.info(f"⚠️ Transaction {reference} marked as CANCELED")
                else:
                    _logger.warning(f"⚠️ No transaction found for reference: {reference}")
            else:
                _logger.warning("⚠️ No reference found in the metadata")

        except Exception as e:
            _logger.error(f"❌ Error processing webhook: {e}")

        return http.Response(status=200)
