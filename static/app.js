const state = {
  meta: { roles: [] },
  people: [],
  sundays: [],
  selectedSundayId: null,
  currentRota: null,
};

const elements = {
  personForm: document.getElementById("person-form"),
  personName: document.getElementById("person-name"),
  peopleList: document.getElementById("people-list"),
  peopleMessage: document.getElementById("people-message"),
  sundayForm: document.getElementById("sunday-form"),
  sundayDate: document.getElementById("sunday-date"),
  sundayList: document.getElementById("sundays-list"),
  sundayMessage: document.getElementById("sunday-message"),
  rotaTitle: document.getElementById("rota-title"),
  rotaGrid: document.getElementById("rota-grid"),
  rotaMessage: document.getElementById("rota-message"),
  clashSummary: document.getElementById("clash-summary"),
  saveRota: document.getElementById("save-rota"),
};

function roleLabel(limit) {
  return `${limit} ${limit === 1 ? "slot" : "slots"}`;
}

function formatLongDate(value) {
  return new Date(`${value}T12:00:00`).toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function isSunday(value) {
  if (!value) return false;
  return new Date(`${value}T12:00:00`).getDay() === 0;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json() : null;
  if (!response.ok) {
    throw new Error(payload?.error || "Request failed.");
  }
  return payload;
}

function setMessage(node, message = "", type = "") {
  node.textContent = message;
  node.className = "message";
  if (type) {
    node.classList.add(type);
  }
}

function getActivePeople() {
  return state.people.filter((person) => person.active);
}

function renderPeople() {
  if (!state.people.length) {
    elements.peopleList.innerHTML = `<div class="empty-state">No people added yet.</div>`;
    return;
  }

  elements.peopleList.innerHTML = state.people
    .map(
      (person) => `
        <article class="person-card">
          <div class="person-row">
            <div>
              <div class="person-name">${escapeHtml(person.name)}</div>
              <div class="person-status">
                <span class="tag ${person.active ? "active" : "inactive"}">
                  ${person.active ? "Active" : "Inactive"}
                </span>
              </div>
            </div>
            <div class="person-actions">
              <button
                type="button"
                class="ghost-button"
                data-person-toggle="${person.id}"
              >
                ${person.active ? "Deactivate" : "Reactivate"}
              </button>
            </div>
          </div>
        </article>
      `
    )
    .join("");
}

function renderSundays() {
  if (!state.sundays.length) {
    elements.sundayList.innerHTML = `<div class="empty-state">No Sundays added yet.</div>`;
    return;
  }

  elements.sundayList.innerHTML = state.sundays
    .map(
      (sunday) => `
        <article class="sunday-card ${state.selectedSundayId === sunday.id ? "selected" : ""}">
          <div class="sunday-row">
            <div>
              <div class="sunday-name">${escapeHtml(formatLongDate(sunday.service_date))}</div>
              <div class="sunday-meta">${escapeHtml(sunday.service_date)}</div>
            </div>
            <div class="sunday-actions">
              <button
                type="button"
                class="ghost-button"
                data-sunday-select="${sunday.id}"
              >
                ${state.selectedSundayId === sunday.id ? "Selected" : "Open"}
              </button>
              <button
                type="button"
                class="ghost-button"
                data-sunday-delete="${sunday.id}"
              >
                Delete
              </button>
            </div>
          </div>
        </article>
      `
    )
    .join("");
}

function gatherSelections() {
  if (!state.currentRota) return null;
  const assignments = {};
  for (const role of state.currentRota.roles) {
    assignments[role.key] = [];
    for (let slotIndex = 0; slotIndex < role.limit; slotIndex += 1) {
      const select = document.querySelector(`[data-role="${role.key}"][data-slot="${slotIndex}"]`);
      const value = select?.value ? Number(select.value) : null;
      assignments[role.key].push(Number.isNaN(value) ? null : value);
    }
  }
  return assignments;
}

function getClashes(assignments) {
  const occurrences = new Map();
  const clashes = new Set();

  Object.entries(assignments).forEach(([roleKey, slots]) => {
    slots.forEach((personId, slotIndex) => {
      if (!personId) return;
      const key = String(personId);
      const list = occurrences.get(key) || [];
      list.push({ roleKey, slotIndex });
      occurrences.set(key, list);
    });
  });

  occurrences.forEach((list, personId) => {
    if (list.length > 1) {
      list.forEach((entry) => clashes.add(`${entry.roleKey}:${entry.slotIndex}`));
    }
  });

  const duplicateNames = Array.from(occurrences.entries())
    .filter(([, list]) => list.length > 1)
    .map(([personId]) => state.people.find((person) => person.id === Number(personId))?.name)
    .filter(Boolean);

  return { clashes, duplicateNames };
}

function renderClashSummary(assignments) {
  const { clashes, duplicateNames } = getClashes(assignments);
  if (!duplicateNames.length) {
    elements.clashSummary.innerHTML = `<div class="clash-box hidden"></div>`;
    return clashes;
  }

  const names = duplicateNames.map(escapeHtml).join(", ");
  elements.clashSummary.innerHTML = `
    <div class="clash-box">
      Clash detected: ${names} ${duplicateNames.length === 1 ? "is" : "are"} serving more than once on this Sunday.
    </div>
  `;
  return clashes;
}

function renderRota() {
  if (!state.currentRota) {
    elements.rotaTitle.textContent = "Select a Sunday";
    elements.rotaGrid.className = "rota-grid empty-state";
    elements.rotaGrid.textContent = "Choose or add a Sunday to start assigning people.";
    elements.clashSummary.innerHTML = "";
    elements.saveRota.disabled = true;
    return;
  }

  elements.rotaTitle.textContent = formatLongDate(state.currentRota.sunday.service_date);
  elements.rotaGrid.className = "rota-grid";
  elements.saveRota.disabled = false;

  const activePeople = getActivePeople();
  const assignments = {};
  for (const role of state.currentRota.roles) {
    assignments[role.key] = role.assignments.map((entry) => entry.personId || null);
  }
  const clashKeys = renderClashSummary(assignments);

  elements.rotaGrid.innerHTML = state.currentRota.roles
    .map((role) => {
      const slotMarkup = role.assignments
        .map((assignment) => {
          const clash = clashKeys.has(`${role.key}:${assignment.slotIndex}`);
          const options = [
            `<option value="">Unassigned</option>`,
            ...activePeople.map(
              (person) => `
                <option value="${person.id}" ${person.id === assignment.personId ? "selected" : ""}>
                  ${escapeHtml(person.name)}
                </option>
              `
            ),
          ].join("");

          return `
            <div class="slot-row ${clash ? "clash" : ""}">
              <label class="slot-label" for="${role.key}-${assignment.slotIndex}">
                Slot ${assignment.slotIndex + 1}
              </label>
              <select
                id="${role.key}-${assignment.slotIndex}"
                data-role="${role.key}"
                data-slot="${assignment.slotIndex}"
              >
                ${options}
              </select>
            </div>
          `;
        })
        .join("");

      return `
        <article class="role-card">
          <div class="role-header">
            <div>
              <h3>${escapeHtml(role.label)}</h3>
            </div>
            <div class="role-limit">${escapeHtml(roleLabel(role.limit))}</div>
          </div>
          <div class="slot-list">${slotMarkup}</div>
        </article>
      `;
    })
    .join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function loadMeta() {
  state.meta = await api("/meta");
}

async function loadPeople() {
  const payload = await api("/people");
  state.people = payload.people;
  renderPeople();
}

async function loadSundays() {
  const payload = await api("/sundays");
  state.sundays = payload.sundays;
  if (state.selectedSundayId && !state.sundays.find((item) => item.id === state.selectedSundayId)) {
    state.selectedSundayId = null;
    state.currentRota = null;
  }
  renderSundays();
}

async function loadRota(sundayId) {
  state.currentRota = await api(`/rotas/${sundayId}`);
  state.selectedSundayId = sundayId;
  renderSundays();
  renderRota();
}

elements.personForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage(elements.peopleMessage);
  try {
    await api("/people", {
      method: "POST",
      body: JSON.stringify({ name: elements.personName.value }),
    });
    elements.personForm.reset();
    await loadPeople();
    renderRota();
    setMessage(elements.peopleMessage, "Person added.", "success");
  } catch (error) {
    setMessage(elements.peopleMessage, error.message, "error");
  }
});

