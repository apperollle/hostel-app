document.addEventListener("DOMContentLoaded", async () => {
  const form = document.getElementById("search-form");
  const grid = document.getElementById("hostel-grid");
  const alertBox = document.getElementById("search-alert");
  const citySelect = document.getElementById("city");
  const defaults = defaultDates();

  if (!form || !grid) return;

  try {
    const { cities } = await api("/api/cities");
    cities.forEach((city) => {
      const opt = document.createElement("option");
      opt.value = city;
      opt.textContent = city;
      citySelect.appendChild(opt);
    });
  } catch (_) {
    /* cities optional */
  }

  const params = getSearchParams();
  form.city.value = params.city || "";
  form.check_in.value = params.check_in || defaults.check_in;
  form.check_out.value = params.check_out || defaults.check_out;
  form.guests.value = params.guests || "1";
  if (form.q) form.q.value = params.q || "";

  async function loadHostels() {
    clearAlert(alertBox);
    grid.innerHTML = '<p class="empty-state">Загрузка...</p>';

    const qs = new URLSearchParams({
      city: form.city.value,
      check_in: form.check_in.value,
      check_out: form.check_out.value,
      guests: form.guests.value,
    });
    if (form.q && form.q.value) qs.set("q", form.q.value);

    try {
      const { hostels } = await api(`/api/hostels?${qs}`);
      if (!hostels.length) {
        grid.innerHTML =
          '<p class="empty-state">Хостелы не найдены. Измените даты или город.</p>';
        return;
      }

      grid.innerHTML = hostels
        .map(
          (h) => `
        <article class="hostel-card">
          <a href="/hostel/${h.id}${buildSearchQuery()}">
            <img src="${h.image_url || ""}" alt="${h.name}" loading="lazy" />
          </a>
          <div class="body">
            <h3><a href="/hostel/${h.id}${buildSearchQuery()}">${h.name}</a></h3>
            <p class="meta">${h.city} · ${h.address}</p>
            <p class="rating">★ ${h.rating} (${h.review_count} отзывов)</p>
            <p class="price">от ${formatPrice(h.min_price)} / ночь</p>
          </div>
        </article>
      `
        )
        .join("");
    } catch (err) {
      showAlert(alertBox, err.message);
      grid.innerHTML = "";
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const qs = buildSearchQuery({
      city: form.city.value,
      check_in: form.check_in.value,
      check_out: form.check_out.value,
      guests: form.guests.value,
      q: form.q ? form.q.value : "",
    });
    window.history.replaceState(null, "", `/${qs}`);
    loadHostels();
  });

  await loadHostels();
});
