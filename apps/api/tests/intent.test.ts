import assert from "node:assert";
import { describe, it } from "node:test";
import { parseIntentToken } from "../src/bot/intent.js";

describe("parseIntentToken", () => {
  it("accepts exact intent tokens", () => {
    assert.strictEqual(parseIntentToken("greeting"), "greeting");
    assert.strictEqual(parseIntentToken("faq_price"), "faq_price");
    assert.strictEqual(parseIntentToken("booking_request"), "booking_request");
  });

  it("strips noise and newlines", () => {
    assert.strictEqual(parseIntentToken("  faq_hours\n"), "faq_hours");
    assert.strictEqual(parseIntentToken("escalate."), "escalate");
  });

  it("maps unknown to fallback", () => {
    assert.strictEqual(parseIntentToken("random"), "fallback");
    assert.strictEqual(parseIntentToken(""), "fallback");
  });
});
