from dipsy_dolphin.llm.runtime_catalog import normalize_runtime_backend, select_runtime_bundle


def test_select_runtime_bundle_prefers_cuda_when_driver_available(monkeypatch) -> None:
    monkeypatch.setattr("dipsy_dolphin.llm.runtime_catalog._has_cuda_driver", lambda: True)

    bundle = select_runtime_bundle("auto")

    assert bundle.runtime_id == "cuda"


def test_select_runtime_bundle_prefers_vulkan_without_cuda_driver(monkeypatch) -> None:
    monkeypatch.setattr("dipsy_dolphin.llm.runtime_catalog._has_cuda_driver", lambda: False)

    bundle = select_runtime_bundle("auto")

    assert bundle.runtime_id == "vulkan"


def test_normalize_runtime_backend_rejects_unknown_values() -> None:
    assert normalize_runtime_backend("banana") == "auto"
