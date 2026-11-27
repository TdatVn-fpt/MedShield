/* scripts/phase-e-label/label.js — Operate the private annotation UI in browser memory. */
const elements = Object.fromEntries(
  [
    "packet",
    "draft",
    "status",
    "work",
    "previous",
    "next",
    "note-index",
    "text",
    "label",
    "add",
    "spans",
    "confirmed",
    "save",
    "export",
  ].map((id) => [id, document.getElementById(id)]),
);
let state;
let operation = 0;

/** Show status feedback without echoing note text. */
function report(message) {
  elements.status.textContent = message;
}

/** Return the label receipt for the currently displayed note. */
function currentRow() {
  return state.rows[state.index];
}

/** Render note content, positions and controls for the newly selected note. */
function showNote(index, message = "") {
  state.index = index;
  state.view = phasePacket.display(state.notes[index].text);
  elements.text.value = state.view.value;
  elements.text.setSelectionRange(0, 0);
  render(message);
}

/** Render annotations, progress and navigation without changing the current selection. */
function render(message = "") {
  const row = currentRow();
  const done = state.rows.filter((item) => item.reviewed).length;
  const count = state.rows.length;
  elements["note-index"].replaceChildren(
    ...state.rows.map((item, index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = `Ghi chú ${index + 1}${item.reviewed ? " · đã rà soát" : ""}`;
      return option;
    }),
  );
  elements["note-index"].value = String(state.index);
  elements.previous.disabled = state.index === 0;
  elements.next.disabled = state.index === count - 1;
  elements.confirmed.checked = row.reviewed;
  elements.export.disabled = done !== count;
  elements.spans.replaceChildren(...row.entities.map(createSpanRow));
  report(`${message ? `${message} ` : ""}Đã rà soát ${done}/${count} ghi chú.`);
}

/** Build a text-only span row and a button that invalidates previous review on removal. */
function createSpanRow(span, index) {
  const item = document.createElement("li");
  const value = state.view.chars.slice(span.start, span.end).join("");
  item.textContent = `${span.label} · [${span.start}, ${span.end}) · ${value}`;
  const remove = document.createElement("button");
  remove.type = "button";
  remove.textContent = `Bỏ vùng ${index + 1}`;
  remove.addEventListener("click", () => {
    const row = currentRow();
    row.entities.splice(index, 1);
    row.reviewed = false;
    render("Đã bỏ vùng. Hãy rà soát lại ghi chú.");
    elements.add.focus();
  });
  item.append(remove);
  return item;
}

/** Load a strict blind packet and atomically replace browser state after validation. */
async function loadPacket() {
  const file = elements.packet.files[0];
  elements.packet.value = "";
  if (!file) return;
  if (
    state?.rows.some((row) => row.reviewed || row.entities.length) &&
    !confirm(
      "Mở gói khác sẽ thay tiến độ đang có trong tab. Bạn đã lưu tiến độ chưa?",
    )
  ) {
    return;
  }
  const request = ++operation;
  try {
    const source = await phasePacket.read(file);
    const notes = phasePacket.parse(source.text);
    const hash = await phasePacket.digest(source.bytes);
    if (request !== operation) return;
    state = {
      notes,
      hash,
      rows: notes.map(({ note_id }) => ({
        note_id,
        entities: [],
        reviewed: false,
      })),
    };
    elements.draft.disabled = false;
    elements.work.hidden = false;
    showNote(0, "Đã mở gói gán mù.");
  } catch (error) {
    if (request === operation)
      report(
        error instanceof TypeError ? "Không thể đọc gói UTF-8." : error.message,
      );
  }
}

/** Load a checkpoint for the same exact blind packet. */
async function loadDraft() {
  const file = elements.draft.files[0];
  elements.draft.value = "";
  if (!file || !state) return;
  const request = ++operation;
  try {
    const source = await phasePacket.read(file);
    if (request !== operation) return;
    let data;
    try {
      data = JSON.parse(source.text);
    } catch {
      throw new Error("Tệp tiến độ không phải JSON hợp lệ.");
    }
    state.rows = phasePacket.restore(state.hash, state.notes, data);
    showNote(
      Math.max(
        0,
        state.rows.findIndex((row) => !row.reviewed),
      ),
      "Đã khôi phục tiến độ.",
    );
  } catch (error) {
    if (request === operation)
      report(
        error instanceof TypeError
          ? "Không thể đọc tiến độ UTF-8."
          : error.message,
      );
  }
}

/** Insert a nonoverlapping source span and require the annotator to review the note again. */
function addSelection() {
  try {
    const row = currentRow();
    const span = phasePacket.range(
      state.view,
      elements.text.selectionStart,
      elements.text.selectionEnd,
    );
    row.entities = phasePacket.validate(state.notes[state.index].text, [
      ...row.entities,
      { ...span, label: elements.label.value },
    ]);
    row.reviewed = false;
    render("Đã thêm vùng.");
  } catch (error) {
    report(error.message);
  }
}

/** Download an explicit draft or receipt without writing to browser storage. */
function download(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

elements.packet.addEventListener("change", loadPacket);
elements.draft.addEventListener("change", loadDraft);
elements.previous.addEventListener("click", () => showNote(state.index - 1));
elements.next.addEventListener("click", () => showNote(state.index + 1));
elements["note-index"].addEventListener("change", () =>
  showNote(Number(elements["note-index"].value)),
);
elements.add.addEventListener("click", addSelection);
elements.confirmed.addEventListener("change", () => {
  currentRow().reviewed = elements.confirmed.checked;
  render();
});
elements.save.addEventListener("click", () => {
  download(
    "phase-e-tien-do.json",
    JSON.stringify({
      schema_version: 1,
      packet_sha256: state.hash,
      rows: state.rows,
    }),
    "application/json",
  );
});
elements.export.addEventListener("click", () => {
  if (state.rows.some((row) => !row.reviewed)) return;
  const text = state.rows
    .map(({ note_id, entities }) => JSON.stringify({ note_id, entities }))
    .join("\n");
  download("phase-e-nhan.jsonl", `${text}\n`, "application/x-ndjson");
});
