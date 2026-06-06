import { readFileSync } from "node:fs";
import { join } from "node:path";
import { colors } from "@/lib/colors";
import { describe, expect, it } from "vitest";
import {
  TOKENS,
  hexToTriplet,
  paletteToColors,
  tripletToHex,
} from "../palette";
import { BUILTIN_THEMES, getTheme } from "../themes";

describe("palette helpers", () => {
  it("hexToTriplet parses 6-digit hex to RGB channels", () => {
    expect(hexToTriplet("#0a0a09")).toBe("10 10 9");
    expect(hexToTriplet("#ffffff")).toBe("255 255 255");
    expect(hexToTriplet("#000000")).toBe("0 0 0");
  });

  it("round-trips hex <-> triplet", () => {
    for (const hex of ["#131311", "#c9a35c", "#6dd58c", "#e87575"]) {
      expect(tripletToHex(hexToTriplet(hex))).toBe(hex);
    }
  });
});

describe("built-in themes", () => {
  it("every theme defines every token as a 6-digit hex", () => {
    for (const t of BUILTIN_THEMES) {
      for (const token of TOKENS) {
        expect(t.palette[token], `${t.id} missing ${token}`).toMatch(
          /^#[0-9a-f]{6}$/i,
        );
      }
    }
  });

  it("goldeneye palette equals the legacy lib/colors.ts export", () => {
    // The default theme must stay pixel-identical to the original palette so
    // existing users/screenshots see no change unless they switch themes.
    expect(paletteToColors(getTheme("goldeneye").palette)).toEqual(colors);
  });
});

// ── Drift guard: globals.css CSS-variable blocks must match themes.ts ────────
function varsBlock(css: string, selector: string): Record<string, string> {
  const start = css.indexOf(`${selector} {`);
  if (start === -1)
    throw new Error(`globals.css: selector not found: ${selector}`);
  const open = css.indexOf("{", start);
  const close = css.indexOf("}", open);
  const body = css.slice(open + 1, close);
  const out: Record<string, string> = {};
  const re = /--([a-z0-9-]+):\s*([^;]+);/g;
  let m: RegExpExecArray | null = re.exec(body);
  while (m !== null) {
    out[m[1]] = m[2].trim();
    m = re.exec(body);
  }
  return out;
}

describe("globals.css ↔ themes.ts parity", () => {
  const css = readFileSync(join(process.cwd(), "app/globals.css"), "utf8");

  for (const t of BUILTIN_THEMES) {
    const selector = t.id === "goldeneye" ? ":root" : `[data-theme="${t.id}"]`;
    it(`${t.id} block matches its palette`, () => {
      const declared = varsBlock(css, selector);
      for (const token of TOKENS) {
        expect(declared[token], `${selector} --${token}`).toBe(
          hexToTriplet(t.palette[token]),
        );
      }
    });
  }
});
