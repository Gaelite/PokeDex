/**
 * PokeSearch Engine - Frontend JavaScript
 * Autocomplete, Term Highlighting, Cry Playback, Detail Modal
 */

document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("searchInput");
    const dropdown = document.getElementById("autocompleteDropdown");
    const modalOverlay = document.getElementById("modalOverlay");
    const modalBody = document.getElementById("modalBody");
    const modalClose = document.getElementById("modalClose");

    let activeIndex = -1;
    let debounceTimer = null;
    let currentAudio = null;

    // ========================================
    // AUTOCOMPLETE
    // ========================================
    searchInput.addEventListener("input", () => {
        clearTimeout(debounceTimer);
        const words = searchInput.value.trim().split(/\s+/);
        const lastWord = words[words.length - 1];

        if (lastWord.length < 2) {
            hideDropdown();
            return;
        }

        debounceTimer = setTimeout(() => {
            fetchAutocomplete(lastWord);
        }, 150);
    });

    async function fetchAutocomplete(prefix) {
        try {
            const res = await fetch(`/api/autocomplete?q=${encodeURIComponent(prefix)}`);
            const data = await res.json();
            if (data.suggestions && data.suggestions.length > 0) {
                renderDropdown(data.suggestions, prefix);
            } else {
                hideDropdown();
            }
        } catch (e) {
            hideDropdown();
        }
    }

    function renderDropdown(items, prefix) {
        activeIndex = -1;
        dropdown.innerHTML = items.map((item, i) => {
            const match = item.substring(0, prefix.length);
            const rest = item.substring(prefix.length);
            return `<div class="ac-item" data-index="${i}" data-value="${item}">
                <span class="ac-match">${match}</span>${rest}
            </div>`;
        }).join("");
        dropdown.classList.add("visible");

        dropdown.querySelectorAll(".ac-item").forEach(el => {
            el.addEventListener("mousedown", (e) => {
                e.preventDefault();
                selectSuggestion(el.dataset.value);
            });
        });
    }

    function hideDropdown() {
        dropdown.classList.remove("visible");
        dropdown.innerHTML = "";
        activeIndex = -1;
    }

    function selectSuggestion(value) {
        const words = searchInput.value.trim().split(/\s+/);
        words[words.length - 1] = value;
        searchInput.value = words.join(" ") + " ";
        hideDropdown();
        searchInput.focus();
    }

    searchInput.addEventListener("keydown", (e) => {
        if (!dropdown.classList.contains("visible")) return;
        const items = dropdown.querySelectorAll(".ac-item");

        if (e.key === "ArrowDown") {
            e.preventDefault();
            activeIndex = Math.min(activeIndex + 1, items.length - 1);
            updateActiveItem(items);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            activeIndex = Math.max(activeIndex - 1, -1);
            updateActiveItem(items);
        } else if (e.key === "Enter" && activeIndex >= 0) {
            e.preventDefault();
            selectSuggestion(items[activeIndex].dataset.value);
        } else if (e.key === "Escape") {
            hideDropdown();
        }
    });

    function updateActiveItem(items) {
        items.forEach((item, i) => {
            item.classList.toggle("active", i === activeIndex);
        });
    }

    searchInput.addEventListener("blur", () => {
        setTimeout(hideDropdown, 200);
    });

    // ========================================
    // TERM HIGHLIGHTING
    // ========================================
    document.querySelectorAll(".card-text[data-query]").forEach(el => {
        const query = el.dataset.query;
        if (!query) return;

        const terms = query.toLowerCase().split(/\s+/).filter(t => t.length > 1);
        if (terms.length === 0) return;

        let html = el.textContent;
        terms.forEach(term => {
            const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
            const regex = new RegExp(`\\b(${escaped}\\w{0,4})\\b`, "gi");
            html = html.replace(regex, '<span class="highlight">$1</span>');
        });
        el.innerHTML = html;
    });

    // ========================================
    // CRY PLAYBACK
    // ========================================
    document.querySelectorAll(".cry-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            playCry(btn.dataset.cry, btn);
        });
    });

    function playCry(url, btn) {
        if (currentAudio) {
            currentAudio.pause();
            document.querySelectorAll(".cry-btn, .modal-cry-btn").forEach(b => b.classList.remove("playing"));
        }
        currentAudio = new Audio(url);
        if (btn) btn.classList.add("playing");
        currentAudio.play().catch(() => {});
        currentAudio.addEventListener("ended", () => {
            if (btn) btn.classList.remove("playing");
            currentAudio = null;
        });
    }

    // ========================================
    // DETAIL MODAL
    // ========================================
    document.querySelectorAll(".pokemon-card").forEach(card => {
        card.addEventListener("click", () => {
            const data = JSON.parse(card.dataset.pokemon);
            openModal(data);
        });
    });

    function openModal(p) {
        const statNames = { hp: "HP", attack: "ATK", defense: "DEF",
            "special-attack": "SPA", "special-defense": "SPD", speed: "SPE" };
        const statColors = { hp: "#e23636", attack: "#e07030", defense: "#f0c040",
            "special-attack": "#5070d0", "special-defense": "#40a060", speed: "#c03060" };
        const maxStat = 255;

        const spriteUrl = `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${p.id}.png`;
        const fallbackSprite = `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${p.id}.png`;
        const cryUrl = `https://raw.githubusercontent.com/PokeAPI/cries/main/cries/pokemon/latest/${p.id}.ogg`;

        let statsHtml = "";
        if (p.stats) {
            const order = ["hp", "attack", "defense", "special-attack", "special-defense", "speed"];
            order.forEach(key => {
                const val = p.stats[key] || 0;
                const pct = Math.min((val / maxStat) * 100, 100);
                const color = statColors[key] || "#888";
                statsHtml += `
                    <div class="stat-row">
                        <span class="stat-name">${statNames[key] || key}</span>
                        <div class="stat-bar-bg">
                            <div class="stat-bar-fill" style="width:${pct}%;background:${color}"></div>
                        </div>
                        <span class="stat-val">${val}</span>
                    </div>`;
            });
        }

        let infoHtml = "";
        if (p.height) infoHtml += `<div class="info-item">Height: <span>${p.height}m</span></div>`;
        if (p.weight) infoHtml += `<div class="info-item">Weight: <span>${p.weight}kg</span></div>`;
        if (p.habitat) infoHtml += `<div class="info-item">Habitat: <span>${p.habitat}</span></div>`;
        if (p.shape) infoHtml += `<div class="info-item">Shape: <span>${p.shape}</span></div>`;
        if (p.color) infoHtml += `<div class="info-item">Color: <span>${p.color}</span></div>`;
        if (p.growth_rate) infoHtml += `<div class="info-item">Growth: <span>${p.growth_rate}</span></div>`;
        if (p.capture_rate) infoHtml += `<div class="info-item">Capture Rate: <span>${p.capture_rate}</span></div>`;
        if (p.base_happiness) infoHtml += `<div class="info-item">Happiness: <span>${p.base_happiness}</span></div>`;
        if (p.egg_groups && p.egg_groups.length) infoHtml += `<div class="info-item">Egg Groups: <span>${p.egg_groups.join(", ")}</span></div>`;
        if (p.evolves_from) infoHtml += `<div class="info-item">Evolves From: <span>${p.evolves_from}</span></div>`;

        let typeBadges = (p.type || []).map(t =>
            `<span class="type-badge type-${t.toLowerCase()}">${t}</span>`
        ).join("");

        let abilitiesHtml = "";
        if (p.abilities && p.abilities.length) {
            abilitiesHtml = `
                <div class="modal-section">
                    <div class="modal-section-title">Abilities</div>
                    <div class="modal-text">${p.abilities.join(", ")}</div>
                </div>`;
        }

        modalBody.innerHTML = `
            <div class="modal-header">
                <img class="modal-sprite" src="${spriteUrl}"
                     onerror="this.src='${fallbackSprite}'" alt="${p.title}" />
                <div class="modal-title-area">
                    <div class="modal-number">#${String(p.id).padStart(4, '0')}</div>
                    <div class="modal-name">${p.title}</div>
                    <div class="modal-genus">${p.genus || ''}</div>
                    <div class="type-badges" style="margin-top:6px">${typeBadges}</div>
                    <button class="modal-cry-btn" id="modalCryBtn" data-cry="${cryUrl}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                            <polygon points="5,3 19,12 5,21"/>
                        </svg>
                        PLAY CRY
                    </button>
                </div>
            </div>

            <div class="modal-section">
                <div class="modal-section-title">Pokedex Entry</div>
                <div class="modal-text">${p.text || ''}</div>
            </div>

            <div class="modal-section">
                <div class="modal-section-title">Base Stats</div>
                ${statsHtml}
            </div>

            ${abilitiesHtml}

            <div class="modal-section">
                <div class="modal-section-title">Details</div>
                <div class="modal-info-grid">${infoHtml}</div>
            </div>

            <div class="modal-section">
                <div class="modal-section-title">Source</div>
                <div class="modal-text" style="font-size:11px;word-break:break-all">
                    ${p.source || ''}
                </div>
            </div>
        `;

        // Modal cry button
        const modalCryBtn = document.getElementById("modalCryBtn");
        if (modalCryBtn) {
            modalCryBtn.addEventListener("click", () => {
                playCry(modalCryBtn.dataset.cry, modalCryBtn);
            });
        }

        modalOverlay.classList.add("visible");
        document.body.style.overflow = "hidden";
    }

    function closeModal() {
        modalOverlay.classList.remove("visible");
        document.body.style.overflow = "";
        if (currentAudio) {
            currentAudio.pause();
            currentAudio = null;
        }
    }

    modalClose.addEventListener("click", closeModal);
    modalOverlay.addEventListener("click", (e) => {
        if (e.target === modalOverlay) closeModal();
    });
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") closeModal();
    });

    // ========================================
    // FOCUS
    // ========================================
    if (!searchInput.value) searchInput.focus();
});
