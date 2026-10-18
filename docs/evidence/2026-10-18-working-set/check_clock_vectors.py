"""Independent stdlib arithmetic oracle; no Observer or Mesh imports or I/O."""

from __future__ import annotations

import json


def main():
    checked = positives = negatives = overlaps = 0
    # Model real capture points in quarter-millisecond units; the implementation
    # sees only their floored milliseconds. Wall and BOOT fractions are separate.
    for start_tick in range(400, 404):
        for elapsed_tick in range(0, 41, 5):
            sample_tick = start_tick + elapsed_tick
            for accept_delay_tick in (0, 1, 4, 13):
                upper_tick = sample_tick + accept_delay_tick
                for wall_fraction in range(4):
                    wall_tick = 4_000 + wall_fraction
                    for age_ms in (0, 1, 9, 10, 11, 40):
                        event_ms = 1_000 - age_ms
                        true_cutoff_tick = sample_tick + 40 - (wall_tick - 4 * event_ms)
                        lower = start_tick // 4 + 10 - age_ms - 1
                        upper = upper_tick // 4 + 10 - age_ms + 1
                        for now in sorted({upper_tick // 4, lower - 1, lower,
                                           upper - 1, upper, upper + 1}):
                            if now < upper_tick // 4:
                                continue
                            checked += 1
                            if now < lower:
                                # Every modeled sub-ms point in this now bucket
                                # is still strictly before the real deadline.
                                assert 4 * now + 3 < true_cutoff_tick
                                positives += 1
                            elif now >= upper:
                                assert 4 * now >= true_cutoff_tick
                                negatives += 1
                            else:
                                overlaps += 1

    translations = 0
    for sent in (100, 1_000):
        for outward in (0, 1, 75, 500):
            for inward in (0, 1, 125, 500):
                for remaining in (1, 100, 500, 2_000, 10_000):
                    for delta in (-100, 0, 1, 50, 1_000):
                        encoded = sent + outward
                        expiry = encoded + remaining
                        received = sent + outward + inward
                        translated = received + max(0, remaining - outward - inward - 100)
                        if translated <= received:
                            continue  # No current receipt can support a claim.
                        cutoff = expiry - delta
                        bounded = translated - max(0, expiry - cutoff)
                        assert bounded <= cutoff
                        assert bounded <= translated
                        translations += 1

    # An attenuated expiry is an upper bound on positive authority, NOT proof
    # that a native negative deadline has passed. This deliberately demonstrates
    # why the facade needs an admitted explicit negative decision instead.
    native_expiry, negative_cutoff, translated_expiry = 500, 400, 450
    early = translated_expiry - max(0, native_expiry - negative_cutoff)
    assert early == 350 < negative_cutoff

    print(json.dumps({
        "scope": "independent bounded arithmetic only; no runtime, native or profile acceptance",
        "flooredCaptureChecks": checked,
        "provedPositiveChecks": positives,
        "provedNegativeChecks": negatives,
        "conservativeUnknownChecks": overlaps,
        "positiveTranslationChecks": translations,
        "negativeTranslationCounterexample": {
            "nativeExpiry": native_expiry,
            "nativeNegativeCutoff": negative_cutoff,
            "translatedExpiry": translated_expiry,
            "unsafeEarlyNegative": early,
        },
        "pass": True,
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
