/* Enhance the two labeled images into a keyboard-accessible wipe comparison. */
document.querySelectorAll("[data-comparison]").forEach(comparison => {
  const images = [...comparison.querySelectorAll("img")];
  const control = comparison.querySelector(".comparison-control");
  const range = control.querySelector("input");
  const output = control.querySelector("output");
  const update = () => {
    const value = Math.max(0, Math.min(100, Number(range.value) || 0));
    comparison.style.setProperty("--reveal", `${value}%`);
    const description = `${value}% original, ${100 - value}% model output`;
    range.setAttribute("aria-valuetext", description);
    output.textContent = `${value}% original`;
  };
  const ready = () => {
    if (!images.every(img => img.complete && img.naturalWidth > 0)) return;
    if (!images.every(img => img.naturalWidth === images[0].naturalWidth && img.naturalHeight === images[0].naturalHeight)) return;
    update();
    comparison.classList.add("is-interactive");
    control.hidden = false;
  };
  range.addEventListener("input", update);
  images.forEach(img => img.addEventListener("load", ready));
  ready();
});
