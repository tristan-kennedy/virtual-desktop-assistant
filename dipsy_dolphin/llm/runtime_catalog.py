from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeBundle:
    display_name: str
    runtime_url: str
    cuda_url: str
    server_executable: str
    runtime_archive_size: int
    runtime_archive_sha256: str
    runtime_extracted_size: int
    cuda_archive_size: int
    cuda_archive_sha256: str
    cuda_extracted_size: int


DEFAULT_RUNTIME_BUNDLE = RuntimeBundle(
    display_name="llama.cpp Windows CUDA 13.1",
    runtime_url="https://github.com/ggml-org/llama.cpp/releases/download/b8468/llama-b8468-bin-win-cuda-13.1-x64.zip",
    cuda_url="https://github.com/ggml-org/llama.cpp/releases/download/b8468/cudart-llama-bin-win-cuda-13.1-x64.zip",
    server_executable="llama-server.exe",
    runtime_archive_size=155_365_158,
    runtime_archive_sha256="60236c85e003cdd91f46052bb0cabfae1b2ea3a8c54e2ebd8cd9cdba799e94c9",
    runtime_extracted_size=237_263_928,
    cuda_archive_size=402_582_216,
    cuda_archive_sha256="f96935e7e385e3b2d0189239077c10fe8fd7e95690fea4afec455b1b6c7e3f18",
    cuda_extracted_size=532_803_920,
)
