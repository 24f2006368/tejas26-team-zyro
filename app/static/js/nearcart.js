// js file for our nearcart app

function requestLocation(onSuccess, onError) {
  if (!navigator.geolocation) {
    onError && onError("Geolocation is not supported by this browser.");
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => onSuccess(pos.coords.latitude, pos.coords.longitude),
    (err) => onError && onError(err.message || "Location permission denied."),
    { enableHighAccuracy: true, timeout: 8000 }
  );
}

function nearcartUseMyLocation(redirectBase) {
  requestLocation(
    (lat, lon) => {
      const url = new URL(redirectBase, window.location.origin);
      url.searchParams.set("lat", lat);
      url.searchParams.set("lon", lon);
      window.location.href = url.toString();
    },
    (msg) => alert("Could not get your location: " + msg + "\nUse manual location instead.")
  );
}

// Star-rating input widget: turns a hidden <input name="rating"> + `.star-input` buttons into a picker.
document.addEventListener("click", function (e) {
  const star = e.target.closest("[data-star]");
  if (!star) return;
  const group = star.closest("[data-star-group]");
  if (!group) return;
  const value = parseInt(star.getAttribute("data-star"), 10);
  group.querySelector('input[name="rating"]').value = value;
  group.querySelectorAll("[data-star]").forEach((el) => {
    const v = parseInt(el.getAttribute("data-star"), 10);
    el.textContent = v <= value ? "★" : "☆";
  });
});