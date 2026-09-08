from app.domains.architecture_recommendation import engine


def test_reference_keywords_dont_collide_within_a_pin():
    """A real bug caught in development: "Internet Edge Router" and "Perimeter Firewall
    (NGFW)" both listed bare "edge"/"internet" as keywords, so a router literally named
    "edge-rtr-01" falsely satisfied the firewall capability match via keyword substring,
    silently hiding a real missing-firewall finding. Guards against every component_type
    within a PIN sharing (or substring-overlapping) a keyword with a sibling component_type,
    which the moment it happens defeats the whole point of per-component matching."""
    pins = engine.load_pins()
    for pin in pins:
        all_keywords = [(rc.component_type, kw.lower()) for rc in pin.recommended_components for kw in rc.matches_keywords]
        for type_a, keyword_a in all_keywords:
            for type_b, keyword_b in all_keywords:
                if type_a == type_b:
                    continue
                assert keyword_a != keyword_b, f"{pin.id}: {keyword_a!r} used by both {type_a} and {type_b}"
                assert keyword_a not in keyword_b, (
                    f"{pin.id}: {type_a} keyword {keyword_a!r} is a substring of {type_b} keyword {keyword_b!r}"
                )


def test_capability_matcher_merges_across_pins():
    pins = engine.load_pins()
    firewall = engine.capability_matcher(pins, "firewall")
    assert "firewall" in firewall.matches_asset_type_codes
    # Merged from multiple PINs' firewall entries (internet_edge, data_center, branch, cloud).
    assert len(firewall.matches_keywords) > 2


def test_shortest_path_respects_max_hops():
    adjacency = {1: [2], 2: [1, 3], 3: [2, 4], 4: [3]}
    assert engine.shortest_path(adjacency, 1, 4, max_hops=3) == [1, 2, 3, 4]
    assert engine.shortest_path(adjacency, 1, 4, max_hops=2) is None


def test_shortest_path_returns_none_when_disconnected():
    adjacency = {1: [2], 2: [1], 3: []}
    assert engine.shortest_path(adjacency, 1, 3, max_hops=5) is None
