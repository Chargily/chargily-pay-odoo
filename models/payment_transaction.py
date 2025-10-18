import requests
import json
import hmac
import hashlib
from odoo import models,fields,api
import logging
from odoo.http import request
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        provider = self.provider_id
        res = super()._get_specific_rendering_values(processing_values)
        
        if provider.code != "chargily":
            return res

        chargily_api_url = provider.api_url
        api_key = provider.api_key        
        
        if self.amount < 50:
            raise ValidationError("The payment amount must be at least 50 DZD.")

        # ✅ Payment request data
        payload = {
            "metadata":[{"reference": self.reference}],
            "amount": int(self.amount), 
            "currency": "dzd",
            "success_url":  f"{request.httprequest.host_url}payment/status",
            "failure_url": f"{request.httprequest.host_url}payment/status"
        }

        # ✅ Convert payload to JSON string for signing
        payload_json = json.dumps(payload, separators=(',', ':'))  # Ensure consistent formatting

        signature = hmac.new(
            api_key.encode(),  
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Signature": signature  # ✅ Include signature in headers
        }

        try:
            response = requests.post(chargily_api_url, json=payload, headers=headers)
            response_data = response.json()

            _logger.info(f"🔹 Chargily API Response: {json.dumps(response_data, indent=4)}")

            if "checkout_url" in response_data:
                res['api_url'] = response_data["checkout_url"]
        except Exception as e:
            _logger.error(f"❌ Chargily API Error: {e}")


        return res

 
