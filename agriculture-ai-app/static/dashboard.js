// Chatbot logic for home page
(function () {
  const toggleBtn = document.getElementById("chatbot-toggle");
  const container = document.getElementById("chatbot-container");
  const closeBtn = document.getElementById("chatbot-close");
  const input = document.getElementById("chatbot-input");
  const sendBtn = document.getElementById("chatbot-send");
  const messagesEl = document.getElementById("chatbot-messages");
  const suggestionsEl = document.getElementById("chatbot-suggestions");
  let welcomed = false;

  /* ------ Simple markdown → HTML converter ------ */
  function md(text) {
    if (!text) return "";
    let h = text
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      // bold
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      // italic
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      // inline code
      .replace(/`(.+?)`/g, "<code>$1</code>")
      // bullet lines
      .replace(/^[\-•]\s+(.+)/gm, "<li>$1</li>")
      // numbered lines
      .replace(/^\d+\.\s+(.+)/gm, "<li>$1</li>");
    // wrap consecutive <li> in <ul>
    h = h.replace(/((?:<li>.*<\/li>\n?)+)/g, "<ul>$1</ul>");
    // paragraphs from double newlines
    h = h.replace(/\n{2,}/g, "</p><p>");
    // single newlines → <br>
    h = h.replace(/\n/g, "<br>");
    return "<p>" + h + "</p>";
  }

  function appendMessage(text, type) {
    if (!messagesEl) return;
    const div = document.createElement("div");
    div.className = `chatbot-message ${type}`;
    if (type === "bot") {
      div.innerHTML = md(text);
    } else {
      div.textContent = text;
    }
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  function showTyping() {
    const div = document.createElement("div");
    div.className = "chatbot-typing";
    div.id = "chatbot-typing";
    div.innerHTML = "<span></span><span></span><span></span>";
    if (messagesEl) {
      messagesEl.appendChild(div);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }
    return div;
  }

  function removeTyping() {
    const el = document.getElementById("chatbot-typing");
    if (el) el.remove();
  }

  function showWelcome() {
    if (welcomed || !messagesEl) return;
    welcomed = true;
    const welcome = document.createElement("div");
    welcome.className = "chatbot-welcome";
    welcome.innerHTML =
      "<strong>🌾 Namaste! I'm Krishi AI</strong><br>" +
      "Ask me about crops, weather, diseases, government schemes, market prices, or enter your <strong>village PIN code</strong> for local weather advice.";
    messagesEl.appendChild(welcome);
  }

  function hideSuggestions() {
    if (suggestionsEl) suggestionsEl.style.display = "none";
  }

  async function sendMessage(overrideText) {
    const text = overrideText || (input ? input.value.trim() : "");
    if (!text) return;
    hideSuggestions();
    appendMessage(text, "user");
    if (input) input.value = "";

    // Disable send while processing
    if (sendBtn) sendBtn.disabled = true;
    showTyping();

    try {
      const res = await fetch("/api/chatbot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      removeTyping();
      const data = await res.json();
      appendMessage(data.response || "No response received.", "bot");
    } catch (e) {
      removeTyping();
      appendMessage("⚠️ Could not reach the assistant. Please check your connection and try again.", "bot");
      console.error("Chatbot error:", e);
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      if (input) input.focus();
    }
  }

  // Quick-action chip buttons
  if (suggestionsEl) {
    suggestionsEl.addEventListener("click", (e) => {
      const chip = e.target.closest(".chatbot-chip");
      if (!chip) return;
      const msg = chip.dataset.msg;
      if (msg) sendMessage(msg);
    });
  }

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      if (!container) return;
      const opening = container.style.display !== "flex";
      container.style.display = opening ? "flex" : "none";
      if (opening) {
        showWelcome();
        if (input) input.focus();
      }
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", () => {
      if (container) container.style.display = "none";
    });
  }

  if (sendBtn && input) {
    sendBtn.addEventListener("click", () => sendMessage());
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        sendMessage();
      }
    });
  }
})();

