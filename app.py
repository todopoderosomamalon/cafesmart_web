"""CaféSmart · Panel web (Flask + Supabase). No usa pandas.

Lee las tablas que sube el notebook y dibuja las 7 pantallas.
Configuración: archivo .env con SUPABASE_URL y SUPABASE_KEY (ver .env.example).
"""
import csv
import io
import os
import time
from collections import Counter, defaultdict
from datetime import date

from dotenv import load_dotenv
from flask import Flask, Response, redirect, render_template, request, url_for
from markupsafe import Markup
from werkzeug.exceptions import HTTPException

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)
CACHE_SEGUNDOS = int(os.getenv("CACHE_SEGUNDOS", "300"))   # cada cuánto vuelve a leer Supabase

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]
CATEGORIAS = {"Coffee": "Café", "Tea": "Té", "Drinking Chocolate": "Chocolate", "Bakery": "Panadería"}
TIPOS = {"semana": "Semana", "mes": "Mes", "estacion": "Estación"}


class ErrorDeConfiguracion(Exception):
    pass


class SinDatos(Exception):
    pass


# ---------------------------------------------------------------- Supabase
_cliente = None
_cache = {}


def cliente():
    global _cliente
    if _cliente is None:
        url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
        if url.endswith("/rest/v1"):                  # error típico al copiar la URL
            url = url[: -len("/rest/v1")]
        llave = os.getenv("SUPABASE_KEY", "").strip()
        if not url or not llave:
            raise ErrorDeConfiguracion("Falta SUPABASE_URL o SUPABASE_KEY en el archivo .env")
        from supabase import create_client
        _cliente = create_client(url, llave)
    return _cliente


def leer(tabla):
    """Lee una tabla completa (Supabase entrega máx. 1,000 filas por consulta, por eso se pagina)."""
    ahora = time.time()
    if tabla in _cache and ahora - _cache[tabla][0] < CACHE_SEGUNDOS:
        return _cache[tabla][1]
    filas, desde = [], 0
    while True:
        lote = cliente().table(tabla).select("*").order("id").range(desde, desde + 999).execute().data
        filas += lote
        if len(lote) < 1000:
            break
        desde += 1000
    _cache[tabla] = (ahora, filas)
    return filas


# ---------------------------------------------------------------- Formato
def mes_label(clave, largo=False):
    anio, mes = clave.split("-")
    nombre = MESES[int(mes) - 1]
    return f"{nombre} {anio}" if largo else f"{nombre[:3]} {anio[2:]}"


def fecha_corta(iso, con_anio=False):
    d = date.fromisoformat(iso)
    return f"{d.day} {MESES[d.month - 1][:3].lower()}" + (f" {d.year}" if con_anio else "")


def ingrediente_legible(nombre, cantidad):
    """'Café molido (g)', 12500 -> ('Café molido', '12.5 kg')."""
    base, _, resto = nombre.partition(" (")
    unidad = resto.rstrip(")")
    if unidad == "g":
        return base, f"{cantidad / 1000:,.1f} kg" if cantidad >= 1000 else f"{cantidad:,.0f} g"
    if unidad == "ml":
        return base, f"{cantidad / 1000:,.1f} L" if cantidad >= 1000 else f"{cantidad:,.0f} ml"
    return base, f"{cantidad:,.0f} u."


def tono(texto):
    t = str(texto)
    if t in ("Sube", "OK", "Completa"):
        return "green"
    if t in ("Baja",) or "FALTA" in t:
        return "red"
    if t in ("Parcial", "Por agotarse", "cálido", "caluroso"):
        return "orange"
    if t == "fresco":
        return "blue"
    return "gray"


