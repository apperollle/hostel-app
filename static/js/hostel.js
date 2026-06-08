document.addEventListener("DOMContentLoaded", async () => {
  const root = document.getElementById("hostel-detail");
  if (!root) return;

  const hostelId = root.dataset.hostelId;
  const alertBox = document.getElementById("detail-alert");
  const params = getSearchParams();
  const defaults = defaultDates();
  const checkIn = params.check_in || defaults.check_in;
  const checkOut = params.check_out || defaults.check_out;
  const guests = params.guests || "1";

  document.getElementById("book-check-in").value = checkIn;
  document.getElementById("book-check-out").value = checkOut;
  document.getElementById("book-guests").value = guests;

  let selectedRoomId = null;

  async function loadDetail() {
    const qs = new URLSearchParams({ check_in: checkIn, check_out: checkOut, guests });
    try {
      const data = await api(`/api/hostels/${hostelId}?${qs}`);
      const { hostel, rooms, reviews } = data;

      document.getElementById("hostel-title").textContent = hostel.name;
      document.getElementById("hostel-city").textContent = `${hostel.city} · ${hostel.address}`;
      document.getElementById("hostel-desc").textContent = hostel.description;
      document.getElementById("hostel-rating").textContent =
        `★ ${hostel.rating} (${hostel.review_count} отзывов)`;
      document.getElementById("hostel-image").src = hostel.image_url || "";

      const roomList = document.getElementById("room-list");
      roomList.innerHTML = rooms
        .map((room) => {
          const typeLabel = room.room_type === "dorm" ? "Общий" : "Приватный";
          const avail = room.available
            ? `<span class="badge">Свободно ${room.free_beds} мест</span>`
            : `<span class="badge unavailable">${room.unavailable_reason || "Нет мест"}</span>`;
          const total =
            room.total_price != null
              ? `<strong>${formatPrice(room.total_price)}</strong> за период`
              : `${formatPrice(room.price_per_night)} / ночь`;

          return `
            <div class="room-item" data-room-id="${room.id}" data-available="${room.available}">
              <div>
                <strong>${room.name}</strong>
                <p class="meta">${typeLabel} · до ${room.total_beds} гостей</p>
                ${avail}
              </div>
              <div>
                <p>${total}</p>
                ${
                  room.available
                    ? `<button type="button" class="btn btn-primary select-room" data-id="${room.id}">Выбрать</button>`
                    : ""
                }
              </div>
            </div>
          `;
        })
        .join("");

      roomList.querySelectorAll(".select-room").forEach((btn) => {
        btn.addEventListener("click", () => {
          selectedRoomId = parseInt(btn.dataset.id, 10);
          roomList.querySelectorAll(".room-item").forEach((el) => {
            el.style.outline =
              parseInt(el.dataset.roomId, 10) === selectedRoomId
                ? "2px solid var(--primary)"
                : "";
          });
          document.getElementById("selected-room").textContent =
            `Выбран номер #${selectedRoomId}`;
        });
      });

      const reviewsEl = document.getElementById("reviews-list");
      reviewsEl.innerHTML = reviews.length
        ? reviews
            .map(
              (r) => `
          <div class="review-item">
            <strong>${r.user_name}</strong>
            <span class="rating">★ ${r.rating}</span>
            <p>${r.comment}</p>
            <small class="meta">${formatDate(r.created_at.slice(0, 10))}</small>
          </div>
        `
            )
            .join("")
        : '<p class="meta">Пока нет отзывов</p>';
    } catch (err) {
      showAlert(alertBox, err.message);
    }
  }

  document.getElementById("book-btn").addEventListener("click", async () => {
    clearAlert(alertBox);
    if (!selectedRoomId) {
      showAlert(alertBox, "Выберите номер");
      return;
    }

    try {
      const result = await api("/api/bookings", {
        method: "POST",
        body: JSON.stringify({
          room_id: selectedRoomId,
          check_in: document.getElementById("book-check-in").value,
          check_out: document.getElementById("book-check-out").value,
          guests: parseInt(document.getElementById("book-guests").value, 10),
        }),
      });
      showAlert(
        alertBox,
        `${result.message}: ${result.hostel_name}, ${formatPrice(result.total_price)}`,
        "success"
      );
      setTimeout(() => {
        window.location.href = "/bookings";
      }, 1500);
    } catch (err) {
      if (err.message.includes("вход")) {
        window.location.href = "/login";
        return;
      }
      showAlert(alertBox, err.message);
    }
  });

  let reviewRating = 0;
  document.querySelectorAll(".stars-input button").forEach((btn) => {
    btn.addEventListener("click", () => {
      reviewRating = parseInt(btn.dataset.star, 10);
      document.querySelectorAll(".stars-input button").forEach((b) => {
        b.classList.toggle("active", parseInt(b.dataset.star, 10) <= reviewRating);
      });
    });
  });

  document.getElementById("review-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert(document.getElementById("review-alert"));
    try {
      await api(`/api/hostels/${hostelId}/reviews`, {
        method: "POST",
        body: JSON.stringify({
          rating: reviewRating,
          comment: document.getElementById("review-comment").value,
        }),
      });
      showAlert(document.getElementById("review-alert"), "Спасибо за отзыв!", "success");
      e.target.reset();
      reviewRating = 0;
      await loadDetail();
    } catch (err) {
      if (err.message.includes("вход") || err.message.includes("Требуется")) {
        window.location.href = "/login";
        return;
      }
      showAlert(document.getElementById("review-alert"), err.message);
    }
  });

  await loadDetail();
});
