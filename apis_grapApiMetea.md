Whatsapp
curl -i -X POST `
     https://graph.facebook.com/v25.0/1237532952784065/messages `
     -H 'Authorization: Bearer EAAW8u0g5PQ8BSSqFPAkV4mv8kmYMHi4meFMxdwpk0ZB0LGcq33l35vrPyFJYeRr4PgczU9lQuvgpCfZAie7ZAG0gin7v5P4rUq0w3cXpyN7oW87njjGa9ChWK3I2UcOjSiTgVJrLF8ZBSoMiaZC8ZCUr9g5zCgL3o0C6BVi17nXLulTBguOk6KbusZCLaUoOkscQNX2BuDgqrWcfsS60uaMKPhf7WVaZC06khBkLIYm67NmYZBucjkhCrv5AVqF0CJCgfKoAysoXnX59YiE0FrnFsaBYtCAZDZD' `
     -H 'Content-Type: application/json' `
     -d '{ \"messaging_product\": \"whatsapp\",
     \"to\": \"573184663204\",
     \"type\": \"template\",
     \"template\": { \"name\": \"jaspers_market_order_confirmation_v1\",
     \"language\": { \"code\": \"en_US\" },
     \"components\": [{ \"type\": \"body\", \"parameters\": [{ \"type\": \"text\", \"text\": \"John Doe\" }, { \"type\": \"text\", \"text\": \"123456\" }, { \"type\": \"text\", \"text\": \"Sep 4, 2026\" }] }] } }'

Instagram
curl -X POST \
  'https://graph.instagram.com/v25.0/me/messages' \
  -H 'Authorization: Bearer 56SRBJ8R3LQUBT95H1PBKWYT6SDQ8F' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": {
        "text": "Hello World"
    },
    "recipient": {
        "id": ""
    }
  }'