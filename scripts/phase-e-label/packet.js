/* scripts/phase-e-label/packet.js — Validate private packets, annotations and Unicode selections. */
const phasePacket = (() => {
  const labels = new Set(["NAME", "DOB", "PHONE", "ID", "ADDR"]);
  const noteId = /^[a-zA-Z0-9_-]{1,128}$/;
  const limit = 100 * 1024 * 1024;

  /** Read a local file as strict UTF-8 and return bytes for binding a draft to its source. */
  async function read(file) {
    if (file.size > limit) throw new Error("Tệp vượt giới hạn 100 MiB.");
    const bytes = await file.arrayBuffer();
    return {
      bytes,
      text: new TextDecoder("utf-8", { fatal: true }).decode(bytes),
    };
  }

  /** Return the exact packet SHA-256 in hexadecimal. */
  async function digest(bytes) {
    const hash = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(hash), (byte) =>
      byte.toString(16).padStart(2, "0"),
    ).join("");
  }

  /** Check a plain record has exactly the expected fields. */
  function fields(value, keys) {
    return (
      value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      Object.keys(value).length === keys.length &&
      keys.every((key) => Object.hasOwn(value, key))
    );
  }

  /** Accept only blind packets with unique opaque IDs and untouched, valid Unicode text. */
  function parse(text) {
    const lines = text.split("\n");
    if (lines.at(-1) === "") lines.pop();
    if (!lines.length) throw new Error("Gói không có ghi chú.");
    const ids = new Set();
    return lines.map((line, index) => {
      let row;
      try {
        row = JSON.parse(line);
      } catch {
        throw new Error(`JSONL lỗi ở dòng ${index + 1}.`);
      }
      if (
        !fields(row, ["note_id", "text"]) ||
        typeof row.note_id !== "string" ||
        !noteId.test(row.note_id) ||
        ids.has(row.note_id) ||
        typeof row.text !== "string" ||
        !row.text.trim() ||
        !row.text.isWellFormed() ||
        Array.from(row.text).length > 50000
      ) {
        throw new Error(
          `Ghi chú dòng ${index + 1} không đúng định dạng gói gán mù.`,
        );
      }
      ids.add(row.note_id);
      return row;
    });
  }

  /** Map textarea UTF-16 offsets, including normalized CRLF, to original code points. */
  function display(text) {
    const chars = Array.from(text);
    const boundaries = [0];
    let value = "";
    for (let index = 0; index < chars.length; index++) {
      let char = chars[index];
      if (char === "\r") {
        if (chars[index + 1] === "\n") index++;
        char = "\n";
      }
      value += char;
      if (char.length > 1) boundaries.push(null);
      boundaries.push(index + 1);
    }
    return { value, chars, boundaries };
  }

  /** Convert a textarea selection to a trimmed half-open range on the original text. */
  function range(view, selectionStart, selectionEnd) {
    let start = view.boundaries[selectionStart];
    let end = view.boundaries[selectionEnd];
    if (!Number.isInteger(start) || !Number.isInteger(end)) {
      throw new Error("Biên vùng cắt giữa ký tự Unicode.");
    }
    while (start < end && /^\s$/u.test(view.chars[start])) start++;
    while (end > start && /^\s$/u.test(view.chars[end - 1])) end--;
    if (start >= end) throw new Error("Hãy chọn một vùng có nội dung.");
    if (
      /^\p{M}$/u.test(view.chars[start]) ||
      (end < view.chars.length && /^\p{M}$/u.test(view.chars[end]))
    ) {
      throw new Error("Hãy chọn cả chữ và dấu tổ hợp.");
    }
    return { start, end };
  }

  /** Validate a note’s sorted nonoverlapping spans, returning a sorted copy. */
  function validate(text, spans) {
    if (!Array.isArray(spans) || spans.length > 2000) {
      throw new Error("Danh sách vùng không hợp lệ hoặc vượt 2.000 vùng.");
    }
    const chars = Array.from(text);
    for (const span of spans) {
      if (
        !fields(span, ["start", "end", "label"]) ||
        !labels.has(span.label) ||
        !Number.isInteger(span.start) ||
        !Number.isInteger(span.end) ||
        span.start < 0 ||
        span.end > chars.length ||
        span.start >= span.end ||
        !chars.slice(span.start, span.end).join("").trim()
      ) {
        throw new Error("Có một vùng gán nhãn không hợp lệ.");
      }
    }
    const sorted = spans.toSorted((a, b) => a.start - b.start || a.end - b.end);
    if (
      sorted.some(
        (span, index) => index > 0 && span.start < sorted[index - 1].end,
      )
    ) {
      throw new Error("Vùng chọn chồng với một vùng đã gán.");
    }
    return sorted;
  }

  /** Restore only a complete checkpoint bound to the exact current packet bytes. */
  function restore(packetHash, notes, data) {
    if (
      !fields(data, ["schema_version", "packet_sha256", "rows"]) ||
      data.schema_version !== 1 ||
      data.packet_sha256 !== packetHash ||
      !Array.isArray(data.rows) ||
      data.rows.length !== notes.length
    ) {
      throw new Error("Tệp tiến độ không thuộc gói đang mở.");
    }
    return data.rows.map((row, index) => {
      if (
        !fields(row, ["note_id", "reviewed", "entities"]) ||
        row.note_id !== notes[index].note_id ||
        typeof row.reviewed !== "boolean"
      ) {
        throw new Error("Tệp tiến độ không khớp danh sách ghi chú.");
      }
      return { ...row, entities: validate(notes[index].text, row.entities) };
    });
  }

  return { read, digest, parse, display, range, validate, restore };
})();
