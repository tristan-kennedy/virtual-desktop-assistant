from dataclasses import dataclass


@dataclass(frozen=True)
class ModelBundle:
    display_name: str
    repo_id: str
    filename: str
    app_subdir: str
    n_ctx: int
    n_gpu_layers: int
    description: str


DEFAULT_MODEL_BUNDLE = ModelBundle(
    display_name="Qwen 3.5 9B",
    repo_id="unsloth/Qwen3.5-9B-GGUF",
    filename="Qwen3.5-9B-Q4_K_M.gguf",
    app_subdir="default",
    n_ctx=6144,
    n_gpu_layers=-1,
    description="Single bundled local model for Dipsy Dolphin.",
)