elements.sundayForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setMessage(elements.sundayMessage);
  const serviceDate = elements.sundayDate.value;
  if (!isSunday(serviceDate)) {
    setMessage(elements.sundayMessage, "Please choose a Sunday date.", "error");
    return;
  }

  try {
    const sunday = await api("/sundays", {
      method: "POST",
      body: JSON.stringify({ serviceDate }),
    });
    elements.sundayForm.reset();
    await loadSundays();
    await loadRota(sunday.id);
    setMessage(elements.sundayMessage, "Sunday added.", "success");
  } catch (error) {
    setMessage(elements.sundayMessage, error.message, "error");
  }
});

elements.peopleList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-person-toggle]");
  if (!button) return;
  const personId = Number(button.dataset.personToggle);
  const person = state.people.find((entry) => entry.id === personId);
  if (!person) return;

  setMessage(elements.peopleMessage);
  try {
    await api(`/people/${personId}`, {
      method: "PATCH",
      body: JSON.stringify({ active: !person.active }),
    });
    await loadPeople();
    if (state.selectedSundayId) {
      await loadRota(state.selectedSundayId);
    } else {
      renderRota();
    }
    setMessage(
      elements.peopleMessage,
      `${person.name} ${person.active ? "deactivated" : "reactivated"}.`,
      "success"
    );
  } catch (error) {
    setMessage(elements.peopleMessage, error.message, "error");
  }
});

