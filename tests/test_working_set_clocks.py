"""Bounded accepted-sample clock authority for working-set recency."""

import unittest
from dataclasses import replace
from uuid import UUID

from agent_observer.working_set_clocks import WorkingSetClocks
from agent_observer.working_set_policy import SampleClock

SERVICE_ID = "00000000-0000-4000-8000-000000000001"
BOOT_ID = "00000000-0000-4000-8000-000000000002"
CLOCK_DOMAIN = "linux-clock-boottime"
PROVIDER = "codex"
NAMESPACE = "scope-a"
CONTEXT_GENERATION = 7
_MAX_SAFE_INTEGER = 2**53 - 1


def sample_id(number):
    return str(UUID(int=number))


def clock(
    *,
    number=3,
    origin_component="history",
    service_id=SERVICE_ID,
    boot_id=BOOT_ID,
    clock_domain=CLOCK_DOMAIN,
    provider=PROVIDER,
    namespace=NAMESPACE,
    context_generation=CONTEXT_GENERATION,
    lower=100,
    wall=10_000,
    upper=100,
):
    return SampleClock(
        sample_id=sample_id(number),
        origin_component=origin_component,
        service_id=service_id,
        provider=provider,
        namespace=namespace,
        context_generation=context_generation,
        boot_id=boot_id,
        clock_domain=clock_domain,
        lower_boottime_ms=lower,
        wall_ms=wall,
        upper_boottime_ms=upper,
    )


def owner():
    return WorkingSetClocks(SERVICE_ID, BOOT_ID, CLOCK_DOMAIN)


def receipt(component, accepted, sample_clock, *, health="current", expires=None):
    if expires is None:
        expires = sample_clock.lower_boottime_ms + 10_000
    return {
        "name": component,
        "health": health,
        "accepted": accepted,
        "sampledBoottimeMs": sample_clock.lower_boottime_ms,
        "expiresBoottimeMs": expires,
    }


def source(sample_clock, *receipts):
    return {
        "provider": sample_clock.provider,
        "namespace": sample_clock.namespace,
        "contextGeneration": sample_clock.context_generation,
        "components": list(receipts),
    }


def support(component, accepted, sample_clock, *, expires=None):
    if expires is None:
        expires = sample_clock.lower_boottime_ms + 10_000
    return {
        "serviceId": sample_clock.service_id,
        "provider": sample_clock.provider,
        "namespace": sample_clock.namespace,
        "contextGeneration": sample_clock.context_generation,
        "component": component,
        "accepted": accepted,
        "sampledBoottimeMs": sample_clock.lower_boottime_ms,
        "expiresBoottimeMs": expires,
    }


