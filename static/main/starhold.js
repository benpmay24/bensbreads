(() => {
  "use strict";

  // Wider board: West (left) vs East (right)
  const COLS = 10;
  const ROWS = 8;
  const ARMY_SIZE = 12;
  const STARS_NEEDED = 3;
  const STARS_TO_WIN = 2;

  const PLAYERS = {
    p1: {
      id: "p1",
      name: "West",
      deployCols: [0], // back line only
      starCols: [0, 1, 2, 3],
    },
    p2: {
      id: "p2",
      name: "East",
      deployCols: [9], // back line only
      starCols: [6, 7, 8, 9],
    },
  };

  const PIECES = {
    circle: {
      label: "Circle",
      blurb: "Move 1 · destroy walls · beats △ □",
      moves: 1,
      wallActions: 1,
      wallModes: ["destroy"],
      defeats: ["triangle", "square"],
    },
    triangle: {
      label: "Triangle",
      blurb: "Move 2 · only beats △",
      moves: 2,
      wallActions: 0,
      wallModes: [],
      defeats: ["triangle"],
    },
    square: {
      label: "Square",
      blurb: "Move 1 · build/destroy 2 walls",
      moves: 1,
      wallActions: 2,
      wallModes: ["build", "destroy"],
      defeats: [],
    },
    trapezoid: {
      label: "Trapezoid",
      blurb: "Move 1 · beats ○ △ □",
      moves: 1,
      wallActions: 0,
      wallModes: [],
      defeats: ["circle", "triangle", "square"],
    },
  };

  const DIRS = {
    n: [-1, 0],
    s: [1, 0],
    e: [0, 1],
    w: [0, -1],
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  let appEl = null;
  let config = { mode: "mp", difficulty: "easy", saveUrl: "", csrf: "" };
  let el = {};

  let state = null;
  let toastTimer = null;
  let busy = false;
  let cpuThinking = false;
  let resultSaved = false;
  let forfeitFrom = null;
  let cpuTimer = null;

  function cacheDom() {
    appEl = document.getElementById("starhold-app");
    config = {
      mode: appEl?.dataset.mode === "sp" ? "sp" : "mp",
      difficulty: appEl?.dataset.difficulty === "hard" ? "hard" : "easy",
      saveUrl: appEl?.dataset.saveUrl || "",
      csrf: appEl?.dataset.csrf || "",
    };
    el = {
      pass: $("#sh-pass-screen"),
      passTitle: $("#sh-pass-title"),
      passText: $("#sh-pass-text"),
      passOrb: $("#sh-pass-orb"),
      passReady: $("#sh-pass-ready"),
      setup: $("#sh-setup"),
      picker: $("#sh-piece-picker"),
      armyCount: $("#sh-army-count"),
      clearArmy: $("#sh-clear-army"),
      confirmArmy: $("#sh-confirm-army"),
      boardWrap: $("#sh-board-wrap"),
      board: $("#sh-board"),
      wallLayer: $("#sh-wall-layer"),
      actionBar: $("#sh-action-bar"),
      turnHint: $("#sh-turn-hint"),
      controlsP1: $("#sh-controls-p1"),
      controlsP2: $("#sh-controls-p2"),
      deployP1: $("#sh-deploy-p1"),
      deployP2: $("#sh-deploy-p2"),
      buildsP1: $("#sh-builds-p1"),
      buildsP2: $("#sh-builds-p2"),
      wallP1: $("#sh-wall-p1"),
      wallP2: $("#sh-wall-p2"),
      cancelP1: $("#sh-cancel-p1"),
      cancelP2: $("#sh-cancel-p2"),
      endP1: $("#sh-end-p1"),
      endP2: $("#sh-end-p2"),
      forfeitP1: $("#sh-forfeit-p1"),
      forfeitP2: $("#sh-forfeit-p2"),
      forfeitModal: $("#sh-forfeit-modal"),
      forfeitText: $("#sh-forfeit-text"),
      forfeitCancel: $("#sh-forfeit-cancel"),
      forfeitConfirm: $("#sh-forfeit-confirm"),
      deployModal: $("#sh-deploy-modal"),
      deployPicker: $("#sh-deploy-picker"),
      deployCancel: $("#sh-deploy-cancel"),
      deployClose: $("#sh-deploy-close"),
      statusText: $("#sh-status-text"),
      phasePill: $("#sh-phase-pill"),
      toast: $("#sh-toast"),
      howto: $("#sh-howto"),
      howtoBtn: $("#sh-howto-btn"),
      howtoClose: $("#sh-howto-close"),
      winner: $("#sh-winner"),
      winnerTitle: $("#sh-winner-title"),
      winnerText: $("#sh-winner-text"),
      playAgain: $("#sh-play-again"),
      panelP1: $("#sh-panel-p1"),
      panelP2: $("#sh-panel-p2"),
      p1Name: $("#sh-p1-name"),
      p2Name: $("#sh-p2-name"),
      p1Role: $("#sh-p1-role"),
      p2Role: $("#sh-p2-role"),
      p1Stars: $("#sh-p1-stars"),
      p2Stars: $("#sh-p2-stars"),
      p1Army: $("#sh-p1-army"),
      p2Army: $("#sh-p2-army"),
    };
  }

  function isSp() {
    return config.mode === "sp";
  }

  function isCpuPlayer(pid) {
    return isSp() && pid === "p2";
  }

  function isCpuInControl() {
    if (!isSp()) return false;
    if (state.phase === "army" || state.phase === "stars") return state.drafting === "p2";
    if (state.phase === "play") return state.current === "p2";
    return false;
  }

  function humanInputBlocked() {
    return busy || cpuThinking || isCpuInControl() || state.phase === "over";
  }

  function applyPlayerNames() {
    const badge1 = el.panelP1?.querySelector(".sh-player-badge");
    const badge2 = el.panelP2?.querySelector(".sh-player-badge");
    PLAYERS.p1.name = isSp() ? "West (You)" : "West";
    PLAYERS.p2.name = isSp()
      ? (config.difficulty === "hard" ? "East (CPU · Hard)" : "East (CPU · Easy)")
      : "East";
    badge1?.classList.toggle("is-you", isSp());
    badge1?.classList.remove("is-cpu");
    badge2?.classList.toggle("is-cpu", isSp());
    badge2?.classList.remove("is-you");
    if (el.p1Name) el.p1Name.textContent = PLAYERS.p1.name;
    if (el.p2Name) el.p2Name.textContent = PLAYERS.p2.name;
  }

  function weightedPick(items) {
    const total = items.reduce((s, it) => s + it.w, 0);
    let roll = Math.random() * total;
    for (const it of items) {
      roll -= it.w;
      if (roll <= 0) return it.v;
    }
    return items[items.length - 1].v;
  }

  function pickRandom(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  function freshState() {
    return {
      phase: "army",
      drafting: "p1",
      armies: { p1: [], p2: [] },
      stars: { p1: [], p2: [] },
      starsFound: { p1: 0, p2: 0 },
      pieces: [],
      walls: {},
      current: "p1",
      selectedReserve: null,
      selectedPieceId: null,
      movesLeft: 0,
      wallActionsLeft: 0,
      wallIntent: "build",
      acted: false,
      nextPieceId: 1,
      passPending: null,
    };
  }

  function key(r, c, edge) {
    return `${r},${c},${edge}`;
  }

  function normalizeWall(r, c, edge) {
    if (edge === "s") return { r: r + 1, c, edge: "n" };
    if (edge === "e") return { r, c: c + 1, edge: "w" };
    return { r, c, edge };
  }

  function wallAt(r, c, edge) {
    const n = normalizeWall(r, c, edge);
    if (n.r < 0 || n.r >= ROWS || n.c < 0 || n.c >= COLS) return null;
    if (n.edge === "n" && n.r === 0) return null;
    if (n.edge === "w" && n.c === 0) return null;
    return state.walls[key(n.r, n.c, n.edge)] || null;
  }

  function setWall(r, c, edge, owner) {
    const n = normalizeWall(r, c, edge);
    if (n.edge === "n" && n.r === 0) return false;
    if (n.edge === "w" && n.c === 0) return false;
    if (n.r < 0 || n.r >= ROWS || n.c < 0 || n.c >= COLS) return false;
    state.walls[key(n.r, n.c, n.edge)] = { owner };
    return true;
  }

  function removeWall(r, c, edge) {
    const n = normalizeWall(r, c, edge);
    const k = key(n.r, n.c, n.edge);
    if (!state.walls[k]) return false;
    delete state.walls[k];
    return true;
  }

  function inBounds(r, c) {
    return r >= 0 && r < ROWS && c >= 0 && c < COLS;
  }

  function pieceAt(r, c) {
    return state.pieces.find((p) => p.alive && p.r === r && p.c === c) || null;
  }

  function canDefeat(attackerType, defenderType) {
    if (attackerType === defenderType) return true;
    return PIECES[attackerType].defeats.includes(defenderType);
  }

  function blockedBetween(r0, c0, r1, c1) {
    const dr = r1 - r0;
    const dc = c1 - c0;
    if (Math.abs(dr) + Math.abs(dc) !== 1) return true;
    let edge;
    if (dr === -1) edge = "n";
    else if (dr === 1) edge = "s";
    else if (dc === 1) edge = "e";
    else edge = "w";
    return !!wallAt(r0, c0, edge);
  }

  function neighbors(r, c) {
    return Object.entries(DIRS)
      .map(([edge, [dr, dc]]) => ({ edge, r: r + dr, c: c + dc }))
      .filter(({ r: nr, c: nc }) => inBounds(nr, nc));
  }

  function toast(msg) {
    el.toast.textContent = msg;
    el.toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      el.toast.hidden = true;
    }, 2400);
  }

  function setStatus(phase, text) {
    el.phasePill.textContent = phase;
    el.statusText.textContent = text;
  }

  function showPass(playerId, title, text, onReady) {
    state.passPending = onReady;
    if (isSp()) {
      setTimeout(() => hidePass(), 350);
      return;
    }
    el.passOrb.className = `sh-pass-orb ${playerId}`;
    el.passTitle.textContent = title;
    el.passText.textContent = text;
    el.pass.hidden = false;
  }

  function hidePass() {
    el.pass.hidden = true;
    const cb = state.passPending;
    state.passPending = null;
    if (cb) cb();
    scheduleCpu();
  }

  function scheduleCpu() {
    if (!isSp() || state.phase === "over" || state.passPending) return;
    const needsCpu =
      (state.phase === "army" && state.drafting === "p2") ||
      (state.phase === "stars" && state.drafting === "p2") ||
      (state.phase === "play" && state.current === "p2" && !state.acted);
    if (!needsCpu) return;
    clearTimeout(cpuTimer);
    cpuTimer = setTimeout(() => {
      runCpuIfNeeded();
    }, 80);
  }

  function runCpuIfNeeded() {
    if (!isSp() || cpuThinking || busy || state.phase === "over") return;
    if (state.passPending) return;
    if (state.phase === "army" && state.drafting === "p2") {
      cpuDraftArmy();
    } else if (state.phase === "stars" && state.drafting === "p2") {
      cpuPlaceStars();
    } else if (state.phase === "play" && state.current === "p2" && !state.acted) {
      cpuPlayTurn();
    }
  }

  function clearSelection() {
    state.selectedReserve = null;
    state.selectedPieceId = null;
    state.movesLeft = 0;
    state.wallActionsLeft = 0;
  }

  function closeDeployModal() {
    el.deployModal.hidden = true;
  }

  function canEditWallOnCell(piece, r, c) {
    return piece.r === r && piece.c === c;
  }

  function reachableDestroyTargets(piece) {
    const seen = new Set();
    const targets = [];
    ["n", "s", "e", "w"].forEach((edge) => {
      if (!wallAt(piece.r, piece.c, edge)) return;
      const n = normalizeWall(piece.r, piece.c, edge);
      const k = key(n.r, n.c, n.edge);
      if (seen.has(k)) return;
      seen.add(k);
      targets.push({ r: piece.r, c: piece.c, edge });
    });
    return targets;
  }

  function possibleBuildEdges(piece) {
    const seen = new Set();
    const edges = [];
    ["n", "s", "e", "w"].forEach((edge) => {
      const n = normalizeWall(piece.r, piece.c, edge);
      if (n.edge === "n" && n.r === 0) return;
      if (n.edge === "w" && n.c === 0) return;
      if (n.r < 0 || n.r >= ROWS || n.c < 0 || n.c >= COLS) return;
      const k = key(n.r, n.c, n.edge);
      if (seen.has(k) || state.walls[k]) return;
      seen.add(k);
      edges.push(n);
    });
    return edges;
  }

  function availableWallModes(piece) {
    const meta = PIECES[piece.type];
    return meta.wallModes.filter((mode) => {
      if (mode === "build") return true;
      if (mode === "destroy") return reachableDestroyTargets(piece).length > 0;
      return false;
    });
  }

  /** Drop useless destroy-only actions; clamp wall intent to what's possible. */
  function syncWallActions(piece) {
    if (!piece || !piece.alive || state.wallActionsLeft <= 0) return;
    const modes = availableWallModes(piece);
    if (!modes.length) {
      state.wallActionsLeft = 0;
      return;
    }
    if (!modes.includes(state.wallIntent)) {
      state.wallIntent = modes[0];
    }
  }

  function maybeFinishCommand(piece) {
    if (!piece || !piece.alive) {
      if (state.acted) {
        renderAll();
        finishTurn();
      }
      return true;
    }
    syncWallActions(piece);
    if (state.movesLeft === 0 && state.wallActionsLeft === 0) {
      renderAll();
      finishTurn();
      return true;
    }
    return false;
  }

  function openDeployModal() {
    if (humanInputBlocked()) return;
    if (state.phase !== "play") return;
    if (state.acted) {
      toast("Already acted this turn — end turn.");
      return;
    }
    if (!state.armies[state.current].length) {
      toast("No pieces left in reserve.");
      return;
    }
    if (state.selectedPieceId != null) {
      toast("Cancel your piece selection first.");
      return;
    }
    clearSelection();
    renderDeployPicker();
    el.deployModal.hidden = false;
  }

  function shapeHtml(type) {
    return `<span class="sh-shape ${type}"></span>`;
  }

  function renderStarTracks() {
    for (const pid of ["p1", "p2"]) {
      const track = pid === "p1" ? el.p1Stars : el.p2Stars;
      const found = state.starsFound[pid];
      track.innerHTML = "";
      for (let i = 0; i < STARS_NEEDED; i++) {
        const slot = document.createElement("div");
        slot.className = "sh-star-slot" + (i < found ? " found" : "");
        slot.innerHTML = '<i class="fas fa-star"></i>';
        track.appendChild(slot);
      }
    }
  }

  function countTypes(list) {
    const counts = { circle: 0, triangle: 0, square: 0, trapezoid: 0 };
    list.forEach((t) => counts[t]++);
    return counts;
  }

  function getPrivateViewer() {
    if (isSp()) return "p1";
    if (state.phase === "army" || state.phase === "stars") return state.drafting;
    if (state.phase === "play") return state.current;
    return "p1";
  }

  function renderArmySummaries() {
    const viewer = getPrivateViewer();
    for (const pid of ["p1", "p2"]) {
      const box = pid === "p1" ? el.p1Army : el.p2Army;
      if (!box) continue;

      const alive = state.pieces.filter((p) => p.owner === pid && p.alive);
      const reserve = state.armies[pid] || [];

      // Fog of war: never reveal opponent piece composition (SP or hotseat)
      if (pid !== viewer && state.phase !== "over") {
        if (state.phase === "army" || state.phase === "stars") {
          const ready = reserve.length === ARMY_SIZE || (state.phase === "stars" && state.stars[pid]?.length === STARS_NEEDED);
          box.innerHTML = `<div class="sh-army-hidden">${ready ? "Army ready" : "Army hidden"}</div>`;
        } else {
          box.innerHTML = `<div class="sh-army-hidden">${alive.length} on board · ${reserve.length} in reserve</div>`;
        }
        continue;
      }

      const counts = (() => {
        const c = { circle: 0, triangle: 0, square: 0, trapezoid: 0 };
        if (state.phase === "army") return countTypes(reserve);
        alive.forEach((p) => c[p.type]++);
        reserve.forEach((t) => c[t]++);
        return c;
      })();
      box.innerHTML = Object.keys(PIECES)
        .map(
          (t) =>
            `<div class="sh-army-chip">${shapeHtml(t)} ${PIECES[t].label.slice(0, 3)} <span class="n">${counts[t]}</span></div>`
        )
        .join("");
    }
  }

  function updateRoles() {
    el.panelP1.classList.toggle("is-active", state.current === "p1" && state.phase === "play" && !cpuThinking);
    el.panelP2.classList.toggle(
      "is-active",
      state.current === "p2" && state.phase === "play" && (isCpuPlayer("p2") ? cpuThinking : true)
    );

    if (state.phase === "army") {
      el.p1Role.textContent = state.drafting === "p1" ? "Drafting army" : "Army ready";
      el.p2Role.textContent = state.drafting === "p2"
        ? isCpuPlayer("p2")
          ? "CPU drafting…"
          : "Drafting army"
        : state.armies.p2.length
          ? "Army ready"
          : "Waiting";
    } else if (state.phase === "stars") {
      el.p1Role.textContent = state.drafting === "p1" ? "Hiding stars" : "Stars set";
      el.p2Role.textContent = state.drafting === "p2"
        ? isCpuPlayer("p2")
          ? "CPU placing stars…"
          : "Hiding stars"
        : state.stars.p2.length === STARS_NEEDED
          ? "Stars set"
          : "Waiting";
    } else if (state.phase === "play") {
      el.p1Role.textContent = state.current === "p1" ? "Your turn" : "Waiting";
      if (isCpuPlayer("p2")) {
        el.p2Role.textContent = state.current === "p2" ? (cpuThinking ? "Thinking…" : "CPU turn") : "Waiting";
      } else {
        el.p2Role.textContent = state.current === "p2" ? "Your turn" : "Waiting";
      }
    } else {
      el.p1Role.textContent = "Finished";
      el.p2Role.textContent = "Finished";
    }
  }

  function renderPicker() {
    if (!el.picker) return;
    const draft = state.armies[state.drafting] || [];
    const counts = countTypes(draft);

    // Prefer updating the static HTML buttons so shapes never disappear
    const buttons = $$(".sh-pick", el.picker);
    if (buttons.length) {
      buttons.forEach((btn) => {
        btn.hidden = false;
        const type = btn.dataset.type;
        const countEl = btn.querySelector("[data-count]") || btn.querySelector(".count");
        if (countEl) countEl.textContent = String(counts[type] || 0);
      });
      // Remove any CPU overlay message if present
      $$(".sh-cpu-status", el.picker).forEach((n) => n.remove());
    } else {
      el.picker.innerHTML = Object.entries(PIECES)
        .map(
          ([type, meta]) => `
          <button type="button" class="sh-pick" data-type="${type}">
            ${shapeHtml(type)}
            <strong>${meta.label}</strong>
            <small>${meta.blurb}</small>
            <div class="count" data-count>${counts[type]}</div>
          </button>`
        )
        .join("");
    }

    if (el.armyCount) el.armyCount.textContent = `${draft.length} / ${ARMY_SIZE}`;
    if (el.confirmArmy) el.confirmArmy.disabled = draft.length !== ARMY_SIZE;
    if (el.clearArmy) el.clearArmy.disabled = false;
    if (el.setup) el.setup.hidden = false;
  }

  function showCpuDraftStatus() {
    if (!el.picker) return;
    $$(".sh-pick", el.picker).forEach((btn) => {
      btn.hidden = true;
    });
    let status = $(".sh-cpu-status", el.picker);
    if (!status) {
      status = document.createElement("p");
      status.className = "sh-cpu-status";
      el.picker.appendChild(status);
    }
    status.hidden = false;
    status.textContent = `East (CPU) is drafting… ${state.armies.p2.length} / ${ARMY_SIZE}`;
    if (el.armyCount) el.armyCount.textContent = `${state.armies.p2.length} / ${ARMY_SIZE}`;
    if (el.clearArmy) el.clearArmy.disabled = true;
    if (el.confirmArmy) el.confirmArmy.disabled = true;
  }

  function cellEl(r, c) {
    return el.board.querySelector(`[data-r="${r}"][data-c="${c}"]`);
  }

  function buildBoard() {
    if (!el.board) return;
    el.board.dataset.cols = String(COLS);
    el.board.innerHTML = "";
    for (let r = 0; r < ROWS; r++) {
      for (let c = 0; c < COLS; c++) {
        const cell = document.createElement("div");
        cell.className = "sh-cell";
        cell.dataset.r = r;
        cell.dataset.c = c;
        cell.setAttribute("role", "gridcell");
        if ((r + c) % 2 === 0) cell.classList.add("tile-a");
        else cell.classList.add("tile-b");
        if (PLAYERS.p1.deployCols.includes(c)) cell.classList.add("home-w");
        if (PLAYERS.p2.deployCols.includes(c)) cell.classList.add("home-e");
        if (c === 4 || c === 5) cell.classList.add("mid");
        el.board.appendChild(cell);
      }
    }
  }

  function clearCellClasses() {
    if (!el.board) return;
    $$(".sh-cell", el.board).forEach((cell) => {
      cell.classList.remove(
        "selectable",
        "valid-move",
        "valid-attack",
        "selected-piece",
        "wall-target",
        "is-edge-hot"
      );
    });
  }

  function renderBoardContent() {
    if (!el.board) return;
    $$(".sh-cell", el.board).forEach((cell) => {
      cell.querySelectorAll(".sh-piece, .sh-star-marker, .sh-star-found-burst").forEach((n) => n.remove());
    });

    const viewer = state.phase === "play" || state.phase === "over" ? state.current : state.drafting;

    if (state.phase === "stars" || state.phase === "play" || state.phase === "over") {
      const showFor = state.phase === "stars" ? state.drafting : viewer;
      (state.stars[showFor] || []).forEach(([sr, sc]) => {
        const cell = cellEl(sr, sc);
        if (!cell) return;
        const mark = document.createElement("div");
        mark.className = "sh-star-marker";
        mark.innerHTML = '<i class="fas fa-star"></i>';
        cell.appendChild(mark);
      });
    }

    state.pieces
      .filter((p) => p.alive)
      .forEach((p) => {
        const cell = cellEl(p.r, p.c);
        if (!cell) return;
        const node = document.createElement("div");
        node.className = `sh-piece ${p.owner}`;
        node.dataset.id = p.id;
        node.innerHTML = shapeHtml(p.type);
        cell.appendChild(node);
      });

    renderWalls();
  }

  function placeWallGraphic(rr, cc, edge, cellW, cellH, className, innerHtml = "") {
    const div = document.createElement("div");
    div.className = className;
    if (innerHtml) div.innerHTML = innerHtml;
    if (edge === "n") {
      div.style.left = `${cc * cellW + 4}px`;
      div.style.width = `${cellW - 8}px`;
      div.style.top = `${rr * cellH - 2}px`;
    } else if (edge === "w") {
      div.style.top = `${rr * cellH + 4}px`;
      div.style.height = `${cellH - 8}px`;
      div.style.left = `${cc * cellW - 2}px`;
    } else {
      return null;
    }
    el.wallLayer.appendChild(div);
    return div;
  }

  function renderWalls() {
    if (!el.wallLayer || !el.board) return;
    el.wallLayer.innerHTML = "";
    const rect = el.board.getBoundingClientRect();
    if (!rect.width) return;
    const cellW = rect.width / COLS;
    const cellH = rect.height / ROWS;

    Object.entries(state.walls).forEach(([k, wall]) => {
      const [r, c, edge] = k.split(",");
      const div = placeWallGraphic(+r, +c, edge, cellW, cellH, `sh-wall ${edge === "n" || edge === "s" ? "h" : "v"}`);
      if (div) {
        div.dataset.key = k;
        if (wall.owner === "p2") div.style.filter = "hue-rotate(-18deg)";
      }
    });

    renderWallHints(cellW, cellH);
  }

  function renderWallHints(cellW, cellH) {
    if (state.phase !== "play" || state.wallActionsLeft <= 0) return;
    const piece = state.pieces.find((p) => p.id === state.selectedPieceId && p.alive);
    if (!piece) return;

    const modes = availableWallModes(piece);
    // Build slots (amber) whenever building is available
    if (modes.includes("build")) {
      possibleBuildEdges(piece).forEach(({ r, c, edge }) => {
        placeWallGraphic(r, c, edge, cellW, cellH, `sh-wall-hint ${edge === "n" ? "h" : "v"}`);
      });
    }

    // Destroyable adjacent walls get a distinct break mark whenever destroy is available
    if (modes.includes("destroy")) {
      reachableDestroyTargets(piece).forEach(({ r, c, edge }) => {
        const n = normalizeWall(r, c, edge);
        placeWallGraphic(
          n.r,
          n.c,
          n.edge,
          cellW,
          cellH,
          `sh-wall-break ${n.edge === "n" ? "h" : "v"}`,
          '<span class="sh-wall-break-mark" aria-hidden="true">✕</span>'
        );
      });
    }
  }

  function renderDeployPicker() {
    const army = state.armies[state.current];
    if (!army.length) {
      el.deployPicker.innerHTML = '<span class="sh-deploy-empty">Reserve is empty.</span>';
      return;
    }
    el.deployPicker.innerHTML = army
      .map(
        (type, idx) => `
        <button type="button" class="sh-reserve-piece ${state.current} ${state.selectedReserve === idx ? "selected" : ""}" data-idx="${idx}" title="${PIECES[type].label}">
          ${shapeHtml(type)}
        </button>`
      )
      .join("");
    $$(".sh-reserve-piece", el.deployPicker).forEach((btn) => {
      btn.addEventListener("click", () => {
        state.selectedReserve = +btn.dataset.idx;
        state.selectedPieceId = null;
        closeDeployModal();
        renderAll();
        toast("Tap a highlighted back-line tile to deploy.");
      });
    });
  }

  function highlightDeployCells() {
    clearCellClasses();
    if (state.selectedReserve == null) return;
    const cols = PLAYERS[state.current].deployCols;
    for (let r = 0; r < ROWS; r++) {
      cols.forEach((c) => {
        if (!pieceAt(r, c)) cellEl(r, c)?.classList.add("selectable");
      });
    }
  }

  function highlightStarCells() {
    clearCellClasses();
    const cols = PLAYERS[state.drafting].starCols;
    const placed = state.stars[state.drafting];
    for (let r = 0; r < ROWS; r++) {
      cols.forEach((c) => {
        const taken = placed.some(([pr, pc]) => pr === r && pc === c);
        if (!taken) cellEl(r, c)?.classList.add("selectable");
      });
    }
    placed.forEach(([r, c]) => {
      cellEl(r, c)?.classList.add("selected-piece");
    });
  }

  function highlightCommandTargets() {
    clearCellClasses();
    if (state.selectedPieceId == null) {
      if (!state.acted) {
        state.pieces
          .filter((p) => p.alive && p.owner === state.current)
          .forEach((p) => cellEl(p.r, p.c)?.classList.add("selectable"));
      }
      return;
    }

    const piece = state.pieces.find((p) => p.id === state.selectedPieceId);
    if (!piece) return;
    syncWallActions(piece);
    cellEl(piece.r, piece.c)?.classList.add("selected-piece");

    if (state.movesLeft > 0) {
      neighbors(piece.r, piece.c).forEach(({ r, c }) => {
        if (blockedBetween(piece.r, piece.c, r, c)) return;
        const occ = pieceAt(r, c);
        if (!occ) {
          cellEl(r, c)?.classList.add("valid-move");
        } else if (occ.owner !== piece.owner) {
          cellEl(r, c)?.classList.add("valid-move", "valid-attack");
        }
      });
    }

    if (state.wallActionsLeft > 0) {
      const modes = availableWallModes(piece);
      if (modes.includes("build") || modes.includes("destroy")) {
        cellEl(piece.r, piece.c)?.classList.add("wall-target");
      }
      requestAnimationFrame(renderWalls);
    }
  }

  function updateDeployButtons() {
    const inPlay = state.phase === "play";
    const army = state.armies[state.current] || [];
    const canDeploy =
      inPlay &&
      !state.acted &&
      !cpuThinking &&
      army.length > 0 &&
      state.selectedPieceId == null &&
      state.selectedReserve == null;

    for (const pid of ["p1", "p2"]) {
      const controls = pid === "p1" ? el.controlsP1 : el.controlsP2;
      const deploy = pid === "p1" ? el.deployP1 : el.deployP2;
      if (!controls || !deploy) continue;
      const isHuman = !isCpuPlayer(pid);
      const isActive = inPlay && state.current === pid && isHuman && !cpuThinking;
      controls.hidden = !isActive;
      deploy.disabled = !canDeploy || state.current !== pid || !isHuman;
    }
  }

  function updateForfeitButtons() {
    const inPlay = state.phase === "play" && !cpuThinking;
    if (el.forfeitP1) {
      el.forfeitP1.hidden = !(inPlay && state.current === "p1");
    }
    if (el.forfeitP2) {
      el.forfeitP2.hidden = !(inPlay && state.current === "p2" && !isCpuPlayer("p2"));
    }
  }

  function updateTurnChrome() {
    updateDeployButtons();
    updateForfeitButtons();

    const piece = state.pieces.find((p) => p.id === state.selectedPieceId);
    if (piece) syncWallActions(piece);
    const modes = piece && state.wallActionsLeft > 0 ? availableWallModes(piece) : [];
    const canBuild = modes.includes("build");
    const active = state.current;
    const buildsEl = active === "p1" ? el.buildsP1 : el.buildsP2;
    const wallBtn = active === "p1" ? el.wallP1 : el.wallP2;
    const cancelBtn = active === "p1" ? el.cancelP1 : el.cancelP2;
    const endBtn = active === "p1" ? el.endP1 : el.endP2;
    const idleBuilds = active === "p1" ? el.buildsP2 : el.buildsP1;
    const idleWall = active === "p1" ? el.wallP2 : el.wallP1;
    const idleCancel = active === "p1" ? el.cancelP2 : el.cancelP1;
    const idleEnd = active === "p1" ? el.endP2 : el.endP1;

    idleBuilds.hidden = true;
    idleWall.hidden = true;
    idleCancel.hidden = true;
    idleEnd.disabled = true;

    if (isCpuPlayer(active) || cpuThinking) {
      buildsEl.hidden = true;
      wallBtn.hidden = true;
      cancelBtn.hidden = true;
      endBtn.disabled = true;
      return;
    }

    if (canBuild && state.wallActionsLeft > 0) {
      buildsEl.hidden = false;
      buildsEl.textContent = `Builds left: ${state.wallActionsLeft}`;
    } else if (modes.includes("destroy") && state.wallActionsLeft > 0) {
      buildsEl.hidden = false;
      buildsEl.textContent = `Destroys left: ${state.wallActionsLeft}`;
    } else {
      buildsEl.hidden = true;
    }

    // Square with both options: show combined actions when destroy targets exist too
    if (canBuild && modes.includes("destroy") && state.wallActionsLeft > 0) {
      buildsEl.hidden = false;
      buildsEl.textContent = `Wall actions left: ${state.wallActionsLeft}`;
    }

    // Click target decides build vs destroy; no mode toggle needed
    wallBtn.hidden = true;

    const cancellable = state.selectedReserve != null || (state.selectedPieceId != null && !state.acted);
    cancelBtn.hidden = !cancellable;
    endBtn.disabled = !state.acted;
  }

  function renderAll() {
    updateRoles();
    renderStarTracks();
    renderArmySummaries();
    renderBoardContent();
    updateDeployButtons();

    if (state.phase === "army") {
      el.setup.hidden = false;
      el.boardWrap.hidden = true;
      el.actionBar.hidden = true;
      if (el.controlsP1) el.controlsP1.hidden = true;
      if (el.controlsP2) el.controlsP2.hidden = true;
      if (el.deployModal) el.deployModal.hidden = true;
      if (isCpuPlayer(state.drafting)) {
        showCpuDraftStatus();
        if (el.setup) el.setup.hidden = false;
        setStatus("Army draft", "East (CPU) is drafting…");
      } else {
        if (el.setup) el.setup.hidden = false;
        renderPicker();
        setStatus("Army draft", `${PLAYERS[state.drafting].name}: pick any 12 pieces`);
      }
    } else if (state.phase === "stars") {
      el.setup.hidden = true;
      el.boardWrap.hidden = false;
      el.actionBar.hidden = true;
      if (el.controlsP1) el.controlsP1.hidden = true;
      if (el.controlsP2) el.controlsP2.hidden = true;
      if (isCpuPlayer(state.drafting)) {
        clearCellClasses();
        const left = STARS_NEEDED - state.stars[state.drafting].length;
        setStatus("Hide stars", `East (CPU) is placing stars… (${left} left)`);
      } else {
        highlightStarCells();
        const left = STARS_NEEDED - state.stars[state.drafting].length;
        setStatus(
          "Hide stars",
          `${PLAYERS[state.drafting].name}: place ${left} more star${left === 1 ? "" : "s"} on your side`
        );
      }
    } else if (state.phase === "play") {
      el.setup.hidden = true;
      el.boardWrap.hidden = false;
      el.actionBar.hidden = false;
      updateTurnChrome();

      if (isCpuPlayer(state.current) || cpuThinking) {
        clearCellClasses();
        el.turnHint.textContent = "CPU is playing…";
        setStatus("Battle", `${PLAYERS.p2.name} is thinking…`);
      } else if (state.selectedReserve != null) {
        highlightDeployCells();
        el.turnHint.textContent = "Tap a highlighted back-line tile to deploy, or Cancel.";
        setStatus("Battle", `${PLAYERS[state.current].name}: choose where to deploy`);
      } else {
        highlightCommandTargets();
        const piece = state.pieces.find((p) => p.id === state.selectedPieceId);
        if (!piece) {
          el.turnHint.textContent = "Select one of your pieces on the board, or tap Deploy.";
          setStatus("Battle", `${PLAYERS[state.current].name}: select a piece or deploy`);
        } else {
          el.turnHint.textContent = state.acted
            ? "Finish remaining actions, then End turn — or End turn now."
            : "Move to a marked tile, use wall actions, or Cancel.";
          setStatus(
            "Battle",
            `${PIECES[piece.type].label}: ${state.movesLeft} move${state.movesLeft === 1 ? "" : "s"} left` +
              (availableWallModes(piece).includes("build") && state.wallActionsLeft
                ? ` · ${state.wallActionsLeft} build${state.wallActionsLeft === 1 ? "" : "s"} left`
                : state.wallActionsLeft
                  ? ` · ${state.wallActionsLeft} wall action${state.wallActionsLeft === 1 ? "" : "s"}`
                  : "")
          );
        }
      }
    } else {
      el.actionBar.hidden = true;
      clearCellClasses();
      updateForfeitButtons();
    }

    requestAnimationFrame(renderWalls);
    scheduleCpu();
  }

  function startArmyDraft(playerId) {
    state.phase = "army";
    state.drafting = playerId;
    renderAll();

    if (isCpuPlayer(playerId)) {
      // SP: CPU drafts immediately — never hand the picker to the human
      toast("East (CPU) is drafting its army…");
      clearTimeout(cpuTimer);
      cpuTimer = setTimeout(() => {
        if (state.phase === "army" && state.drafting === "p2") cpuDraftArmy();
      }, 120);
      return;
    }

    requestAnimationFrame(() => {
      if (state.phase === "army" && state.drafting === playerId && !isCpuPlayer(playerId)) {
        if (el.setup) el.setup.hidden = false;
        renderPicker();
      }
    });
  }

  function confirmArmy() {
    if ((state.armies[state.drafting] || []).length !== ARMY_SIZE) return;

    if (state.drafting === "p1") {
      if (isSp()) {
        // Human done → CPU drafts East automatically (no pass / no human picker)
        startArmyDraft("p2");
        return;
      }
      showPass("p2", "Pass to East", "West's army is locked in. Hand the device to East — don't peek.", () => {
        startArmyDraft("p2");
      });
      return;
    }

    // p2 finished drafting
    if (isSp()) {
      // CPU finished → human places stars
      startStarPhase("p1");
      return;
    }
    showPass("p1", "Pass to West", "Armies are ready. West hides stars first — no peeking.", () => {
      startStarPhase("p1");
    });
  }

  function startStarPhase(playerId) {
    state.phase = "stars";
    state.drafting = playerId;
    state.stars[playerId] = [];
    renderAll();
  }

  function placeStar(r, c) {
    const player = PLAYERS[state.drafting];
    if (!player.starCols.includes(c)) {
      toast("Stars must be on your side of the board.");
      return;
    }
    const list = state.stars[state.drafting];
    const idx = list.findIndex(([pr, pc]) => pr === r && pc === c);
    if (idx >= 0) {
      list.splice(idx, 1);
      renderAll();
      return;
    }
    if (list.length >= STARS_NEEDED) {
      toast("Already placed 3 stars — tap one to move it.");
      return;
    }
    list.push([r, c]);
    if (list.length === STARS_NEEDED) {
      if (state.drafting === "p1") {
        const nextLabel = isCpuPlayer("p2") ? "CPU places stars" : "Pass to East";
        const nextMsg = isCpuPlayer("p2")
          ? "Your stars are set. East (CPU) is hiding its stars…"
          : "West's stars are hidden. Hand the device to East.";
        showPass("p2", nextLabel, nextMsg, () => {
          startStarPhase("p2");
        });
      } else {
        showPass("p1", isSp() ? "Battle begins" : "Pass to West", "Stars are set. West opens the battle.", () => {
          beginPlay();
        });
      }
      return;
    }
    renderAll();
  }

  function beginPlay() {
    state.phase = "play";
    state.current = "p1";
    clearSelection();
    state.acted = false;
    renderAll();
    toast("West begins — select a piece or deploy.");
  }

  function finishTurn() {
    if (!state.acted) return;
    const next = state.current === "p1" ? "p2" : "p1";
    showPass(next, `Pass to ${PLAYERS[next].name}`, "Keep enemy stars secret. Ready when you are.", () => {
      state.current = next;
      clearSelection();
      state.acted = false;
      renderAll();
    });
  }

  function checkVictory() {
    for (const pid of ["p1", "p2"]) {
      if (state.starsFound[pid] >= STARS_TO_WIN) {
        endGame(pid, `${PLAYERS[pid].name} uncovered ${state.starsFound[pid]} enemy stars.`);
        return true;
      }
      const foe = pid === "p1" ? "p2" : "p1";
      const foeAlive =
        state.pieces.some((p) => p.owner === foe && p.alive) || state.armies[foe].length > 0;
      if (!foeAlive) {
        endGame(pid, `${PLAYERS[pid].name} eliminated every opposing piece.`);
        return true;
      }
    }
    return false;
  }

  function endGame(winnerId, reason) {
    state.phase = "over";
    cpuThinking = false;
    clearTimeout(cpuTimer);
    if (el.forfeitModal) el.forfeitModal.hidden = true;
    forfeitFrom = null;
    renderAll();
    el.winnerTitle.textContent = `${PLAYERS[winnerId].name} wins`;
    el.winnerText.textContent = reason;
    el.winner.hidden = false;

    if (isSp() && config.saveUrl && !resultSaved) {
      resultSaved = true;
      const result = winnerId === "p1" ? "win" : "loss";
      fetch(config.saveUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": config.csrf,
        },
        body: JSON.stringify({ result, difficulty: config.difficulty }),
      }).catch(() => {});
    }
  }

  function discoverStar(r, c, moverId) {
    const foe = moverId === "p1" ? "p2" : "p1";
    const idx = state.stars[foe].findIndex(([sr, sc]) => sr === r && sc === c);
    if (idx < 0) return false;
    state.stars[foe].splice(idx, 1);
    state.starsFound[moverId] += 1;
    const cell = cellEl(r, c);
    if (cell) {
      const burst = document.createElement("div");
      burst.className = "sh-star-found-burst";
      burst.innerHTML = '<i class="fas fa-star"></i>';
      cell.appendChild(burst);
      setTimeout(() => burst.remove(), 900);
    }
    toast(`Star found! (${state.starsFound[moverId]}/${STARS_TO_WIN} to win)`);
    return true;
  }

  async function animateMove(piece, toR, toC) {
    const node = el.board.querySelector(`.sh-piece[data-id="${piece.id}"]`);
    if (node) node.classList.add("moving");
    await wait(180);
    piece.r = toR;
    piece.c = toC;
    renderBoardContent();
    const moved = el.board.querySelector(`.sh-piece[data-id="${piece.id}"]`);
    if (moved) {
      moved.classList.add("moving");
      await wait(200);
      moved.classList.remove("moving");
    }
  }

  function wait(ms) {
    return new Promise((res) => setTimeout(res, ms));
  }

  function pickCpuArmyType() {
    if (config.difficulty === "hard") {
      return weightedPick([
        { v: "trapezoid", w: 3.2 },
        { v: "circle", w: 2.8 },
        { v: "square", w: 2.2 },
        { v: "triangle", w: 1.0 },
      ]);
    }
    return weightedPick([
      { v: "circle", w: 1.1 },
      { v: "triangle", w: 1.0 },
      { v: "square", w: 1.0 },
      { v: "trapezoid", w: 0.95 },
    ]);
  }

  async function cpuDraftArmy() {
    if (!isSp() || cpuThinking || state.phase !== "army" || state.drafting !== "p2") return;
    cpuThinking = true;
    showCpuDraftStatus();
    setStatus("Army draft", "East (CPU) is drafting…");
    toast("East (CPU) is assembling an army…");
    await wait(400);
    state.armies.p2 = [];
    for (let i = 0; i < ARMY_SIZE; i++) {
      state.armies.p2.push(pickCpuArmyType());
      if (i % 3 === 2) {
        showCpuDraftStatus();
        renderArmySummaries();
        await wait(80);
      }
    }
    showCpuDraftStatus();
    renderArmySummaries();
    updateRoles();
    await wait(250);
    cpuThinking = false;
    // Lock in CPU army and advance without exposing the picker
    confirmArmy();
  }

  function pickCpuStarCells() {
    const cols = PLAYERS.p2.starCols.slice();
    const preferredCols = config.difficulty === "hard" ? [8, 9, 8, 9, 7] : cols;
    const used = new Set();
    const placed = [];
    const rows = [...Array(ROWS).keys()];

    while (placed.length < STARS_NEEDED) {
      const colPool = preferredCols.filter((c) => cols.includes(c));
      const c = pickRandom(colPool.length ? colPool : cols);
      let rowPool = rows.filter((r) => !used.has(`${r},${c}`));
      if (config.difficulty === "hard" && placed.length) {
        const usedRows = new Set(placed.map(([r]) => r));
        const diverse = rowPool.filter((r) => !usedRows.has(r));
        if (diverse.length) rowPool = diverse;
      }
      if (!rowPool.length) {
        // fallback any free cell in star cols
        for (const cc of cols) {
          for (const rr of rows) {
            if (!used.has(`${rr},${cc}`)) rowPool.push(rr);
          }
        }
        if (!rowPool.length) break;
        const r = pickRandom(rowPool);
        // find matching free (r,c) — simplified: scan
        let found = false;
        for (const cc of cols) {
          if (!used.has(`${r},${cc}`)) {
            used.add(`${r},${cc}`);
            placed.push([r, cc]);
            found = true;
            break;
          }
        }
        if (!found) break;
        continue;
      }
      const r = pickRandom(rowPool);
      used.add(`${r},${c}`);
      placed.push([r, c]);
    }
    return placed;
  }

  async function cpuPlaceStars() {
    if (cpuThinking || state.phase !== "stars" || state.drafting !== "p2") return;
    cpuThinking = true;
    state.stars.p2 = [];
    renderAll();
    await wait(280);
    const cells = pickCpuStarCells();
    for (const [r, c] of cells) {
      state.stars.p2.push([r, c]);
      renderBoardContent();
      renderArmySummaries();
      updateRoles();
      await wait(160);
    }
    cpuThinking = false;
    showPass("p1", "Pass to West", "Stars are set. West opens the battle.", () => {
      beginPlay();
    });
  }

  function scoreDeployCell(r, c) {
    // Prefer open rows and toward midboard visibility
    let score = 1;
    if (config.difficulty === "hard") {
      score += Math.abs(r - 3.5) < 2 ? 1.5 : 0.4;
      score += c === 9 ? 0.5 : 0;
      // Prefer not stacking on same row as ally
      const allies = state.pieces.filter((p) => p.alive && p.owner === "p2" && p.r === r);
      score -= allies.length * 0.8;
    }
    return score;
  }

  function scoreMove(piece, r, c, occ) {
    let score = 1;
    const hard = config.difficulty === "hard";

    if (occ) {
      if (canDefeat(piece.type, occ.type)) {
        score += hard ? 12 : 6;
        if (occ.type === "trapezoid" || occ.type === "circle") score += 3;
      } else {
        // suicidal
        score -= hard ? 20 : 8;
      }
    } else {
      score += 1;
      // Toward enemy half / star columns
      if (c < piece.c) score += hard ? 2.5 : 0.8;
      if (c <= 4) score += hard ? 2 : 0.5;
      if (c <= 3) score += hard ? 1.5 : 0.3;
      // Toward enemy pieces
      const foes = state.pieces.filter((p) => p.alive && p.owner === "p1");
      if (foes.length) {
        const before = Math.min(...foes.map((f) => Math.abs(f.r - piece.r) + Math.abs(f.c - piece.c)));
        const after = Math.min(...foes.map((f) => Math.abs(f.r - r) + Math.abs(f.c - c)));
        score += (before - after) * (hard ? 1.8 : 0.6);
      }
    }
    return score;
  }

  function scoreWallAction(piece, action) {
    let score = 1;
    const hard = config.difficulty === "hard";
    if (action.mode === "destroy") {
      score += hard ? 4 : 1.5;
      // Prefer destroying walls that block westward progress
      if (action.edge === "w" || action.edge === "n" || action.edge === "s") score += hard ? 1.5 : 0.4;
    } else if (action.mode === "build") {
      score += hard ? 2.2 : 1;
      // Build east-side walls? Prefer walls that hinder human approaching from west
      if (action.edge === "w") score += hard ? 2.5 : 0.6;
      // Prefer walls near mid / facing human
      if (piece.c <= 7) score += hard ? 1.2 : 0.3;
    }
    return score;
  }

  function listCpuDeployOptions() {
    const army = state.armies.p2;
    if (!army.length) return [];
    const options = [];
    const cols = PLAYERS.p2.deployCols;
    for (let idx = 0; idx < army.length; idx++) {
      const type = army[idx];
      for (let r = 0; r < ROWS; r++) {
        for (const c of cols) {
          if (pieceAt(r, c)) continue;
          let score = scoreDeployCell(r, c);
          if (config.difficulty === "hard") {
            if (type === "trapezoid" || type === "circle") score += 3;
            else if (type === "square") score += 1.5;
            else score += 0.4;
          } else {
            score += 1;
          }
          options.push({ kind: "deploy", idx, type, r, c, score });
        }
      }
    }
    return options;
  }

  function listCpuCommandStarters() {
    const options = [];
    state.pieces
      .filter((p) => p.alive && p.owner === "p2")
      .forEach((piece) => {
        const moves = [];
        neighbors(piece.r, piece.c).forEach(({ r, c }) => {
          if (blockedBetween(piece.r, piece.c, r, c)) return;
          const occ = pieceAt(r, c);
          if (occ && occ.owner === piece.owner) return;
          const score = scoreMove(piece, r, c, occ);
          moves.push({ r, c, occ, score });
        });
        const walls = [];
        const meta = PIECES[piece.type];
        if (meta.wallActions > 0) {
          if (meta.wallModes.includes("destroy")) {
            reachableDestroyTargets(piece).forEach(({ r, c, edge }) => {
              walls.push({ mode: "destroy", r, c, edge, score: scoreWallAction(piece, { mode: "destroy", edge }) });
            });
          }
          if (meta.wallModes.includes("build")) {
            ["n", "s", "e", "w"].forEach((edge) => {
              const n = normalizeWall(piece.r, piece.c, edge);
              if (n.edge === "n" && n.r === 0) return;
              if (n.edge === "w" && n.c === 0) return;
              if (n.r < 0 || n.r >= ROWS || n.c < 0 || n.c >= COLS) return;
              if (state.walls[key(n.r, n.c, n.edge)]) return;
              walls.push({
                mode: "build",
                r: piece.r,
                c: piece.c,
                edge,
                score: scoreWallAction(piece, { mode: "build", edge }),
              });
            });
          }
        }
        if (!moves.length && !walls.length) return;
        const bestMove = moves.length ? Math.max(...moves.map((m) => m.score)) : -Infinity;
        const bestWall = walls.length ? Math.max(...walls.map((w) => w.score)) : -Infinity;
        options.push({
          kind: "command",
          pieceId: piece.id,
          type: piece.type,
          moves,
          walls,
          score: Math.max(bestMove, bestWall, 0.5),
        });
      });
    return options;
  }

  function chooseCpuTurnPlan() {
    const deployOpts = listCpuDeployOptions();
    const commandOpts = listCpuCommandStarters();
    const hard = config.difficulty === "hard";
    const onBoard = state.pieces.filter((p) => p.alive && p.owner === "p2").length;

    if (config.difficulty === "easy") {
      // Slight bias to deploy early; rarely pick suicidal attacks
      const filteredCommands = commandOpts
        .map((opt) => {
          const safeMoves = opt.moves.filter((m) => {
            if (!m.occ) return true;
            if (canDefeat(opt.type, m.occ.type)) return true;
            return Math.random() < 0.12; // rarely suicidal
          });
          return { ...opt, moves: safeMoves };
        })
        .filter((opt) => opt.moves.length || opt.walls.length);

      const pool = [];
      deployOpts.forEach((o) => {
        const earlyBias = onBoard < 4 ? 1.6 : 0.7;
        pool.push({ v: o, w: Math.max(0.2, earlyBias) });
      });
      filteredCommands.forEach((o) => {
        pool.push({ v: o, w: 1 });
      });
      if (!pool.length) return null;
      return weightedPick(pool);
    }

    // Hard: score-based pick among near-best
    const all = [...deployOpts, ...commandOpts];
    if (!all.length) return null;
    all.sort((a, b) => b.score - a.score);
    const best = all[0].score;
    const contenders = all.filter((o) => o.score >= best - (hard ? 1.5 : 3));
    return pickRandom(contenders);
  }

  function pickBestScored(list, hard) {
    if (!list.length) return null;
    list.sort((a, b) => b.score - a.score);
    const best = list[0].score;
    const slack = hard ? 0.8 : 2.5;
    const contenders = list.filter((o) => o.score >= best - slack);
    return pickRandom(contenders);
  }

  async function cpuExecuteDeploy(plan) {
    const type = state.armies.p2[plan.idx];
    if (type == null) return;
    if (pieceAt(plan.r, plan.c)) return;
    state.armies.p2.splice(plan.idx, 1);
    state.pieces.push({
      id: state.nextPieceId++,
      owner: "p2",
      type,
      r: plan.r,
      c: plan.c,
      alive: true,
    });
    state.acted = true;
    discoverStar(plan.r, plan.c, "p2");
    renderAll();
    await wait(200);
    if (checkVictory()) return;
    finishTurn();
  }

  async function cpuExecuteCommand(plan) {
    const piece = state.pieces.find((p) => p.id === plan.pieceId && p.alive);
    if (!piece) return;

    state.selectedReserve = null;
    state.selectedPieceId = piece.id;
    state.movesLeft = PIECES[piece.type].moves;
    state.wallActionsLeft = PIECES[piece.type].wallActions;
    state.wallIntent = PIECES[piece.type].wallModes[0] || "destroy";
    syncWallActions(piece);
    renderAll();
    await wait(220);

    const hard = config.difficulty === "hard";
    let guard = 12;
    while (guard-- > 0 && state.phase === "play" && state.current === "p2" && piece.alive) {
      if (state.movesLeft <= 0 && state.wallActionsLeft <= 0) break;

      if (state.movesLeft > 0) {
        const moves = [];
        neighbors(piece.r, piece.c).forEach(({ r, c }) => {
          if (blockedBetween(piece.r, piece.c, r, c)) return;
          const occ = pieceAt(r, c);
          if (occ && occ.owner === piece.owner) return;
          let score = scoreMove(piece, r, c, occ);
          if (!hard && occ && !canDefeat(piece.type, occ.type) && Math.random() >= 0.12) {
            return;
          }
          if (hard && occ && !canDefeat(piece.type, occ.type)) {
            score -= 25;
          }
          moves.push({ r, c, score });
        });
        const choice = pickBestScored(moves, hard);
        if (choice && (hard ? choice.score > -10 : true)) {
          await tryMovePiece(piece, choice.r, choice.c);
          await wait(140);
          if (state.passPending || state.phase === "over" || state.current !== "p2") return;
          if (!piece.alive) return;
          continue;
        }
        // No useful move — drop remaining moves if walls remain, else bail
        if (state.wallActionsLeft <= 0) {
          state.movesLeft = 0;
          break;
        }
        state.movesLeft = 0;
      }

      if (state.wallActionsLeft > 0) {
        syncWallActions(piece);
        const modes = availableWallModes(piece);
        const walls = [];
        if (modes.includes("destroy")) {
          reachableDestroyTargets(piece).forEach(({ r, c, edge }) => {
            walls.push({
              mode: "destroy",
              r,
              c,
              edge,
              score: scoreWallAction(piece, { mode: "destroy", edge }),
            });
          });
        }
        if (modes.includes("build")) {
          ["n", "s", "e", "w"].forEach((edge) => {
            const n = normalizeWall(piece.r, piece.c, edge);
            if (n.edge === "n" && n.r === 0) return;
            if (n.edge === "w" && n.c === 0) return;
            if (n.r < 0 || n.r >= ROWS || n.c < 0 || n.c >= COLS) return;
            if (state.walls[key(n.r, n.c, n.edge)]) return;
            walls.push({
              mode: "build",
              r: piece.r,
              c: piece.c,
              edge,
              score: scoreWallAction(piece, { mode: "build", edge }),
            });
          });
        }
        const choice = pickBestScored(walls, hard);
        if (!choice) {
          state.wallActionsLeft = 0;
          break;
        }
        handleWallAction(piece, choice.r, choice.c, choice.edge);
        await wait(140);
        if (state.passPending || state.phase === "over" || state.current !== "p2") return;
        continue;
      }
      break;
    }

    if (state.passPending || state.phase === "over") return;

    if (state.phase === "play" && state.current === "p2" && state.acted) {
      finishTurn();
    } else if (state.phase === "play" && state.current === "p2" && !state.acted) {
      // Selected but couldn't act — clear and try deploy fallback once
      clearSelection();
      const deployOpts = listCpuDeployOptions();
      if (deployOpts.length) {
        const fallback = pickBestScored(deployOpts, hard) || pickRandom(deployOpts);
        await cpuExecuteDeploy(fallback);
      }
    }
  }

  async function cpuPlayTurn() {
    if (!isSp() || cpuThinking || busy || state.phase !== "play" || state.current !== "p2") return;
    cpuThinking = true;
    renderAll();
    await wait(config.difficulty === "hard" ? 450 : 320);
    try {
      if (state.phase !== "play" || state.current !== "p2" || state.phase === "over") return;
      const plan = chooseCpuTurnPlan();
      if (!plan) {
        // Nothing legal — skip turn only if somehow stuck without action (shouldn't end incorrectly)
        toast("CPU passes — no legal actions.");
        return;
      }
      if (plan.kind === "deploy") {
        await cpuExecuteDeploy(plan);
      } else {
        await cpuExecuteCommand(plan);
      }
    } finally {
      cpuThinking = false;
    }
  }

  async function resolveCombat(attacker, defender) {
    if (canDefeat(attacker.type, defender.type)) {
      defender.alive = false;
      const node = el.board.querySelector(`.sh-piece[data-id="${defender.id}"]`);
      if (node) {
        node.classList.add("dying");
        await wait(420);
      }
      toast(`${PIECES[attacker.type].label} defeats ${PIECES[defender.type].label}`);
      return "win";
    }
    attacker.alive = false;
    const node = el.board.querySelector(`.sh-piece[data-id="${attacker.id}"]`);
    if (node) {
      node.classList.add("dying");
      await wait(420);
    }
    toast(`${PIECES[attacker.type].label} fails against ${PIECES[defender.type].label}`);
    return "lose";
  }

  async function tryMovePiece(piece, r, c) {
    if (state.movesLeft <= 0) return;
    if (!inBounds(r, c)) return;
    if (Math.abs(piece.r - r) + Math.abs(piece.c - c) !== 1) return;
    if (blockedBetween(piece.r, piece.c, r, c)) {
      toast("A wall blocks that path.");
      return;
    }
    const occ = pieceAt(r, c);
    if (occ && occ.owner === piece.owner) return;

    busy = true;
    if (occ) {
      const result = await resolveCombat(piece, occ);
      if (result === "win") {
        await animateMove(piece, r, c);
        discoverStar(r, c, piece.owner);
      }
    } else {
      await animateMove(piece, r, c);
      discoverStar(r, c, piece.owner);
    }

    state.movesLeft -= 1;
    state.acted = true;

    if (!piece.alive) {
      clearSelection();
    }

    busy = false;
    if (checkVictory()) return;
    if (maybeFinishCommand(piece.alive ? piece : null)) return;
    renderAll();
  }

  function edgeFromClick(cell, clientX, clientY) {
    const rect = cell.getBoundingClientRect();
    const x = (clientX - rect.left) / rect.width;
    const y = (clientY - rect.top) / rect.height;
    const dist = { n: y, s: 1 - y, w: x, e: 1 - x };
    return Object.entries(dist).sort((a, b) => a[1] - b[1])[0][0];
  }

  function handleWallAction(piece, r, c, edge) {
    if (state.wallActionsLeft <= 0) return;
    const modes = availableWallModes(piece);
    if (!modes.length) {
      state.wallActionsLeft = 0;
      maybeFinishCommand(piece);
      return;
    }
    if (!canEditWallOnCell(piece, r, c)) {
      toast("Walls must be on an edge of your piece.");
      return;
    }

    const existing = wallAt(r, c, edge);

    // Prefer destroy when tapping an existing adjacent wall (uses one wall action)
    if (existing && modes.includes("destroy")) {
      removeWall(r, c, edge);
      state.wallActionsLeft -= 1;
      state.acted = true;
      state.wallIntent = modes.includes("build") && state.wallActionsLeft > 0 ? state.wallIntent : "destroy";
      toast(`Wall destroyed (${state.wallActionsLeft} wall action${state.wallActionsLeft === 1 ? "" : "s"} left)`);
      if (maybeFinishCommand(piece)) return;
      renderAll();
      return;
    }

    if (!existing && modes.includes("build")) {
      if (!setWall(r, c, edge, piece.owner)) {
        toast("Can't place a wall on the outer rim.");
        return;
      }
      state.wallActionsLeft -= 1;
      state.acted = true;
      state.wallIntent = "build";
      toast(`Wall built (${state.wallActionsLeft} wall action${state.wallActionsLeft === 1 ? "" : "s"} left)`);
      if (maybeFinishCommand(piece)) return;
      renderAll();
      return;
    }

    if (existing) {
      toast("This piece can't destroy walls.");
    } else {
      toast("Click a glowing edge to build, or a marked wall to destroy.");
    }
  }

  async function onCellClick(r, c, evt) {
    if (humanInputBlocked()) return;

    if (state.phase === "stars") {
      placeStar(r, c);
      return;
    }

    if (state.phase !== "play") return;

    // Deploy placement
    if (state.selectedReserve != null) {
      if (state.acted) {
        toast("Already acted this turn — end turn.");
        return;
      }
      if (!PLAYERS[state.current].deployCols.includes(c)) {
        toast("Deploy only on your back line.");
        return;
      }
      if (pieceAt(r, c)) {
        toast("That tile is occupied.");
        return;
      }
      const type = state.armies[state.current][state.selectedReserve];
      state.armies[state.current].splice(state.selectedReserve, 1);
      state.pieces.push({
        id: state.nextPieceId++,
        owner: state.current,
        type,
        r,
        c,
        alive: true,
      });
      state.selectedReserve = null;
      state.acted = true;
      discoverStar(r, c, state.current);
      renderAll();
      if (checkVictory()) return;
      finishTurn();
      return;
    }

    if (state.acted && state.selectedPieceId == null) {
      toast("Turn spent — end turn.");
      return;
    }

    const piece = state.pieces.find((p) => p.id === state.selectedPieceId);

    if (!piece) {
      const target = pieceAt(r, c);
      if (target && target.owner === state.current) {
        if (state.acted) {
          toast("You already acted this turn.");
          return;
        }
        state.selectedReserve = null;
        state.selectedPieceId = target.id;
        state.movesLeft = PIECES[target.type].moves;
        state.wallActionsLeft = PIECES[target.type].wallActions;
        state.wallIntent = PIECES[target.type].wallModes[0] || "destroy";
        syncWallActions(target);
        renderAll();
      }
      return;
    }

    // Locked to this piece after any action; before acting, allow switching
    const clickedOwn = pieceAt(r, c);
    if (clickedOwn && clickedOwn.owner === state.current && clickedOwn.id !== piece.id) {
      if (state.acted) {
        toast("Already committed to this piece this turn.");
        return;
      }
      state.selectedPieceId = clickedOwn.id;
      state.movesLeft = PIECES[clickedOwn.type].moves;
      state.wallActionsLeft = PIECES[clickedOwn.type].wallActions;
      state.wallIntent = PIECES[clickedOwn.type].wallModes[0] || "destroy";
      syncWallActions(clickedOwn);
      renderAll();
      return;
    }

    const isStep = Math.abs(piece.r - r) + Math.abs(piece.c - c) === 1;
    if (state.movesLeft > 0 && isStep && !blockedBetween(piece.r, piece.c, r, c)) {
      const occ = pieceAt(r, c);
      if (!occ || occ.owner !== piece.owner) {
        await tryMovePiece(piece, r, c);
        return;
      }
    }

    if (state.wallActionsLeft > 0 && evt) {
      const cell = cellEl(r, c);
      const edge = edgeFromClick(cell, evt.clientX, evt.clientY);
      const rect = cell.getBoundingClientRect();
      const x = (evt.clientX - rect.left) / rect.width;
      const y = (evt.clientY - rect.top) / rect.height;
      const distMap = Math.min(x, 1 - x, y, 1 - y);
      if (distMap < 0.28 && canEditWallOnCell(piece, r, c)) {
        handleWallAction(piece, r, c, edge);
        return;
      }
    }

    if (state.wallActionsLeft > 0) {
      toast("Click near a tile edge to build or destroy a wall.");
    }
  }

  function bind() {
    if (!el.picker) {
      console.error("Starhold: piece picker not found");
      return;
    }
    el.picker.addEventListener("click", (e) => {
      const btn = e.target.closest(".sh-pick");
      if (!btn || state.phase !== "army" || isCpuInControl() || cpuThinking || isCpuPlayer(state.drafting)) return;
      const type = btn.dataset.type;
      const army = state.armies[state.drafting];
      if (army.length >= ARMY_SIZE) {
        toast("Army full — remove pieces or confirm.");
        return;
      }
      army.push(type);
      renderPicker();
      renderArmySummaries();
    });

    el.picker.addEventListener("contextmenu", (e) => {
      const btn = e.target.closest(".sh-pick");
      if (!btn || state.phase !== "army" || isCpuInControl() || cpuThinking || isCpuPlayer(state.drafting)) return;
      e.preventDefault();
      const type = btn.dataset.type;
      const army = state.armies[state.drafting];
      const idx = army.lastIndexOf(type);
      if (idx >= 0) army.splice(idx, 1);
      renderPicker();
      renderArmySummaries();
    });

    el.clearArmy.addEventListener("click", () => {
      if (isCpuInControl() || cpuThinking || isCpuPlayer(state.drafting)) return;
      state.armies[state.drafting] = [];
      renderPicker();
      renderArmySummaries();
    });

    el.confirmArmy.addEventListener("click", () => {
      if (isCpuInControl() || cpuThinking || isCpuPlayer(state.drafting)) return;
      confirmArmy();
    });
    el.passReady.addEventListener("click", hidePass);

    el.deployP1.addEventListener("click", openDeployModal);
    el.deployP2.addEventListener("click", openDeployModal);
    el.deployCancel.addEventListener("click", closeDeployModal);
    el.deployClose.addEventListener("click", closeDeployModal);
    el.deployModal.addEventListener("click", (e) => {
      if (e.target === el.deployModal) closeDeployModal();
    });

    function onCancelSelection() {
      if (humanInputBlocked()) return;
      if (state.acted) {
        toast("Can't cancel after acting — use End turn.");
        return;
      }
      clearSelection();
      renderAll();
    }

    function onEndTurn() {
      if (humanInputBlocked()) return;
      if (!state.acted) return;
      finishTurn();
    }

    function onWallModeToggle() {
      if (humanInputBlocked()) return;
      const piece = state.pieces.find((p) => p.id === state.selectedPieceId);
      if (!piece) return;
      const modes = availableWallModes(piece);
      if (modes.length < 2) return;
      const i = modes.indexOf(state.wallIntent);
      state.wallIntent = modes[(i + 1) % modes.length];
      renderAll();
    }

    el.cancelP1.addEventListener("click", onCancelSelection);
    el.cancelP2.addEventListener("click", onCancelSelection);
    el.endP1.addEventListener("click", onEndTurn);
    el.endP2.addEventListener("click", onEndTurn);
    el.wallP1.addEventListener("click", onWallModeToggle);
    el.wallP2.addEventListener("click", onWallModeToggle);

    function openForfeit(pid) {
      if (state.phase !== "play" || cpuThinking || busy) return;
      if (isCpuPlayer(pid)) return;
      if (state.current !== pid) return;
      forfeitFrom = pid;
      if (el.forfeitText) {
        el.forfeitText.textContent = isSp()
          ? "This ends the match as a loss and awards the win to the CPU."
          : `This will end the game and award the win to ${PLAYERS[pid === "p1" ? "p2" : "p1"].name}.`;
      }
      if (el.forfeitModal) el.forfeitModal.hidden = false;
    }

    function closeForfeit() {
      forfeitFrom = null;
      if (el.forfeitModal) el.forfeitModal.hidden = true;
    }

    function confirmForfeit() {
      const loser = forfeitFrom;
      closeForfeit();
      if (!loser || state.phase !== "play") return;
      const winner = loser === "p1" ? "p2" : "p1";
      endGame(winner, `${PLAYERS[loser].name} forfeited.`);
    }

    if (el.forfeitP1) el.forfeitP1.addEventListener("click", () => openForfeit("p1"));
    if (el.forfeitP2) el.forfeitP2.addEventListener("click", () => openForfeit("p2"));
    if (el.forfeitCancel) el.forfeitCancel.addEventListener("click", closeForfeit);
    if (el.forfeitConfirm) el.forfeitConfirm.addEventListener("click", confirmForfeit);
    if (el.forfeitModal) {
      el.forfeitModal.addEventListener("click", (e) => {
        if (e.target === el.forfeitModal) closeForfeit();
      });
    }

    el.board.addEventListener("click", (e) => {
      const cell = e.target.closest(".sh-cell");
      if (!cell) return;
      onCellClick(+cell.dataset.r, +cell.dataset.c, e);
    });

    el.howtoBtn.addEventListener("click", () => {
      el.howto.hidden = false;
    });
    el.howtoClose.addEventListener("click", () => {
      el.howto.hidden = true;
    });
    el.howto.addEventListener("click", (e) => {
      if (e.target === el.howto) el.howto.hidden = true;
    });

    el.playAgain.addEventListener("click", () => {
      el.winner.hidden = true;
      resetGame();
    });

    window.addEventListener("resize", () => {
      if (!el.boardWrap.hidden) renderWalls();
    });
  }

  function resetGame() {
    clearTimeout(cpuTimer);
    cpuThinking = false;
    resultSaved = false;
    forfeitFrom = null;
    if (el.forfeitModal) el.forfeitModal.hidden = true;
    state = freshState();
    applyPlayerNames();
    el.winner.hidden = true;
    el.pass.hidden = true;
    closeDeployModal();
    buildBoard();
    startArmyDraft("p1");
    renderPicker();
  }

  function init() {
    cacheDom();
    applyPlayerNames();
    state = freshState();
    buildBoard();
    bind();
    startArmyDraft("p1");
    // Hard guarantee the static piece buttons are visible for human draft
    renderPicker();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
