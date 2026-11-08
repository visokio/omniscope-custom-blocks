// JSON text in the exact format of Python's json.dump(obj, f, indent=N) with its defaults
// (ensure_ascii=True, separators (",", ": ")). index.json has always been written that way, so
// keeping the format byte for byte means regenerating it never produces a noisy diff.

export function pythonJsonDump(value: unknown, indent = 4): string {
  return dump(value, indent, 0);
}

function dump(v: unknown, indent: number, depth: number): string {
  if (v === null || v === undefined) return "null";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number") {
    if (!Number.isFinite(v)) throw new Error(`cannot encode ${v}`);
    return pyNumber(v);
  }
  if (typeof v === "string") return pyString(v);
  const pad = " ".repeat(indent * (depth + 1));
  const end = " ".repeat(indent * depth);
  if (Array.isArray(v)) {
    if (v.length === 0) return "[]";
    return "[\n" + v.map((x) => pad + dump(x, indent, depth + 1)).join(",\n") + "\n" + end + "]";
  }
  if (typeof v === "object") {
    const entries = Object.entries(v as Record<string, unknown>);
    if (entries.length === 0) return "{}";
    return (
      "{\n" +
      entries.map(([k, x]) => pad + pyString(k) + ": " + dump(x, indent, depth + 1)).join(",\n") +
      "\n" + end + "}"
    );
  }
  throw new Error(`cannot encode a ${typeof v}`);
}

// Integers print as integers. JSON.parse loses the difference between 1 and 1.0, so a float that
// happens to be whole prints as an integer: the index never carries one, and the golden test would catch it.
function pyNumber(n: number): string {
  if (Number.isInteger(n)) return String(n);
  const s = String(n);
  // JavaScript writes 1e-7 where Python writes 1e-07.
  return s.replace(/e([+-])(\d)$/, "e$10$2");
}

function pyString(s: string): string {
  let out = '"';
  for (const ch of s) {
    const c = ch.codePointAt(0)!;
    if (ch === '"') out += '\\"';
    else if (ch === "\\") out += "\\\\";
    else if (ch === "\n") out += "\\n";
    else if (ch === "\r") out += "\\r";
    else if (ch === "\t") out += "\\t";
    else if (ch === "\b") out += "\\b";
    else if (ch === "\f") out += "\\f";
    else if (c < 0x20 || (c >= 0x7f && c <= 0xffff)) out += "\\u" + c.toString(16).padStart(4, "0");
    else if (c > 0xffff) {
      const v = c - 0x10000;
      out += "\\u" + (0xd800 + (v >> 10)).toString(16) + "\\u" + (0xdc00 + (v & 0x3ff)).toString(16);
    } else out += ch;
  }
  return out + '"';
}
