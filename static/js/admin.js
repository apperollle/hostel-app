document.addEventListener("DOMContentLoaded", () => {
  const listEl = document.getElementById("admin-hostels");
  const alertBox = document.getElementById("admin-alert");
  const modalHostel = document.getElementById("modal-hostel");
  const modalRoom = document.getElementById("modal-room");
  const hostelForm = document.getElementById("hostel-form");
  const roomForm = document.getElementById("room-form");

  if (!listEl) return;

  function openModal(modal) {
    modal.classList.remove("hidden");
  }

  function closeModal(modal) {
    modal.classList.add("hidden");
  }

  document.querySelectorAll("[data-close]").forEach((el) => {
    el.addEventListener("click", () => {
      closeModal(modalHostel);
      closeModal(modalRoom);
    });
  });

  function roomTypeLabel(type) {
    return type === "private" ? "Приватный" : "Общий";
  }

  function renderHostels(hostels) {
    if (!hostels.length) {
      listEl.innerHTML = '<p class="empty-state">Нет хостелов. Добавьте первый.</p>';
      return;
    }

    listEl.innerHTML = hostels
      .map(
        (h) => `
      <section class="admin-card" data-hostel-id="${h.id}">
        <div class="admin-card-head">
          <div>
            <h2>${h.name}</h2>
            <p class="meta">${h.city} · ${h.address}</p>
            <p class="meta">★ ${h.rating} · ${h.review_count} отзывов</p>
          </div>
          <div class="admin-card-actions">
            <a href="/hostel/${h.id}" class="btn btn-outline" target="_blank">На сайте</a>
            <button type="button" class="btn btn-outline edit-hostel" data-id="${h.id}">Изменить</button>
            <button type="button" class="btn btn-danger delete-hostel" data-id="${h.id}">Удалить</button>
          </div>
        </div>
        <p>${h.description}</p>
        <div class="admin-rooms">
          <div class="admin-rooms-head">
            <h3>Номера</h3>
            <button type="button" class="btn btn-primary add-room" data-hostel-id="${h.id}">+ Номер</button>
          </div>
          ${
            h.rooms.length
              ? `<table class="admin-table">
            <thead><tr><th>Название</th><th>Тип</th><th>Цена</th><th>Мест</th><th></th></tr></thead>
            <tbody>
              ${h.rooms
                .map(
                  (r) => `
                <tr>
                  <td>${r.name}</td>
                  <td>${roomTypeLabel(r.room_type)}</td>
                  <td>${formatPrice(r.price_per_night)}</td>
                  <td>${r.total_beds}</td>
                  <td class="table-actions">
                    <button type="button" class="btn btn-outline edit-room"
                      data-id="${r.id}" data-hostel-id="${h.id}"
                      data-name="${r.name}" data-type="${r.room_type}"
                      data-price="${r.price_per_night}" data-beds="${r.total_beds}">Изменить</button>
                    <button type="button" class="btn btn-danger delete-room" data-id="${r.id}">Удалить</button>
                  </td>
                </tr>
              `
                )
                .join("")}
            </tbody>
          </table>`
              : '<p class="meta">Номеров пока нет</p>'
          }
        </div>
      </section>
    `
      )
      .join("");

    bindActions(hostels);
  }

  function bindActions(hostels) {
    document.querySelectorAll(".edit-hostel").forEach((btn) => {
      btn.addEventListener("click", () => {
        const h = hostels.find((x) => x.id === parseInt(btn.dataset.id, 10));
        if (!h) return;
        document.getElementById("modal-hostel-title").textContent = "Редактировать хостел";
        document.getElementById("hostel-id").value = h.id;
        document.getElementById("hostel-name").value = h.name;
        document.getElementById("hostel-city").value = h.city;
        document.getElementById("hostel-address").value = h.address;
        document.getElementById("hostel-desc").value = h.description;
        document.getElementById("hostel-image").value = h.image_url || "";
        openModal(modalHostel);
      });
    });

    document.querySelectorAll(".delete-hostel").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Удалить хостел и все его номера?")) return;
        try {
          await api(`/api/admin/hostels/${btn.dataset.id}`, { method: "DELETE" });
          await load();
        } catch (err) {
          showAlert(alertBox, err.message);
        }
      });
    });

    document.querySelectorAll(".add-room").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.getElementById("modal-room-title").textContent = "Добавить номер";
        document.getElementById("room-id").value = "";
        document.getElementById("room-hostel-id").value = btn.dataset.hostelId;
        roomForm.reset();
        document.getElementById("room-hostel-id").value = btn.dataset.hostelId;
        openModal(modalRoom);
      });
    });

    document.querySelectorAll(".edit-room").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.getElementById("modal-room-title").textContent = "Редактировать номер";
        document.getElementById("room-id").value = btn.dataset.id;
        document.getElementById("room-hostel-id").value = btn.dataset.hostelId;
        document.getElementById("room-name").value = btn.dataset.name;
        document.getElementById("room-type").value = btn.dataset.type;
        document.getElementById("room-price").value = btn.dataset.price;
        document.getElementById("room-beds").value = btn.dataset.beds;
        openModal(modalRoom);
      });
    });

    document.querySelectorAll(".delete-room").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Удалить номер?")) return;
        try {
          await api(`/api/admin/rooms/${btn.dataset.id}`, { method: "DELETE" });
          await load();
        } catch (err) {
          showAlert(alertBox, err.message);
        }
      });
    });
  }

  async function load() {
    clearAlert(alertBox);
    listEl.innerHTML = '<p class="empty-state">Загрузка...</p>';
    try {
      const { hostels } = await api("/api/admin/hostels");
      renderHostels(hostels);
    } catch (err) {
      if (err.message.includes("администратора") || err.message.includes("вход")) {
        window.location.href = "/admin/login";
        return;
      }
      showAlert(alertBox, err.message);
      listEl.innerHTML = "";
    }
  }

  document.getElementById("btn-add-hostel").addEventListener("click", () => {
    document.getElementById("modal-hostel-title").textContent = "Новый хостел";
    document.getElementById("hostel-id").value = "";
    hostelForm.reset();
    openModal(modalHostel);
  });

  hostelForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert(alertBox);
    const id = document.getElementById("hostel-id").value;
    const body = {
      name: document.getElementById("hostel-name").value,
      city: document.getElementById("hostel-city").value,
      address: document.getElementById("hostel-address").value,
      description: document.getElementById("hostel-desc").value,
      image_url: document.getElementById("hostel-image").value,
    };
    try {
      if (id) {
        await api(`/api/admin/hostels/${id}`, { method: "PUT", body: JSON.stringify(body) });
      } else {
        await api("/api/admin/hostels", { method: "POST", body: JSON.stringify(body) });
      }
      closeModal(modalHostel);
      await load();
      showAlert(alertBox, "Хостел сохранён", "success");
    } catch (err) {
      showAlert(alertBox, err.message);
    }
  });

  roomForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert(alertBox);
    const roomId = document.getElementById("room-id").value;
    const hostelId = document.getElementById("room-hostel-id").value;
    const body = {
      name: document.getElementById("room-name").value,
      room_type: document.getElementById("room-type").value,
      price_per_night: parseFloat(document.getElementById("room-price").value),
      total_beds: parseInt(document.getElementById("room-beds").value, 10),
    };
    try {
      if (roomId) {
        await api(`/api/admin/rooms/${roomId}`, { method: "PUT", body: JSON.stringify(body) });
      } else {
        await api(`/api/admin/hostels/${hostelId}/rooms`, {
          method: "POST",
          body: JSON.stringify(body),
        });
      }
      closeModal(modalRoom);
      await load();
      showAlert(alertBox, "Номер сохранён", "success");
    } catch (err) {
      showAlert(alertBox, err.message);
    }
  });

  load();
});