// Theme toggle (light / dark) on navbar
(function () {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;

  function applyTheme(mode) {
    const body = document.body;
    if (mode === "dark") {
      body.classList.add("dark-mode");
      btn.textContent = "☀️ Light";
    } else {
      body.classList.remove("dark-mode");
      btn.textContent = "🌙 Dark";
    }
    localStorage.setItem("sk_theme", mode);
  }

  const stored = localStorage.getItem("sk_theme") || "dark";
  applyTheme(stored);

  btn.addEventListener("click", () => {
    const current = document.body.classList.contains("dark-mode") ? "dark" : "light";
    applyTheme(current === "dark" ? "light" : "dark");
  });
})();

// Crop recommendation form
(function () {
  const form = document.getElementById("crop-form");
  if (!form) return;

  const pincodeInput = document.getElementById("crop-pincode");
  const fetchWeatherBtn = document.getElementById("fetch-weather-btn");
  const weatherStatus = document.getElementById("weather-autofill-status");
  const saveStatusEl = document.getElementById("crop-save-status");
  const resultDiv = document.getElementById("crop-result");
  const placeholder = document.getElementById("crop-placeholder");
  const tempInput = form.querySelector("input[name='temperature']");
  const humidityInput = form.querySelector("input[name='humidity']");
  const rainfallInput = form.querySelector("input[name='rainfall']");

  function feedbackLabel(status) {
    if (status === "accepted") return "Accepted";
    if (status === "trying") return "Trying This Crop";
    if (status === "not_suitable") return "Not Suitable";
    return "Pending";
  }

  if (resultDiv) {
    resultDiv.addEventListener("click", async (event) => {
      const btn = event.target.closest(".crop-feedback-save");
      if (!btn) return;

      const recommendationId = Number(btn.dataset.recommendationId || 0);
      const cropName = String(btn.dataset.cropName || "");
      const box = btn.closest(".crop-feedback-box");
      if (!recommendationId || !cropName || !box) return;

      const statusInput = box.querySelector(".crop-feedback-status");
      const commentInput = box.querySelector(".crop-feedback-comment");
      const ratingInput = box.querySelector(".crop-feedback-rating");
      const msgEl = box.querySelector(".crop-feedback-message");

      const feedbackStatus = statusInput ? statusInput.value : "pending";
      const comment = commentInput ? commentInput.value : "";
      const rating = ratingInput ? ratingInput.value : "";

      btn.disabled = true;
      if (msgEl) {
        msgEl.textContent = "Saving feedback...";
        msgEl.className = "crop-feedback-message text-muted";
      }

      try {
        const res = await fetch("/api/recommendation-feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            recommendation_id: recommendationId,
            crop_name: cropName,
            feedback_status: feedbackStatus,
            rating,
            comment,
          }),
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || "Feedback save failed.");
        }

        if (msgEl) {
          msgEl.textContent = `Saved: ${feedbackLabel(data.feedback?.status || feedbackStatus)}`;
          msgEl.className = "crop-feedback-message text-success";
        }
      } catch (err) {
        if (msgEl) {
          msgEl.textContent = err.message || "Feedback save failed.";
          msgEl.className = "crop-feedback-message text-danger";
        }
      } finally {
        btn.disabled = false;
      }
    });
  }

  if (pincodeInput) {
    pincodeInput.addEventListener("input", () => {
      pincodeInput.value = pincodeInput.value.replace(/\D/g, "").slice(0, 6);
    });
  }

  if (fetchWeatherBtn && pincodeInput) {
    fetchWeatherBtn.addEventListener("click", async () => {
      const pincode = (pincodeInput.value || "").trim();
      if (!(pincode.length === 6 && /^\d{6}$/.test(pincode))) {
        if (weatherStatus) {
          weatherStatus.textContent = "Enter a valid 6-digit PIN code.";
          weatherStatus.className = "text-danger";
        }
        return;
      }

      fetchWeatherBtn.disabled = true;
      const originalLabel = fetchWeatherBtn.textContent;
      fetchWeatherBtn.textContent = "Fetching...";
      if (weatherStatus) {
        weatherStatus.textContent = "Getting weather from API...";
        weatherStatus.className = "text-muted";
      }

      try {
        const res = await fetch("/api/weather-by-pincode", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pincode }),
        });

        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.error || "Unable to fetch weather for this PIN code.");
        }

        if (tempInput) tempInput.value = Number(data.temperature || 0).toFixed(1);
        if (humidityInput) humidityInput.value = Number(data.humidity || 0).toFixed(1);
        if (rainfallInput) rainfallInput.value = Number(data.rainfall || 0).toFixed(1);

        if (weatherStatus) {
          const place = data.place_name ? ` (${data.place_name})` : "";
          weatherStatus.textContent = `Auto-filled from weather API${place}.`;
          weatherStatus.className = "text-success";
        }
      } catch (err) {
        if (weatherStatus) {
          weatherStatus.textContent = err.message || "Failed to fetch weather.";
          weatherStatus.className = "text-danger";
        }
      } finally {
        fetchWeatherBtn.disabled = false;
        fetchWeatherBtn.textContent = originalLabel || "Fetch Weather";
      }
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Show loading state
    const btnText = document.getElementById("crop-btn-text");
    const btnSpinner = document.getElementById("crop-btn-spinner");
    const submitBtn = document.getElementById("crop-submit-btn");
    if (btnText) btnText.classList.add("d-none");
    if (btnSpinner) btnSpinner.classList.remove("d-none");
    if (submitBtn) submitBtn.disabled = true;

    const formData = new FormData(form);
    const payload = Object.fromEntries(formData.entries());

    try {
      const res = await fetch("/api/crop-recommendation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!resultDiv) return;

      const recommendationId = Number(data.recommendation_id || 0);
      if (saveStatusEl) {
        if (recommendationId) {
          saveStatusEl.textContent = `Saved to monitoring dashboard (Record #${recommendationId}).`;
          saveStatusEl.className = "d-block mt-2 text-success";
        } else {
          saveStatusEl.textContent = "Recommendation generated but dashboard sync record ID missing.";
          saveStatusEl.className = "d-block mt-2 text-warning";
        }
      }

      // Hide placeholder, show results
      if (placeholder) placeholder.classList.add("d-none");
      resultDiv.classList.remove("d-none");

      // Build HTML for each recommended crop
      let html = "";
      const crops = data.crops || [];

      crops.forEach((crop, idx) => {
        const isPrimary = crop.is_primary;
        const badgeColor = isPrimary ? "#22c55e" : "#3b82f6";
        const badgeText = isPrimary ? "🏆 BEST MATCH" : `#${crop.rank} Alternative`;
        const borderColor = isPrimary
          ? "border: 2px solid #22c55e;"
          : "border: 1px solid rgba(148,163,184,0.35);";

        // Suitability bar color
        const suitScore = crop.suitability_score;
        const barColor =
          suitScore >= 70 ? "#22c55e" : suitScore >= 45 ? "#fbbf24" : "#ef4444";

        // Economics
        const econ = crop.economics || {};
        const profitColor = econ.estimated_profit >= 0 ? "#22c55e" : "#ef4444";

        // Farming plan steps
        let planHTML = "";
        (crop.farming_plan || []).forEach((step, i) => {
          planHTML += `<div style="display:flex; gap:10px; margin-bottom:8px; align-items:flex-start;">
            <span style="background:linear-gradient(135deg,#3b82f6,#8b5cf6); color:#fff; border-radius:50%; min-width:28px; height:28px; display:flex; align-items:center; justify-content:center; font-size:0.8rem; font-weight:700;">${i + 1}</span>
            <span style="flex:1; font-size:0.95rem; line-height:1.5;">${step}</span>
          </div>`;
        });

        // Govt schemes
        let schemesHTML = "";
        (crop.govt_schemes || []).forEach((scheme) => {
          schemesHTML += `<div style="background:linear-gradient(135deg, rgba(34,197,94,0.15), rgba(59,130,246,0.1)); border-left:4px solid #22c55e; padding:12px 16px; border-radius:0 8px 8px 0; margin-bottom:10px;">
            <div style="font-weight:700; font-size:1.05rem; color:#22c55e; margin-bottom:4px;">
              🏛️ ${scheme.name}
            </div>
            <div style="font-size:0.95rem; margin-bottom:6px;">${scheme.benefit}</div>
            <a href="${scheme.link}" target="_blank" rel="noopener" style="color:#60a5fa; font-size:0.85rem; text-decoration:underline;">
              Visit Portal →
            </a>
          </div>`;
        });

        // Accordion ID
        const accId = `crop-detail-${idx}`;
        const feedback = crop.feedback || {};
        const fbStatus = feedback.status || "pending";
        const fbComment = feedback.comment || "";
        const fbRating = feedback.rating || "";

        html += `
        <div class="card-3d mb-4 p-0 overflow-hidden" style="${borderColor}">
          <!-- Crop Header -->
          <div style="padding:1.5rem; cursor:pointer; ${isPrimary ? "background:linear-gradient(135deg, rgba(34,197,94,0.15), rgba(34,197,94,0.05));" : ""}" onclick="document.getElementById('${accId}').classList.toggle('d-none'); this.querySelector('.chevron').classList.toggle('rotate-chevron');">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
              <div>
                <span style="background:${badgeColor}; color:#fff; padding:4px 14px; border-radius:20px; font-size:0.8rem; font-weight:700; display:inline-block; margin-bottom:8px;">
                  ${badgeText}
                </span>
                <h3 style="font-weight:800; margin:0; font-size:1.8rem; ${isPrimary ? "color:#22c55e;" : ""}">${crop.crop_name}</h3>
                <div style="display:flex; gap:16px; flex-wrap:wrap; margin-top:8px;">
                  <span style="font-size:0.9rem;">🌱 ${crop.season}</span>
                  <span style="font-size:0.9rem;">⏱️ ${crop.duration}</span>
                  <span style="font-size:0.9rem;">💧 ${crop.water_requirement}</span>
                </div>
              </div>
              <div style="text-align:right; min-width:140px;">
                <div style="font-size:0.8rem; text-transform:uppercase; font-weight:700; margin-bottom:4px;">Suitability</div>
                <div style="font-size:2rem; font-weight:800; color:${barColor};">${suitScore}%</div>
                <div style="background:rgba(148,163,184,0.3); border-radius:10px; height:8px; width:120px; margin:4px 0 0 auto;">
                  <div style="background:${barColor}; height:100%; border-radius:10px; width:${suitScore}%; transition:width 0.5s ease;"></div>
                </div>
                <span class="chevron" style="display:inline-block; margin-top:8px; font-size:1.2rem; transition:transform 0.3s;">▼</span>
              </div>
            </div>
          </div>

          <!-- Expandable Details -->
          <div id="${accId}" class="${isPrimary ? "" : "d-none"}" style="border-top:1px solid rgba(148,163,184,0.2);">
            <!-- Economics Section -->
            <div style="padding:1.5rem; background:linear-gradient(135deg, rgba(30,41,59,0.3), rgba(15,23,42,0.2));">
              <h5 style="font-weight:700; color:#fbbf24; margin-bottom:1rem;">💰 Financial Estimation</h5>
              <div class="row g-3">
                <div class="col-6 col-md-3">
                  <div style="background:rgba(255,255,255,0.06); border-radius:12px; padding:16px; text-align:center; border:1px solid rgba(148,163,184,0.2);">
                    <div style="font-size:0.8rem; text-transform:uppercase; font-weight:700; margin-bottom:6px;">Investment</div>
                    <div style="font-size:1.4rem; font-weight:800; color:#ef4444;">₹${(econ.estimated_cost || 0).toLocaleString("en-IN")}</div>
                  </div>
                </div>
                <div class="col-6 col-md-3">
                  <div style="background:rgba(255,255,255,0.06); border-radius:12px; padding:16px; text-align:center; border:1px solid rgba(148,163,184,0.2);">
                    <div style="font-size:0.8rem; text-transform:uppercase; font-weight:700; margin-bottom:6px;">Exp. Yield</div>
                    <div style="font-size:1.4rem; font-weight:800; color:#60a5fa;">${(econ.expected_yield_kg || 0).toLocaleString("en-IN")} kg</div>
                  </div>
                </div>
                <div class="col-6 col-md-3">
                  <div style="background:rgba(255,255,255,0.06); border-radius:12px; padding:16px; text-align:center; border:1px solid rgba(148,163,184,0.2);">
                    <div style="font-size:0.8rem; text-transform:uppercase; font-weight:700; margin-bottom:6px;">Revenue (MSP ₹${econ.msp_per_kg}/kg)</div>
                    <div style="font-size:1.4rem; font-weight:800; color:#3b82f6;">₹${(econ.estimated_revenue || 0).toLocaleString("en-IN")}</div>
                  </div>
                </div>
                <div class="col-6 col-md-3">
                  <div style="background:rgba(255,255,255,0.06); border-radius:12px; padding:16px; text-align:center; border:1px solid ${profitColor}30;">
                    <div style="font-size:0.8rem; text-transform:uppercase; font-weight:700; margin-bottom:6px;">Est. Profit</div>
                    <div style="font-size:1.4rem; font-weight:800; color:${profitColor};">₹${(econ.estimated_profit || 0).toLocaleString("en-IN")}</div>
                    <div style="font-size:0.75rem; color:${profitColor}; font-weight:600;">ROI: ${econ.roi_percent || 0}%</div>
                  </div>
                </div>
              </div>
              <div style="margin-top:12px; font-size:0.85rem; text-align:center; font-weight:600;">
                🌾 Fertilizer: ${crop.fertilizer_suggestion}
              </div>
            </div>

            <!-- Farming Plan -->
            <div style="padding:1.5rem;">
              <h5 style="font-weight:700; color:#60a5fa; margin-bottom:1rem;">📋 Step-by-Step Farming Plan</h5>
              ${planHTML}
            </div>

            <!-- Government Schemes -->
            <div style="padding:1.5rem; background:linear-gradient(135deg, rgba(30,41,59,0.3), rgba(15,23,42,0.2));">
              <h5 style="font-weight:700; color:#22c55e; margin-bottom:1rem;">🏛️ Government Subsidies & Schemes</h5>
              ${schemesHTML}
            </div>

            <div style="padding:1.5rem; border-top:1px solid rgba(148,163,184,0.2);" class="crop-feedback-box">
              <h5 style="font-weight:700; color:#0ea5e9; margin-bottom:1rem;">📝 Real-time Feedback</h5>
              <div class="row g-2 align-items-end">
                <div class="col-md-4">
                  <label class="form-label mb-1">Status</label>
                  <select class="form-select form-select-sm crop-feedback-status">
                    <option value="pending" ${fbStatus === "pending" ? "selected" : ""}>Pending</option>
                    <option value="accepted" ${fbStatus === "accepted" ? "selected" : ""}>Accepted</option>
                    <option value="trying" ${fbStatus === "trying" ? "selected" : ""}>Trying This Crop</option>
                    <option value="not_suitable" ${fbStatus === "not_suitable" ? "selected" : ""}>Not Suitable</option>
                  </select>
                </div>
                <div class="col-md-2">
                  <label class="form-label mb-1">Rating</label>
                  <input type="number" min="1" max="5" class="form-control form-control-sm crop-feedback-rating" value="${fbRating}" placeholder="1-5" />
                </div>
                <div class="col-md-4">
                  <label class="form-label mb-1">Comment</label>
                  <input type="text" class="form-control form-control-sm crop-feedback-comment" value="${fbComment}" placeholder="Your feedback" />
                </div>
                <div class="col-md-2">
                  <button type="button" class="btn btn-sm btn-outline-success w-100 crop-feedback-save" data-recommendation-id="${recommendationId}" data-crop-name="${crop.crop_name}">Save</button>
                </div>
              </div>
              <small class="crop-feedback-message text-muted d-block mt-2">Feedback state: ${feedbackLabel(fbStatus)}</small>
            </div>
          </div>
        </div>`;
      });

      resultDiv.innerHTML = html;

      // Scroll to results
      resultDiv.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      console.error("Crop recommendation error:", err);
    } finally {
      // Reset button
      if (btnText) btnText.classList.remove("d-none");
      if (btnSpinner) btnSpinner.classList.add("d-none");
      if (submitBtn) submitBtn.disabled = false;
    }
  });
})();

