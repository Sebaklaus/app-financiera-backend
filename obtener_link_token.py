"""Obtiene un link_token de PRUEBA de Fintoc (Link Intent -> Widget -> exchange).

Uso (PowerShell, dentro del backend, con .venv activo):
    python obtener_link_token.py

Lee FINTOC_SECRET_KEY (sk_test_...) y FINTOC_PUBLIC_KEY (pk_test_...) del archivo
.env de la carpeta actual o de variables de entorno. El link_token se imprime SOLO
en la terminal (no se guarda). Copialo apenas aparezca: Fintoc no lo almacena.
"""
import json
import os
import threading
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

API = "https://api.fintoc.com/v1"
PUERTO = 8765


def leer_env():
    valores = {}
    if os.path.exists(".env"):
        with open(".env", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#") and "=" in linea:
                    k, v = linea.split("=", 1)
                    valores[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("FINTOC_SECRET_KEY", "FINTOC_PUBLIC_KEY"):
        valores[k] = os.environ.get(k, valores.get(k, ""))
    return valores


ENV = leer_env()
SECRETA = ENV["FINTOC_SECRET_KEY"]
PUBLICA = ENV["FINTOC_PUBLIC_KEY"]


def llamar(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(
        API + ruta, data=datos, method=metodo,
        headers={"Authorization": SECRETA, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode(errors="replace")}


PAGINA = """<!doctype html><meta charset="utf-8"><title>Link de prueba</title>
<body style="font-family:sans-serif;max-width:560px;margin:40px auto">
<h2>Crear Link de prueba (Fintoc)</h2>
<p>Elige tu banco y entra con <b>41614850-3</b> / <b>jonsnow</b>.</p>
<button id="b" style="padding:10px 18px;font-size:16px">Abrir widget</button>
<pre id="o"></pre>
<script src="https://js.fintoc.com/v1/"></script>
<script>
const o=document.getElementById('o');
document.getElementById('b').onclick=async()=>{
  const r=await fetch('/intent',{method:'POST'}); const d=await r.json();
  if(!d.widget_token){o.textContent='Error: '+JSON.stringify(d);return;}
  const w=Fintoc.create({publicKey:'__PK__',widgetToken:d.widget_token,
    onSuccess:async(li)=>{
      const t=li.exchangeToken||li.exchange_token;
      const x=await fetch('/exchange?t='+encodeURIComponent(t));
      o.textContent=(await x.text());
    },
    onExit:()=>{o.textContent='Cerraste el widget.';}});
  w.open();
};
</script>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _enviar(self, codigo, cuerpo, tipo="application/json"):
        b = cuerpo.encode()
        self.send_response(codigo)
        self.send_header("Content-Type", tipo + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/":
            self._enviar(200, PAGINA.replace("__PK__", PUBLICA), "text/html")
        elif self.path.startswith("/exchange"):
            from urllib.parse import parse_qs, urlparse
            t = parse_qs(urlparse(self.path).query).get("t", [""])[0]
            cod, d = llamar("GET", "/links/exchange?exchange_token=" + t)
            tok = d.get("link_token")
            if tok:
                print("\n=== LINK_TOKEN (copialo ahora, no se puede recuperar) ===")
                print(tok)
                print("=========================================================\n")
                self._enviar(200, "Listo. Mira tu terminal y copia el link_token.", "text/plain")
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            else:
                print("Error en exchange:", cod, d)
                self._enviar(200, "Error. Mira la terminal.", "text/plain")
        else:
            self._enviar(404, "{}")

    def do_POST(self):
        if self.path == "/intent":
            cod, d = llamar("POST", "/link_intents",
                            {"country": "cl", "holder_type": "individual", "product": "movements"})
            if cod >= 400:
                print("Error creando Link Intent:", cod, d)
            self._enviar(200, json.dumps(d))
        else:
            self._enviar(404, "{}")


if __name__ == "__main__":
    if not SECRETA.startswith("sk_test_") or not PUBLICA.startswith("pk_test_"):
               raise SystemExit(
            "Faltan FINTOC_SECRET_KEY (sk_test_...) "
            "y/o FINTOC_PUBLIC_KEY (pk_test_...) en .env"
        )
    print(f"Abre http://localhost:{PUERTO} (Ctrl+C para salir)")
    webbrowser.open(f"http://localhost:{PUERTO}")
    HTTPServer(("127.0.0.1", PUERTO), H).serve_forever()