class WorkingSetClocksTest(unittest.TestCase):
    def test_constructor_requires_a_valid_clock_incarnation(self):
        for service_id, boot_id, clock_domain in (
            ("not-a-uuid", BOOT_ID, CLOCK_DOMAIN),
            (SERVICE_ID, "not-a-uuid", CLOCK_DOMAIN),
            (SERVICE_ID, BOOT_ID, ""),
            (SERVICE_ID, BOOT_ID, "x" * 129),
        ):
            with self.subTest(service_id=service_id, boot_id=boot_id, clock_domain=clock_domain):
                with self.assertRaisesRegex(ValueError, "working_set_clock_incarnation_invalid"):
                    WorkingSetClocks(service_id, boot_id, clock_domain)

    def test_runtime_and_history_can_bind_the_same_original_sample(self):
        store = owner()
        sample = clock(number=3, origin_component="history")
        store.accept(sample, component="history", accepted=2)
        before = store.floor, store.ceiling, store.generation, store._acceptance_order

        store.accept(sample, component="runtime", accepted=5)

        self.assertEqual(
            (store.floor, store.ceiling, store.generation, store._acceptance_order), before
        )
        current = source(
            sample,
            receipt("runtime", 5, sample),
            receipt("history", 2, sample),
        )
        exported = store.export(current)
        self.assertEqual([entry["component"] for entry in exported], ["history", "runtime"])
        for entry in exported:
            self.assertEqual(
                entry,
                {
                    "component": entry["component"],
                    "accepted": 2 if entry["component"] == "history" else 5,
                    "sampleId": sample.sample_id,
                    "originComponent": "history",
                    "sampledBoottimeMs": 100,
                    "wallMs": 10_000,
                    "acceptedBoottimeMs": 100,
                },
            )
        self.assertEqual(
            store.get(support("history", 2, sample), current, sample_id=sample.sample_id),
            sample,
        )
        self.assertEqual(
            store.get(support("runtime", 5, sample), current, sample_id=sample.sample_id),
            sample,
        )

    def test_get_requires_current_exact_support_counter_context_and_sample(self):
        store = owner()
        sample = clock(number=4, origin_component="runtime")
        store.accept(sample, component="runtime", accepted=8)
        current = source(sample, receipt("runtime", 8, sample))
        exact = support("runtime", 8, sample)

        self.assertEqual(store.get(exact, current, sample_id=sample.sample_id), sample)
        self.assertIsNone(store.get(exact, current, sample_id=sample_id(5)))
        self.assertIsNone(
            store.get(support("runtime", 7, sample), current, sample_id=sample.sample_id)
        )
        self.assertIsNone(
            store.get(
                support("runtime", 8, sample, expires=9_000),
                current,
                sample_id=sample.sample_id,
            )
        )
        unsafe_expiry = _MAX_SAFE_INTEGER + 1
        self.assertIsNone(
            store.get(
                support("runtime", 8, sample, expires=unsafe_expiry),
                source(sample, receipt("runtime", 8, sample, expires=unsafe_expiry)),
                sample_id=sample.sample_id,
            )
        )
        self.assertIsNone(
            store.get(
                exact,
                {**current, "namespace": "scope-b"},
                sample_id=sample.sample_id,
            )
        )
        self.assertIsNone(store.get(exact, current, sample_id=None))
        self.assertIsNone(store.get(exact, None, sample_id=sample.sample_id))
        self.assertEqual(store.export(None), [])
        self.assertEqual(
            store.export({**current, "contextGeneration": True}), []
        )
        too_many_components = source(
            sample,
            receipt("runtime", 8, sample),
            receipt("history", 1, sample),
            receipt("runtime", 8, sample),
        )
        self.assertIsNone(
            store.get(exact, too_many_components, sample_id=sample.sample_id)
        )
        self.assertEqual(store.export(too_many_components), [])
        mismatched_current = source(sample, receipt("runtime", 7, sample))
        self.assertEqual(store.export(mismatched_current), [])

    def test_failed_accepts_leave_all_clock_authority_unchanged(self):
        store = owner()
        baseline = clock(number=6, origin_component="runtime")
        store.accept(baseline, component="runtime", accepted=5)
        current = source(baseline, receipt("runtime", 5, baseline))
        before = (
            store.floor,
            store.ceiling,
            store.generation,
            store._acceptance_order,
            store.last_discontinuity,
            store.export(current),
        )

        invalid_inputs = (
            (baseline, "runtime", True),
            (baseline, "unknown", 6),
            (replace(baseline, boot_id=sample_id(99)), "runtime", 6),
            (baseline, "runtime", 4),
            (replace(baseline, sample_id=sample_id(7)), "runtime", 5),
            (baseline, "runtime", 6),
            (replace(baseline, lower_boottime_ms=101), "runtime", 6),
            (replace(baseline, lower_boottime_ms=True), "runtime", 6),
            (replace(baseline, wall_ms=True), "runtime", 6),
            (replace(baseline, wall_ms=4_000_000_000_001), "runtime", 6),
            (replace(baseline, context_generation=True), "runtime", 6),
            (replace(baseline, sample_id="not-a-uuid"), "runtime", 6),
            (replace(baseline, namespace="n" * 129), "runtime", 6),
            (replace(baseline, upper_boottime_ms=_MAX_SAFE_INTEGER + 1), "runtime", 6),
            (
                replace(
                    baseline,
                    lower_boottime_ms=_MAX_SAFE_INTEGER,
                    upper_boottime_ms=_MAX_SAFE_INTEGER,
                    wall_ms=0,
                    sample_id=sample_id(8),
                ),
                "runtime",
                6,
            ),
            (replace(baseline, origin_component=[]), "runtime", 6),
        )
        for candidate, component, accepted in invalid_inputs:
            with self.subTest(candidate=candidate, component=component, accepted=accepted):
                with self.assertRaises(ValueError):
                    store.accept(candidate, component=component, accepted=accepted)
                self.assertEqual(
                    (
                        store.floor,
                        store.ceiling,
                        store.generation,
                        store._acceptance_order,
                        store.last_discontinuity,
                        store.export(current),
                    ),
                    before,
                )

    def test_global_ceiling_survives_context_retirement_and_wide_brackets(self):
        store = owner()
        first = clock(number=10, lower=100, wall=10_000, upper=100)
        store.accept(first, component="runtime", accepted=1)
        first_ceiling = first.wall_ms - first.lower_boottime_ms + 1
        first_floor = first.wall_ms - first.upper_boottime_ms - 1
        self.assertEqual(store.floor, first_floor)
        self.assertEqual(store.ceiling, first_ceiling)

        second = clock(
            number=11,
            namespace="scope-b",
            lower=5_000,
            wall=10_000,
            upper=9_990,
        )
        store.accept(second, component="runtime", accepted=1)
        self.assertEqual(store.floor, 9)
        self.assertEqual(store.ceiling, first_ceiling)
        self.assertEqual(store.generation, 1)
        self.assertEqual(store.export(source(first, receipt("runtime", 1, first))), [])
        self.assertEqual(len(store.export(source(second, receipt("runtime", 1, second)))), 1)

        third = clock(
            number=12,
            namespace="scope-b",
            lower=0,
            wall=10_000,
            upper=9_990,
        )
        store.accept(third, component="runtime", accepted=2)
        self.assertEqual(store.floor, 9)
        self.assertEqual(store.ceiling, 10_001)
        self.assertGreaterEqual(store.ceiling, first_ceiling)
        self.assertEqual(store.generation, 1)

        incident = store.last_discontinuity
        fourth = clock(
            number=13,
            namespace="scope-c",
            lower=0,
            wall=10_000,
            upper=9_990,
        )
        store.accept(fourth, component="runtime", accepted=1)
        self.assertEqual(store.last_discontinuity, incident)

    def test_discontinuity_epoch_advances_once_per_distinct_sample(self):
        store = owner()
        first = clock(number=20, lower=100, wall=10_000, upper=100)
        store.accept(first, component="runtime", accepted=1)
        self.assertEqual(store.generation, 0)
        self.assertEqual(store._acceptance_order, 1)
        self.assertIsNone(store.last_discontinuity)

        second = clock(number=21, lower=100, wall=20_000, upper=100)
        store.accept(second, component="runtime", accepted=2)
        self.assertEqual(store.generation, 1)
        self.assertEqual(store._acceptance_order, 2)
        incident = store.last_discontinuity
        self.assertEqual(incident["generation"], 1)
        self.assertEqual(incident["oldAcceptanceOrder"], 1)
        self.assertEqual(incident["newAcceptanceOrder"], 2)
        self.assertEqual(incident["serviceId"], SERVICE_ID)
        self.assertEqual(incident["bootId"], BOOT_ID)
        self.assertEqual(incident["clockDomain"], CLOCK_DOMAIN)
        self.assertEqual(incident["old"]["sampleId"], first.sample_id)
        self.assertEqual(incident["new"]["sampleId"], second.sample_id)
        self.assertEqual(incident["old"]["offsetIntervalMs"], [9_899, 9_901])
        self.assertEqual(incident["new"]["offsetIntervalMs"], [19_899, 19_901])

        store.accept(second, component="history", accepted=1)
        store.accept(second, component="history", accepted=1)
        self.assertEqual(store.generation, 1)
        self.assertEqual(store._acceptance_order, 2)
        self.assertEqual(store.last_discontinuity, incident)

        third = clock(number=22, lower=100, wall=30_000, upper=100)
        store.accept(third, component="runtime", accepted=3)
        self.assertEqual(store.generation, 2)
        self.assertEqual(store._acceptance_order, 3)
        self.assertEqual(store.last_discontinuity["oldAcceptanceOrder"], 2)
        self.assertEqual(store.last_discontinuity["newAcceptanceOrder"], 3)

    def test_floor_is_conservative_and_last_incident_read_is_detached(self):
        store = owner()
        baseline = clock(number=25, lower=100, wall=10_000, upper=100)
        store.accept(baseline, component="runtime", accepted=1)
        baseline_floor, baseline_ceiling = store.floor, store.ceiling

        backstep = clock(number=26, lower=5_000, wall=10_000, upper=5_000)
        store.accept(backstep, component="runtime", accepted=2)
        self.assertLess(store.floor, baseline_floor)
        self.assertEqual(store.ceiling, baseline_ceiling)
        incident = store.last_discontinuity
        incident["new"]["offsetIntervalMs"][0] = 1
        incident["old"]["sampleId"] = sample_id(99)
        self.assertEqual(store.last_discontinuity["old"]["sampleId"], baseline.sample_id)
        self.assertNotEqual(store.last_discontinuity["new"]["offsetIntervalMs"][0], 1)

    def test_reads_and_exports_are_detached_and_do_not_mutate_state(self):
        store = owner()
        input_clock = clock(number=30, origin_component="runtime")
        expected_clock = replace(input_clock)
        store.accept(input_clock, component="runtime", accepted=1)
        current = source(input_clock, receipt("runtime", 1, input_clock))
        exact = support("runtime", 1, input_clock)
        before = (
            store.floor,
            store.ceiling,
            store.generation,
            store._acceptance_order,
            store.last_discontinuity,
        )

        object.__setattr__(input_clock, "wall_ms", 1)
        self.assertEqual(store.get(exact, current, sample_id=expected_clock.sample_id), expected_clock)
        first_export = store.export(current)
        first_export[0]["sampleId"] = sample_id(31)
        first_export.append({"untrusted": True})
        returned_clock = store.get(exact, current, sample_id=expected_clock.sample_id)
        object.__setattr__(returned_clock, "wall_ms", 1)

        self.assertEqual(store.get(exact, current, sample_id=expected_clock.sample_id), expected_clock)
        self.assertEqual(store.export(current), [
            {
                "component": "runtime",
                "accepted": 1,
                "sampleId": expected_clock.sample_id,
                "originComponent": "runtime",
                "sampledBoottimeMs": expected_clock.lower_boottime_ms,
                "wallMs": expected_clock.wall_ms,
                "acceptedBoottimeMs": expected_clock.upper_boottime_ms,
            }
        ])
        self.assertEqual(
            (
                store.floor,
                store.ceiling,
                store.generation,
                store._acceptance_order,
                store.last_discontinuity,
            ),
            before,
        )

    def test_repeated_accepts_keep_only_current_bounded_bindings(self):
        store = owner()
        latest = None
        for accepted in range(1, 101):
            latest = clock(
                number=1_000 + accepted,
                origin_component="runtime",
                lower=100 + accepted,
                wall=10_000 + accepted,
                upper=100 + accepted,
            )
            store.accept(latest, component="runtime", accepted=accepted)

        current = source(latest, receipt("runtime", 100, latest))
        self.assertEqual(len(store._bindings), 1)
        self.assertEqual(len(store.export(current)), 1)
        self.assertEqual(store.export(current)[0]["sampleId"], latest.sample_id)
        self.assertEqual(store.ceiling, 9_901)
        self.assertEqual(store.floor, 9_899)
        self.assertEqual(store.generation, 0)
        self.assertEqual(store._acceptance_order, 100)


if __name__ == "__main__":
    unittest.main()
