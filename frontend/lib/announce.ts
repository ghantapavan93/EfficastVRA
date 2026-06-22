/** Push a message to the global polite live region for screen readers. */
export function announce(message: string) {
  if (typeof document === "undefined") return;
  const el = document.getElementById("vra-live");
  if (el) {
    el.textContent = "";
    // next tick so repeated identical messages still announce
    window.setTimeout(() => {
      el.textContent = message;
    }, 30);
  }
}
