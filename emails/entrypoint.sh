#!/bin/bash
set -e

echo "==> Configurando Postfix..."

# Hostname
MAIL_HOSTNAME="${MAIL_HOSTNAME:-mail.local}"
echo "$MAIL_HOSTNAME" > /etc/mailname

# Configuracion principal de Postfix
cat > /etc/postfix/main.cf << EOF
myhostname = ${MAIL_HOSTNAME}
myorigin = /etc/mailname
mydestination = localhost
inet_interfaces = all
inet_protocols = ipv4

# Forzar uso del resolver nativo (getent) en lugar del resolver interno de Postfix
smtp_host_lookup = native
lmtp_host_lookup = native

# Relay SMTP externo
relayhost = ${RELAYHOST:-[smtp.gmail.com]:587}

# Autenticacion SASL
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
smtp_sasl_security_options = noanonymous
smtp_sasl_tls_security_options = noanonymous

# TLS obligatorio
smtp_tls_security_level = encrypt
smtp_tls_CAfile = /etc/ssl/certs/ca-certificates.crt

# Logs a stdout
maillog_file = /dev/stdout

# Limites
message_size_limit = 20971520
mailbox_size_limit = 0
EOF

# Credenciales del relay
echo "${RELAYHOST:-[smtp.gmail.com]:587}    ${SMTP_USER}:${SMTP_PASSWORD}" > /etc/postfix/sasl_passwd
postmap /etc/postfix/sasl_passwd
chmod 600 /etc/postfix/sasl_passwd /etc/postfix/sasl_passwd.db

echo "==> Postfix configurado. Iniciando..."
exec postfix start-fg
