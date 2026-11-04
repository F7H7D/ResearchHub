document.addEventListener("DOMContentLoaded", () => {
  // Auto-dismiss toasts
  document.querySelectorAll(".toast").forEach((toast) => {
    setTimeout(() => {
      toast.style.transition = "opacity 0.3s, transform 0.3s";
      toast.style.opacity = "0";
      toast.style.transform = "translateX(16px)";
      setTimeout(() => toast.remove(), 300);
    }, 4800);
  });
});