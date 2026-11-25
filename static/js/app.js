/* CaféSmart · JavaScript mínimo: menú móvil, ordenar tablas, avisos y "Usar en promoción". */
function toast(msg) {
  document.querySelectorAll(".toast").forEach((t) => t.remove());
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2400);
}

function menuMovil(abrir) {
  document.querySelector(".sidebar").classList.toggle("mobile-open", abrir);
  document.querySelectorAll(".nav-overlay").forEach((o) => o.remove());
  if (abrir) {
    const o = document.createElement("button");
    o.className = "nav-overlay";
    o.dataset.action = "closeMenu";
    document.body.appendChild(o);
  }
}

document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-action]");
  if (!el) return;
  const accion = el.dataset.action;
  if (accion === "toggleMenu") menuMovil(!document.querySelector(".sidebar").classList.contains("mobile-open"));
  if (accion === "closeMenu") menuMovil(false);
  if (accion === "print") window.print();            // en el diálogo elige "Guardar como PDF"
  if (accion === "promo") {
    const activo = el.classList.toggle("btn-dark");
    el.classList.toggle("btn-primary", !activo);
    el.querySelector("span").textContent = activo ? "En promoción ✓" : "Usar en promoción";
    toast(activo ? "Combo agregado a la promoción." : "Combo retirado de la promoción.");
  }
});

/* Ordenar tablas al hacer clic en un encabezado con clase "sortable". */
document.querySelectorAll("th.sortable").forEach((th) => {
  th.addEventListener("click", () => {
    const tabla = th.closest("table");
    const asc = th.dataset.dir !== "asc";
    tabla.querySelectorAll("th").forEach((x) => delete x.dataset.dir);
    th.dataset.dir = asc ? "asc" : "desc";
    const valor = (fila) => { const c = fila.cells[th.cellIndex]; return c.dataset.v ?? c.textContent.trim(); };
    const filas = [...tabla.tBodies[0].rows].sort((a, b) => {
      const x = valor(a), y = valor(b);
      const r = !isNaN(x) && !isNaN(y) ? Number(x) - Number(y) : String(x).localeCompare(String(y), "es");
      return asc ? r : -r;
    });
    filas.forEach((f) => tabla.tBodies[0].appendChild(f));
  });
});
