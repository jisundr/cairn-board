import { describe, expect, it } from "vitest";
import type { TaskCard } from "../api/types";
import { attentionLabel, BASE_TITLE, needsAttentionCount, titleForCount } from "./attention";

const card = (needs: boolean) => ({ needs_attention: needs }) as TaskCard;

describe("attention helpers", () => {
  it("counts only cards flagged needs_attention", () => {
    expect(needsAttentionCount([card(true), card(false), card(true)])).toBe(2);
    expect(needsAttentionCount(undefined)).toBe(0);
  });

  it("puts the count in the title only when above zero", () => {
    expect(titleForCount(0)).toBe(BASE_TITLE);
    expect(titleForCount(3)).toBe("(3) cairn board");
  });

  it("names the trigger phrase, else a generic label", () => {
    expect(attentionLabel("stalled on review")).toBe("stalled");
    expect(attentionLabel("needs-human: pick one")).toBe("needs-human");
    expect(attentionLabel("something else")).toBe("needs attention");
  });
});
