async function generate(campaign, fmt) {
  const status = document.getElementById("status");
  const buttons = document.querySelectorAll("button");
  buttons.forEach((b) => { b.disabled = true; });
  status.textContent = "Tracking beats and rendering the " + campaign + " film. This can take a minute.";
  try {
    const res = await fetch("/api/generate/" + campaign + "/" + fmt, { method: "POST" });
    if (!res.ok) {
      throw new Error("Render failed");
    }
    const data = await res.json();
    status.textContent = data.cta + " film ready · " + Math.round(data.tempo) + " BPM · " + data.url;
    window.location.reload();
  } catch (err) {
    status.textContent = "Could not render. Try again.";
    buttons.forEach((b) => { b.disabled = false; });
  }
}

document.querySelectorAll("button[data-campaign]").forEach((button) => {
  button.addEventListener("click", () => generate(button.dataset.campaign, button.dataset.fmt));
});
