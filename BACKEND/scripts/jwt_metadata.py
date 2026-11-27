"""Inspect a supplied development token without logging its value or identity claims.

This is not signature verification and must never be used for authentication.
"""
import json
import os
import time
import jwt


def main():
    token = os.environ.get('QA_BEARER_TOKEN', '').strip()
    if not token:
        raise SystemExit('Configura QA_BEARER_TOKEN de desarrollo; nunca lo pegues en el código.')
    try:
        payload = jwt.decode(token, options={'verify_signature': False})
        expires = payload.get('exp')
        result = {'signature_verified': False,
                  'expired': expires <= time.time() if isinstance(expires, (int, float)) else None,
                  'token_type': payload.get('token_type') if payload.get('token_type') in ('access', 'refresh') else 'unknown'}
    except Exception:
        raise SystemExit('No se pudo leer el token; valor y claims privados omitidos.') from None
    print(json.dumps(result))


if __name__ == '__main__':
    main()
