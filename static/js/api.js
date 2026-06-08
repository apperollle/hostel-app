async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    credentials: "same-origin",
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || "Ошибка запроса");
  }
  return data;
}

function formatPrice(value) {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatDate(iso) {
  return new Date(iso + "T12:00:00").toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function getSearchParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    city: params.get("city") || "",
    check_in: params.get("check_in") || "",
    check_out: params.get("check_out") || "",
    guests: params.get("guests") || "1",
    q: params.get("q") || "",
  };
}

function buildSearchQuery(overrides = {}) {
  const base = getSearchParams();
  const merged = { ...base, ...overrides };
  const params = new URLSearchParams();
  Object.entries(merged).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

function defaultDates() {
  const today = new Date();
  const checkIn = new Date(today);
  checkIn.setDate(checkIn.getDate() + 3);
  const checkOut = new Date(checkIn);
  checkOut.setDate(checkOut.getDate() + 2);
  return {
    check_in: checkIn.toISOString().slice(0, 10),
    check_out: checkOut.toISOString().slice(0, 10),
  };
}

function showAlert(container, message, type = "error") {
  container.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
}

function clearAlert(container) {
  container.innerHTML = "";
}
