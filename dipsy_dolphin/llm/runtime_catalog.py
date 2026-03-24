from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeBundle:
    display_name: str
    runtime_url: str
    cuda_url: str
    server_executable: str


DEFAULT_RUNTIME_BUNDLE = RuntimeBundle(
    display_name="llama.cpp Windows CUDA 13.1",
    runtime_url="https://github.com/ggml-org/llama.cpp/releases/download/b8468/llama-b8468-bin-win-cuda-13.1-x64.zip",
    cuda_url="https://github.com/ggml-org/llama.cpp/releases/download/b8468/cudart-llama-bin-win-cuda-13.1-x64.zip",
    server_executable="llama-server.exe",
)
