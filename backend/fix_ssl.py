"""
Configuración SSL para Windows.

Python en Windows a veces no encuentra los certificados raíz del sistema, lo
que rompe las llamadas HTTPS a las APIs. En vez de DESACTIVAR la verificación
(inseguro), apuntamos la verificación al paquete de certificados de `certifi`,
que trae las CA raíz actualizadas. Así las conexiones siguen siendo seguras.

Debe importarse ANTES que cualquier otra librería de red.
"""
import os
import ssl

import certifi

_CA_BUNDLE = certifi.where()

# Librerías que respetan estas variables de entorno de OpenSSL (requests, httpx, grpc, etc.)
os.environ.setdefault("SSL_CERT_FILE", _CA_BUNDLE)
os.environ.setdefault("REQUESTS_CA_BUNDLE", _CA_BUNDLE)

# Biblioteca estándar (urllib y demás): usar el bundle de certifi por defecto,
# manteniendo la verificación de certificados activada.
ssl._create_default_https_context = lambda *a, **k: ssl.create_default_context(cafile=_CA_BUNDLE)