ICONOS = {
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    "chart": '<path d="M4 20V10"/><path d="M10 20V4"/><path d="M16 20v-7"/><path d="M22 20H2"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h10"/><circle cx="19" cy="18" r="2"/>',
    "box": '<path d="m21 8-9 5-9-5"/><path d="M3 8l9-5 9 5v9l-9 5-9-5Z"/><path d="M12 13v9"/>',
    "cloud": '<path d="M17.5 19H6a4 4 0 0 1-.5-8 6.5 6.5 0 0 1 12.4-1.4A4.8 4.8 0 0 1 17.5 19Z"/><path d="M8 22h8"/>',
    "file": '<path d="M6 2h9l4 4v16H6Z"/><path d="M14 2v5h5"/><path d="M9 13h6M9 17h6"/>',
    "store": '<path d="M3 9h18l-2-6H5Z"/><path d="M5 9v12h14V9"/><path d="M9 21v-7h6v7"/>',
    "arrow": '<path d="M5 12h14"/><path d="m14 7 5 5-5 5"/>',
    "download": '<path d="M12 3v13"/><path d="m7 11 5 5 5-5"/><path d="M4 21h16"/>',
    "check": '<path d="m5 12 4 4L19 6"/>',
    "hamburger": '<path d="M4 6h16M4 12h16M4 18h16"/>',
}


def icon(nombre, size=18):
    return Markup(f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                  f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONOS[nombre]}</svg>')


PAGINAS = [("resumen", "Resumen", "grid"), ("ventas", "Ventas", "chart"), ("menu", "Menú sugerido", "menu"),
           ("inventario", "Inventario", "box"), ("clima", "Alertas de clima", "cloud"),
           ("reportes", "Reportes", "file"), ("tiendas", "Tiendas", "store")]

app.jinja_env.globals.update(icon=icon, PAGINAS=PAGINAS, TIPOS=TIPOS, tono=tono)
app.jinja_env.filters["num"] = lambda v: f"{float(v):,.0f}"
app.jinja_env.filters["dinero"] = lambda v: f"${float(v):,.2f}"


# ---------------------------------------------------------------- Cálculos
def periodos(tipo):
    """Barras de la gráfica: próximas 8 semanas, meses o estaciones."""
    if tipo == "semana":
        tot = defaultdict(float)
        for f in leer("pronostico_semanal"):
            tot[f["fecha"]] += f["unidades"]
        lista = [dict(key=k, label=fecha_corta(k), largo="Semana que termina el " + fecha_corta(k, True), unidades=tot[k], parcial=False)
                 for k in sorted(tot)[:8]]
    elif tipo == "mes":
        lista = [dict(key=r["mes"], label=mes_label(r["mes"]), largo=mes_label(r["mes"], True), unidades=r["unidades"], parcial=False)
                 for r in sorted(leer("total_mensual"), key=lambda r: r["mes"])]
    else:
        lista = [dict(key=r["estacion"], label=r["estacion"], largo=r["estacion"], unidades=r["unidades"], parcial=not r["completa"])
                 for r in leer("total_estacion")]
    if not lista:
        raise SinDatos("Las tablas de Supabase están vacías. Corre la celda de subida del notebook.")
    return lista


def elegir(tipo, sel, endpoint):
    """Devuelve (barras, periodo_elegido) con la altura y el enlace de cada barra."""
    lista = periodos(tipo)
    actual = next((p for p in lista if p["key"] == sel), lista[0])
    tope = max(p["unidades"] for p in lista) or 1
    for p in lista:
        p["alto"] = max(round(p["unidades"] / tope * 100), 4)
        p["href"] = url_for(endpoint, p=tipo, sel=p["key"])
    return lista, actual


def promedio_historico():
    """Promedio semanal por producto en las últimas 8 semanas reales."""
    filas = leer("ventas_semanales")
    ultimas = set(sorted({f["fecha"] for f in filas})[-8:])
    suma = defaultdict(float)
    for f in filas:
        if f["fecha"] in ultimas:
            suma[f["producto"]] += f["unidades"]
    return {p: s / (len(ultimas) or 1) for p, s in suma.items()}


def productos_en(tipo, clave):
    campo = {"semana": "fecha", "mes": "mes", "estacion": "estacion"}[tipo]
    filas = [f for f in leer("pronostico_semanal") if f[campo] == clave]
    semanas = len({f["fecha"] for f in filas}) or 1
    unidades, categoria = defaultdict(float), {}
    for f in filas:
        unidades[f["producto"]] += f["unidades"]
        categoria[f["producto"]] = CATEGORIAS.get(f["categoria"], f["categoria"] or "Otros")
    hist = promedio_historico()
    salida = []
    for prod, u in unidades.items():
        base = hist.get(prod)
        razon = (u / semanas) / base if base else None
        tend = "Sin dato" if razon is None else "Sube" if razon >= 1.05 else "Baja" if razon <= 0.95 else "Estable"
        salida.append(dict(producto=prod, categoria=categoria[prod], unidades=u, tendencia=tend))
    return sorted(salida, key=lambda x: -x["unidades"])