// Disease detection form
(function () {
  const form = document.getElementById("disease-form");
  const fileInput = document.getElementById("disease-image");
  const preview = document.getElementById("disease-preview");

  if (!form) return;

  // Live preview of selected leaf image
  if (fileInput && preview) {
    fileInput.addEventListener("change", () => {
      const [file] = fileInput.files;
      if (file) {
        preview.src = URL.createObjectURL(file);
        preview.classList.remove("d-none");
      }
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!fileInput.files[0]) return;

    const formData = new FormData();
    formData.append("image", fileInput.files[0]);

    const res = await fetch("/api/disease-detection", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    const card = document.getElementById("disease-result");
    if (!card) return;

    const diseaseNameEl = document.getElementById("disease-name");
    const confidenceEl = document.getElementById("disease-confidence");
    const treatmentEl = document.getElementById("disease-treatment");
    const pesticideEl = document.getElementById("disease-pesticide");

    if (diseaseNameEl) {
      diseaseNameEl.textContent = data.disease || "Unknown";
    }
    if (confidenceEl) {
      confidenceEl.textContent =
        data.confidence !== undefined && data.confidence !== null
          ? `${(data.confidence * 100).toFixed(1)}%`
          : "-";
    }
    if (treatmentEl) {
      treatmentEl.textContent = data.suggestion ||
        (data.disease === "Unknown"
          ? "Model could not confidently classify this image. Try a clearer photo or consult a local agronomist."
          : "-");
    }
    if (pesticideEl) {
      pesticideEl.textContent = data.pesticide || "-";
    }
    card.classList.remove("d-none");
  });
})();

// Drone analysis form
(function () {
  const form = document.getElementById("drone-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("drone-image");
    if (!fileInput.files[0]) return;

    const formData = new FormData();
    formData.append("image", fileInput.files[0]);

    const res = await fetch("/api/drone-analysis", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();

    const card = document.getElementById("drone-result");
    if (!card) return;

    document.getElementById("drone-score").textContent = data.health_score ?? "-";
    document.getElementById("drone-stress").textContent = data.stress_result || "-";

    const diseaseEl = document.getElementById("drone-disease");
    const confEl = document.getElementById("drone-confidence");
    const treatmentEl = document.getElementById("drone-treatment");

    if (diseaseEl) {
      diseaseEl.textContent = data.disease || "Unknown";
    }
    if (confEl) {
      confEl.textContent =
        data.confidence !== undefined && data.confidence !== null
          ? `${(data.confidence * 100).toFixed(1)}%`
          : "-";
    }
    if (treatmentEl) {
      treatmentEl.textContent = data.suggestion || "-";
    }
    card.classList.remove("d-none");
  });
})();

// Satellite / Leaflet map on Drone Monitoring page
(function () {
  const mapContainer = document.getElementById("satelliteMap");
  if (!mapContainer || typeof L === "undefined") return;

  const center = [16.3067, 80.4365]; // Example coordinates (Guntur region)

  const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
  });

  const satellite = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      attribution: "Satellite Imagery",
    }
  );

  const map = L.map("satelliteMap", {
    center,
    zoom: 12,
    layers: [satellite],
  });

  const baseMaps = {
    "Street Map": osm,
    "Satellite Map": satellite,
  };

  L.control.layers(baseMaps).addTo(map);

  const farmMarker = L.marker(center).addTo(map);
  farmMarker.bindPopup("Farmer Field Location").openPopup();

  const stressZone = L.circle(center, {
    color: "red",
    fillColor: "#f03",
    fillOpacity: 0.4,
    radius: 400,
  }).addTo(map);
  stressZone.bindPopup("Possible Crop Stress Area");
  const boundaryPoints = [];

  map.on("click", async function (e) {
    const { lat, lng } = e.latlng;
    boundaryPoints.push([lat, lng]);

    // Draw or update the field boundary polygon
    if (boundaryPoints.length >= 3) {
      if (window.fieldBoundary) {
        window.fieldBoundary.setLatLngs(boundaryPoints);
      } else {
        window.fieldBoundary = L.polygon(boundaryPoints, { color: "#16a34a" }).addTo(map);
      }
    } else {
      L.marker([lat, lng]).addTo(map).bindPopup("Marked field point");
    }

    // Call backend for location insights
    try {
      const res = await fetch("/api/location-insights", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat, lon: lng }),
      });
      const data = await res.json();
      const coordsEl = document.getElementById("loc-coords");
      const placeEl = document.getElementById("loc-place");
      const weatherEl = document.getElementById("loc-weather");
      const soilEl = document.getElementById("loc-soil");
      if (coordsEl) coordsEl.textContent = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
      if (placeEl) placeEl.textContent = data.place || "Unknown";
      if (weatherEl) weatherEl.textContent = data.weather_summary || "--";
      if (soilEl) soilEl.textContent = data.soil_hint || "--";
    } catch (err) {
      console.error("Failed to fetch location insights", err);
    }
  });
})();