elements.sundayList.addEventListener("click", async (event) => {
  const selectButton = event.target.closest("[data-sunday-select]");
  if (selectButton) {
    const sundayId = Number(selectButton.dataset.sundaySelect);
    setMessage(elements.rotaMessage);
    try {
      await loadRota(sundayId);
    } catch (error) {
      setMessage(elements.rotaMessage, error.message, "error");
    }
    return;
  }

  const deleteButton = event.target.closest("[data-sunday-delete]");
  if (!deleteButton) return;

  const sundayId = Number(deleteButton.dataset.sundayDelete);
  const targetSunday = state.sundays.find((entry) => entry.id === sundayId);
  if (!targetSunday) return;

  const confirmed = window.confirm(`Delete ${formatLongDate(targetSunday.service_date)}?`);
  if (!confirmed) return;

  try {
    await api(`/sundays/${sundayId}`, { method: "DELETE" });
    await loadSundays();
    if (state.selectedSundayId === sundayId) {
      state.currentRota = null;
      state.selectedSundayId = null;
      renderRota();
    }
    setMessage(elements.sundayMessage, "Sunday deleted.", "success");
  } catch (error) {
    setMessage(elements.sundayMessage, error.message, "error");
  }
});

elements.rotaGrid.addEventListener("change", () => {
  const assignments = gatherSelections();
  if (!assignments) return;
  const clashKeys = renderClashSummary(assignments);
  document.querySelectorAll(".slot-row").forEach((row) => row.classList.remove("clash"));
  clashKeys.forEach((key) => {
    const [roleKey, slotIndex] = key.split(":");
    const row = document.querySelector(`[data-role="${roleKey}"][data-slot="${slotIndex}"]`)?.closest(".slot-row");
    if (row) row.classList.add("clash");
  });
});

elements.saveRota.addEventListener("click", async () => {
  if (!state.selectedSundayId) return;
  const assignments = gatherSelections();
  const { duplicateNames } = getClashes(assignments);
  if (duplicateNames.length) {
    setMessage(
      elements.rotaMessage,
      `Please resolve clashes before saving: ${duplicateNames.join(", ")}.`,
      "error"
    );
    return;
  }

  setMessage(elements.rotaMessage);
  try {
    state.currentRota = await api(`/rotas/${state.selectedSundayId}/assignments`, {
      method: "PUT",
      body: JSON.stringify({ assignments }),
    });
    renderRota();
    setMessage(elements.rotaMessage, "Rota saved.", "success");
  } catch (error) {
    setMessage(elements.rotaMessage, error.message, "error");
  }
});

async function boot() {
  try {
    await loadMeta();
    await Promise.all([loadPeople(), loadSundays()]);
    if (state.sundays.length) {
      await loadRota(state.sundays[0].id);
    } else {
      renderRota();
    }
  } catch (error) {
    setMessage(elements.rotaMessage, error.message, "error");
  }
}

boot();