def por_categoria(productos):
    tot = defaultdict(float)
    for p in productos:
        tot[p["categoria"]] += p["unidades"]
    suma = sum(tot.values()) or 1
    return sorted(((c, round(v / suma * 100)) for c, v in tot.items()), key=lambda x: -x[1])


def estacion_de(tipo, clave):
    if tipo == "estacion":
        return clave
    campo = {"semana": "fecha", "mes": "mes"}[tipo]
    cuenta = Counter(f["estacion"] for f in leer("pronostico_semanal") if f[campo] == clave)
    return cuenta.most_common(1)[0][0] if cuenta else None


def combos_de(tipo, clave):
    if tipo == "semana":
        tabla, periodo = "menu_semanal", f"Semana del {clave}"
    else:
        if tipo == "estacion":      # el menú es mensual: se muestra el primer mes de la estación
            meses = sorted({f["mes"] for f in leer("pronostico_semanal") if f["estacion"] == clave})
            if not meses:
                return []
            clave = meses[0]
        tabla, periodo = "menu_mensual", mes_label(clave, largo=True)
    return [dict(c, nombre=f'{c["bebida"]} + {c["comida"]}') for c in leer(tabla) if c["periodo"] == periodo]


def pedido_de(estacion):
    filas = [r for r in leer("pedido_estacion") if r["estacion"] == estacion]
    salida = []
    for r in sorted(filas, key=lambda r: -r["cantidad"]):
        nombre, total = ingrediente_legible(r["ingrediente"], r["cantidad"])
        _, semanal = ingrediente_legible(r["ingrediente"], r["cantidad"] / (r["semanas"] or 1))
        salida.append(dict(ingrediente=nombre, total=total, semanal=semanal, cruda=r["cantidad"],
                           semanas=r["semanas"], completa=r["completa"]))
    return salida


def resumen_modelos():
    """Error medio de cada modelo en la validación y mejora contra el promedio simple."""
    v = leer("validacion_modelos")
    if not v:
        return None
    n = len(v)
    medias = {k: sum(r[k] for r in v) / n for k in ("linea_base", "random_forest", "gradient_boosting")}
    mejor = min(("random_forest", "gradient_boosting"), key=medias.get)
    nombre = "Random Forest" if mejor == "random_forest" else "Gradient Boosting"
    mejora = (1 - medias[mejor] / medias["linea_base"]) * 100 if medias["linea_base"] else 0
    return dict(medias=medias, mejor=nombre, error_mejor=medias[mejor], mejora=mejora)


# ---------------------------------------------------------------- Páginas
def _parametros(endpoint):
    tipo = request.args.get("p", "semana")
    tipo = tipo if tipo in TIPOS else "semana"
    barras, actual = elegir(tipo, request.args.get("sel"), endpoint)
    return tipo, barras, actual


@app.route("/")
def resumen():
    tipo, barras, actual = _parametros("resumen")
    prods = productos_en(tipo, actual["key"])
    combos = combos_de(tipo, actual["key"])
    est = estacion_de(tipo, actual["key"])
    ingredientes = pedido_de(est)[:5] if est else []
    return render_template("resumen.html", tipo=tipo, barras=barras, actual=actual, prods=prods,
                           combos=combos, ingredientes=ingredientes, estacion=est, modelos=resumen_modelos())


@app.route("/ventas")
def ventas():
    tipo, barras, actual = _parametros("ventas")
    prods = productos_en(tipo, actual["key"])
    todas = {}
    for f in leer("pronostico_semanal"):
        todas[f["fecha"]] = todas.get(f["fecha"], 0) + f["unidades"]
    mejor_sem = max(todas, key=todas.get)
    meses = sorted(leer("total_mensual"), key=lambda r: -r["unidades"])
    return render_template("ventas.html", tipo=tipo, barras=barras, actual=actual, prods=prods,
                           categorias=por_categoria(prods), mejor_semana=(fecha_corta(mejor_sem, True), todas[mejor_sem]),
                           mejor_mes=(mes_label(meses[0]["mes"], True), meses[0]["unidades"]) if meses else None)


