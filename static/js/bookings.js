document.addEventListener("DOMContentLoaded", async () => {
  const list = document.getElementById("booking-list");
  const alertBox = document.getElementById("bookings-alert");
  if (!list) return;

  async function load() {
    try {
      const { bookings } = await api("/api/bookings");
      if (!bookings.length) {
        list.innerHTML =
          '<p class="empty-state">У вас пока нет бронирований. <a href="/">Найти хостел</a></p>';
        return;
      }

      list.innerHTML = bookings
        .map(
          (b) => `
        <div class="booking-card" data-id="${b.id}">
          <img src="${b.image_url || ""}" alt="" />
          <div class="info">
            <h3>${b.hostel_name}</h3>
            <p class="meta">${b.city} · ${b.room_name}</p>
            <p>${formatDate(b.check_in)} — ${formatDate(b.check_out)} · ${b.guests} гост.</p>
            <p><strong>${formatPrice(b.total_price)}</strong></p>
            <span class="badge ${b.status === "cancelled" ? "unavailable" : ""}">${b.status === "confirmed" ? "Подтверждено" : "Отменено"}</span>
          </div>
          ${
            b.status === "confirmed"
              ? `<button type="button" class="btn btn-danger cancel-btn" data-id="${b.id}">Отменить</button>`
              : ""
          }
        </div>
      `
        )
        .join("");

      list.querySelectorAll(".cancel-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!confirm("Отменить бронирование?")) return;
          try {
            await api(`/api/bookings/${btn.dataset.id}`, { method: "DELETE" });
            await load();
          } catch (err) {
            showAlert(alertBox, err.message);
          }
        });
      });
    } catch (err) {
      showAlert(alertBox, err.message);
    }
  }

  await load();
});
