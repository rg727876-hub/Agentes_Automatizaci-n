"""
Parche SSL para Windows.
Python en Windows a veces no tiene los certificados raíz correctos.
Este módulo desactiva la verificación SSL para que las llamadas a las APIs funcionen.
Debe importarse ANTES que cualquier otra librería de red.
"""
import ssl
import httpx

ssl._create_default_https_context = ssl._create_unverified_context

_orig_client = httpx.Client.__init__
def _client_noverify(self, *args, **kwargs):
    kwargs.setdefault("verify", False)
    _orig_client(self, *args, **kwargs)
httpx.Client.__init__ = _client_noverify

_orig_async = httpx.AsyncClient.__init__
def _async_noverify(self, *args, **kwargs):
    kwargs.setdefault("verify", False)
    _orig_async(self, *args, **kwargs)
httpx.AsyncClient.__init__ = _async_noverify