// Yield monitoring: save production + charts
(function () {
  const lineCtx = document.getElementById("yield-line-chart");
  const barCtx = document.getElementById("yield-bar-chart");
  const pieCtx = document.getElementById("crop-pie-chart");
  const form = document.getElementById("production-form");
  const messageEl = document.getElementById("production-message");
  const recommendationListEl = document.getElementById("recommendation-monitor-list");
  const recommendationSyncEl = document.getElementById("recommendation-sync-status");

  if ((!lineCtx || !barCtx || !pieCtx) && !form) return;

  let lineChart;
  let barChart;
  let pieChart;

  function feedbackBadgeClass(status) {
    if (status === "accepted") return "success";
    if (status === "trying") return "primary";
    if (status === "not_suitable") return "danger";
    return "secondary";
  }

  function feedbackLabel(status) {
    if (status === "accepted") return "Accepted";
    if (status === "trying") return "Trying";
    if (status === "not_suitable") return "Not Suitable";
    return "Pending";
  }

  async function loadRecommendationMonitoring() {
    if (!recommendationListEl) return;
    try {
      const res = await fetch("/api/recommendation-dashboard?limit=12");
      const data = await res.json();
      const items = data.items || [];

      if (!items.length) {
        recommendationListEl.innerHTML = '<div class="text-muted">No recommendation history available yet.</div>';
        if (recommendationSyncEl) {
          recommendationSyncEl.textContent = "Synced: no records yet";
        }
        return;
      }

      let html = "";
      items.forEach((item) => {
        const crops = item.crops || [];
        const input = item.input_snapshot || {};

        let cropBlocks = "";
        crops.forEach((crop) => {
          const feedback = crop.feedback || {};
          const status = feedback.status || "pending";
          const plan = crop.farming_plan || [];

          let planHtml = "";
          plan.forEach((step, i) => {
            planHtml += `<li style="margin-bottom:4px;">${i + 1}. ${step}</li>`;
          });

          cropBlocks += `
            <div class="border rounded p-2 mb-2" style="border-color: rgba(148,163,184,0.35) !important;">
              <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
                <div><strong>${crop.crop_name || "Unknown"}</strong> <span class="text-muted">(${crop.suitability_score || 0}% suitability)</span></div>
                <span class="badge bg-${feedbackBadgeClass(status)}">${feedbackLabel(status)}</span>
              </div>
              <div class="small text-muted mt-1">Comment: ${feedback.comment || "-"}</div>
              <div class="small text-muted mb-1">Rating: ${feedback.rating || "-"}</div>
              <div class="small fw-semibold">Step-by-Step Farming Plan</div>
              <ol class="small mb-0 ps-3">${planHtml || "<li>No steps provided.</li>"}</ol>
            </div>`;
        });

        html += `
          <div class="border rounded p-3" style="border-color: rgba(148,163,184,0.35) !important;">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2">
              <div>
                <div><strong>Record #${item.id}</strong> - Primary Crop: <strong>${item.primary_crop || "-"}</strong></div>
                <div class="small text-muted">Location: ${item.location || "-"} | PIN: ${item.pincode || "-"}</div>
              </div>
              <div class="small text-muted">${item.updated_at || item.created_at || ""}</div>
            </div>
            <div class="small mt-2 mb-2">Input: Temp ${input.temperature ?? "-"}C, Humidity ${input.humidity ?? "-"}%, Rainfall ${input.rainfall ?? "-"} mm, pH ${input.ph ?? "-"}</div>
            ${cropBlocks}
          </div>`;
      });

      recommendationListEl.innerHTML = html;
      if (recommendationSyncEl) {
        recommendationSyncEl.textContent = `Synced at ${new Date().toLocaleTimeString()}`;
      }
    } catch (err) {
      console.error("Recommendation monitoring sync failed", err);
      if (recommendationSyncEl) {
        recommendationSyncEl.textContent = "Sync failed. Retrying...";
      }
    }
  }

  async function loadYieldDashboard(farmerId = 1) {
    if (!lineCtx || !barCtx || !pieCtx || typeof Chart === "undefined") return;

    try {
      const res = await fetch(`/field_growth/${farmerId}`);
      const rows = await res.json();
      if (!rows || !rows.length) {
        return;
      }

      const labels = rows.map((r) => r.year);
      const production = rows.map((r) => r.production);
      const investment = rows.map((r) => r.investment);
      const profit = rows.map((r) => r.profit);

      if (lineChart) lineChart.destroy();
      if (barChart) barChart.destroy();
      if (pieChart) pieChart.destroy();

      lineChart = new Chart(lineCtx, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "Production (kg)",
              data: production,
              borderColor: "#00b894",
              backgroundColor: "rgba(0,184,148,0.15)",
              tension: 0.3,
            },
          ],
        },
      });

      barChart = new Chart(barCtx, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "Investment (₹)",
              data: investment,
              backgroundColor: "rgba(52,152,219,0.8)",
            },
            {
              label: "Profit (₹)",
              data: profit,
              backgroundColor: "rgba(46,204,113,0.8)",
            },
          ],
        },
        options: { responsive: true, scales: { x: { stacked: false }, y: { beginAtZero: true } } },
      });

      const cropTotals = {};
      rows.forEach((r) => {
        const key = r.crop || "Unknown";
        cropTotals[key] = (cropTotals[key] || 0) + (r.production || 0);
      });

      pieChart = new Chart(pieCtx, {
        type: "pie",
        data: {
          labels: Object.keys(cropTotals),
          datasets: [
            {
              data: Object.values(cropTotals),
              backgroundColor: ["#1abc9c", "#3498db", "#9b59b6", "#e67e22", "#e74c3c", "#f1c40f"],
            },
          ],
        },
      });
    } catch (e) {
      console.error(e);
    }
  }

  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const payload = {
        farmer_id: 1,
        field_id: 1,
        crop: document.getElementById("crop").value,
        year: document.getElementById("year").value,
        investment: document.getElementById("investment").value,
        production: document.getElementById("production").value,
        price: document.getElementById("price").value,
      };

      try {
        const res = await fetch("/add_production", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();

        if (messageEl) {
          const msg = data.error || data.message || "Production saved";
          messageEl.textContent = msg;
          messageEl.classList.remove("d-none");
        }

        await loadYieldDashboard(1);
        await loadRecommendationMonitoring();
      } catch (e) {
        console.error(e);
      }
    });
  }

  // Initial load for farmer 1
  loadYieldDashboard(1);
  loadRecommendationMonitoring();
  if (recommendationListEl) {
    setInterval(loadRecommendationMonitoring, 10000);
  }
})();