@app.route("/menu")
def menu():
    tipo = "semana" if request.args.get("p") == "semana" else "mes"
    lista = periodos(tipo)
    actual = next((p for p in lista if p["key"] == request.args.get("sel")), lista[0])
    prods = productos_en(tipo, actual["key"])
    unidades = {p["producto"]: p["unidades"] for p in prods}
    combos = combos_de(tipo, actual["key"])
    for c in combos:
        c["u_bebida"], c["u_comida"] = unidades.get(c["bebida"], 0), unidades.get(c["comida"], 0)
    return render_template("menu.html", tipo=tipo, lista=lista, actual=actual, combos=combos, prods=prods[:10])


@app.route("/inventario")
def inventario():
    estaciones = [r["estacion"] for r in leer("total_estacion")]
    est = request.args.get("estacion") if request.args.get("estacion") in estaciones else (estaciones[0] if estaciones else None)
    tab = "revision" if request.args.get("tab") == "revision" else "pedido"
    return render_template("inventario.html", estaciones=estaciones, estacion=est, tab=tab,
                           pedido=pedido_de(est) if est else [], revision=leer("revision_inventario"))


@app.route("/inventario/pedido.csv")
def pedido_csv():
    est = request.args.get("estacion", "")
    salida = io.StringIO()
    w = csv.writer(salida)
    w.writerow(["estacion", "ingrediente", "cantidad_total", "cantidad_por_semana", "semanas"])
    for r in pedido_de(est):
        w.writerow([est, r["ingrediente"], r["total"], r["semanal"], r["semanas"]])
    nombre = est.replace(" ", "_") or "pedido"
    return Response("\ufeff" + salida.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename=pedido_{nombre}.csv"})


@app.route("/clima")
def clima():
    filas = leer("menu_mensual")
    meses, vistos = [], {}
    for f in filas:
        if f["periodo"] not in vistos:
            vistos[f["periodo"]] = dict(periodo=f["periodo"], clima=f["clima_esperado"], combos=[])
            meses.append(vistos[f["periodo"]])
        vistos[f["periodo"]]["combos"].append(f'{f["bebida"]} + {f["comida"]}')
    conteo = Counter(m["clima"] for m in meses)
    return render_template("clima.html", meses=meses, conteo=conteo)


@app.route("/reportes")
def reportes():
    v = leer("validacion_modelos")
    series = [("linea_base", "Promedio simple", "bar-gray", "dot-gray"),
              ("random_forest", "Random Forest", "bar-soft", "dot-soft"),
              ("gradient_boosting", "Gradient Boosting", "bar-strong", "dot-strong")]
    tope = max((r[k] for r in v for k, *_ in series), default=1) or 1
    return render_template("reportes.html", validacion=v, series=series, tope=tope, modelos=resumen_modelos())


@app.route("/tiendas")
def tiendas():
    sem = periodos("semana")[:4]
    fechas = {p["key"] for p in sem}
    unidades = defaultdict(float)
    for f in leer("pronostico_semanal"):
        if f["fecha"] in fechas:
            unidades[f["producto"]] += f["unidades"]
    estrella = max(unidades, key=unidades.get) if unidades else "—"
    ultima = leer("total_estacion")[0]["estacion"] if leer("total_estacion") else None
    return render_template("tiendas.html", unidades=sum(p["unidades"] for p in sem), estrella=estrella,
                           semanas=len({f["fecha"] for f in leer("pronostico_semanal")}),
                           n_ingredientes=len(pedido_de(ultima)) if ultima else 0, modelos=resumen_modelos())


@app.route("/actualizar")
def actualizar():
    """Borra la memoria y vuelve a leer Supabase (útil justo después de subir datos nuevos)."""
    _cache.clear()
    return redirect(request.referrer or url_for("resumen"))


# ---------------------------------------------------------------- Errores
@app.errorhandler(Exception)
def falla(e):
    if isinstance(e, HTTPException):
        return e
    app.logger.exception(e)
    if isinstance(e, (ErrorDeConfiguracion, SinDatos)):
        titulo, detalle = ("Falta configurar la conexión" if isinstance(e, ErrorDeConfiguracion) else "Aún no hay datos"), str(e)
    else:
        titulo, detalle = "No se pudo leer Supabase", f"{type(e).__name__}: {e}"
    return render_template("error.html", titulo=titulo, detalle=detalle), 500


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "5000")))
