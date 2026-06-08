document.addEventListener("DOMContentLoaded", () => {
  const loginForm = document.getElementById("login-form");
  const adminLoginForm = document.getElementById("admin-login-form");
  const registerForm = document.getElementById("register-form");
  const alertBox = document.getElementById("auth-alert");

  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearAlert(alertBox);
      const fd = new FormData(loginForm);
      try {
        await api("/api/login", {
          method: "POST",
          body: JSON.stringify({
            email: fd.get("email"),
            password: fd.get("password"),
          }),
        });
        window.location.href = "/bookings";
      } catch (err) {
        showAlert(alertBox, err.message);
      }
    });
  }

  if (adminLoginForm) {
    adminLoginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearAlert(alertBox);
      const fd = new FormData(adminLoginForm);
      try {
        await api("/api/admin/login", {
          method: "POST",
          body: JSON.stringify({
            email: fd.get("email"),
            password: fd.get("password"),
          }),
        });
        window.location.href = "/admin";
      } catch (err) {
        showAlert(alertBox, err.message);
      }
    });
  }

  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      clearAlert(alertBox);
      const fd = new FormData(registerForm);
      try {
        await api("/api/register", {
          method: "POST",
          body: JSON.stringify({
            name: fd.get("name"),
            email: fd.get("email"),
            password: fd.get("password"),
          }),
        });
        window.location.href = "/";
      } catch (err) {
        showAlert(alertBox, err.message);
      }
    });
  }
});
