/* Apply the saved preference before the stylesheet paints. CSS handles System. */
(() => {
  const key = "enfusion-neural-theme";
  const valid = value => ["system", "light", "dark"].includes(value);
  let theme = "system";
  try {
    const saved = localStorage.getItem(key);
    if (valid(saved)) theme = saved;
  } catch (_) { /* Theme selection still works when storage is unavailable. */ }
  document.documentElement.dataset.theme = theme;
  document.addEventListener("DOMContentLoaded", () => {
    const controls = document.querySelectorAll("[data-theme-control]");
    controls.forEach(control => {
      control.value = theme;
      control.addEventListener("change", () => {
        if (!valid(control.value)) return;
        theme = control.value;
        document.documentElement.dataset.theme = theme;
        controls.forEach(other => { other.value = theme; });
        try { localStorage.setItem(key, theme); } catch (_) { /* Device-local preference only. */ }
      });
    });
  });
})();
