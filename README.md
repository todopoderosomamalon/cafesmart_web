# CaféSmart · Panel web (Flask + Supabase)

Lee las tablas que sube el notebook y muestra 7 pantallas: Resumen, Ventas, Menú sugerido,
Inventario, Alertas de clima, Reportes y Tiendas. No usa pandas.

## Cómo correrlo en Visual Studio Code

1. Abre esta carpeta en VS Code (Archivo → Abrir carpeta) y abre la terminal (Ctrl + Ñ).
2. Crea el entorno e instala (solo la primera vez):

   **Windows (PowerShell)**
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
   Si PowerShell bloquea el script: `Set-ExecutionPolicy -Scope Process Bypass` y repite.

   **Mac / Linux**
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Crea tu archivo `.env`: copia `.env.example`, renómbralo a `.env` y pega tu `SUPABASE_URL` y `SUPABASE_KEY`.
4. Corre la app:
   ```
   python app.py
   ```

## Cada mes
Corre el notebook (sube el CSV nuevo y guarda en Supabase). En la página, pulsa **↻ Datos**
(abajo en el menú lateral) para volver a leer Supabase sin esperar los 5 minutos de memoria.

## Seguridad
- `.env` está en `.gitignore`: no se sube a GitHub. Sube `.env.example`, que no tiene secretos.
- La llave solo la usa el servidor de Flask; el navegador nunca la ve.
- Si alguna vez la llave se publica por error, en Supabase genera una nueva y reemplázala.

## Estructura
```
app.py            lee Supabase, calcula y define las rutas
templates/        HTML (Jinja): base, macros y una plantilla por pantalla
static/css        estilos del prototipo de Figma
static/js         menú móvil, ordenar tablas, avisos
```
5. Abre http://127.0.0.1:5000
