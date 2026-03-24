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
    download_url: str
    size_bytes: int
    sha256: str


DEFAULT_MODEL_BUNDLE = ModelBundle(
    display_name="Qwen 3.5 9B",
    repo_id="unsloth/Qwen3.5-9B-GGUF",
    filename="Qwen3.5-9B-Q4_K_M.gguf",
    app_subdir="default",
    n_ctx=6144,
    n_gpu_layers=-1,
    description="Single bundled local model for Dipsy Dolphin.",
    download_url="https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/resolve/main/Qwen3.5-9B-Q4_K_M.gguf?download=1",
    size_bytes=5_680_522_464,
    sha256="03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8",
)
