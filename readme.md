# 🎤 Faster-Whisper Transcription API

[https://img.shields.io/badge/Python-3.8%252B-blue](https://img.shields.io/badge/Python-3.8%2B-blue)
[https://img.shields.io/badge/FastAPI-0.100%252B-green](https://img.shields.io/badge/FastAPI-0.100%2B-green)
https://img.shields.io/badge/License-MIT-yellow

一个基于Faster-Whisper的高性能语音转录API服务，支持批量处理和长音频智能切片并行处理。

## ✨ 特性

### 🚀 高性能转录

- **多模型支持**: 支持多种Whisper模型（tiny、base、small、medium、large）
- **硬件加速**: 支持CPU和CUDA设备，支持多种计算精度（float16、float32、int8）
- **智能缓存**: 模型自动缓存和复用，减少加载开销

### 🔧 智能音频处理

- **批量处理**: 支持多个音频文件并行转录
- **长音频优化**: 智能音频切片技术，自动将长音频分割为最优片段并行处理
- **动态并发**: 根据音频时长和系统负载自动计算最优并发数

### 🎯 专业API设计

- **RESTful接口**: 清晰的API端点设计
- **统一响应格式**: 标准化的JSON响应结构
- **实时进度**: 详细的处理日志和状态反馈
- **资源管理**: 自动清理临时文件，避免资源泄漏

## 📦 快速开始

### 安装依赖

bash

```
pip install -r requirements.txt
```

### 启动服务

bash

```
# 开发模式（带热重载）
uvicorn api.app:app --reload --host 0.0.0.0 --port 9898

# 生产模式（多工作进程）
uvicorn api.app:app --host 0.0.0.0 --port 9898 --workers 2
```

### API请求示例

**批量转录多个音频文件**:

bash

```
curl -X POST "http://localhost:9898/api/v1/transcribe-batch" \
  -F "files=@audio1.wav" \
  -F "files=@audio2.mp3" \
  -F "model_name=Systran/faster-whisper-small" \
  -F "max_concurrent=4"
```

**转录长音频文件（智能切片）**:

bash

```
curl -X POST "http://localhost:9898/api/v1/transcribe-sliced" \
  -F "file=@long_podcast.mp3" \
  -F "model_name=Systran/faster-whisper-medium" \
  -F "min_slice_length=30000" \
  -F "slice_threshold=-35"
```

## 📚 API文档

启动服务后访问以下地址查看交互式API文档：

- **Swagger UI**: http://localhost:9898/docs
- **ReDoc**: http://localhost:9898/redoc

### 主要端点

| 端点                        | 方法 | 描述               |
| :-------------------------- | :--- | :----------------- |
| `/api/v1/transcribe-batch`  | POST | 批量转录音频文件   |
| `/api/v1/transcribe-sliced` | POST | 智能切片转录长音频 |
| `/health`                   | GET  | 服务健康检查       |
| `/models`                   | GET  | 获取支持的模型列表 |
| `/config`                   | GET  | 获取服务配置信息   |

## ⚙️ 配置选项

在 `config/settings.py` 中修改配置：

python

```
# 模型配置
DEFAULT_MODEL = "Systran/faster-whisper-small"
DEFAULT_DEVICE = "cpu"  # "cpu" 或 "cuda"
DEFAULT_COMPUTE_TYPE = "int8"  # "float16", "float32", "int8"

# 并发配置
DEFAULT_MAX_CONCURRENT = 4
MAX_CONCURRENT_LIMIT = 8

# 音频切片配置
MIN_SLICE_LENGTH = 30000  # 30秒
SLICE_THRESHOLD = -40     # 静音检测阈值
```

## 🚀 性能表现

基于测试数据：

- **普通处理**: 基础耗时
- **切片并行处理**: 基础耗时 - 30秒（提升约30%）
- **支持音频格式**: WAV、MP3、M4A、FLAC、OGG等

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](https://license/) 文件了解详情。

## 🙏 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) - 语音识别模型
- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) - 高性能Whisper实现
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能Web框架

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 [Issue](https://github.com/StarryLightning/Faster-Whisper-Transcription-API/issues)

------

⭐ 如果这个项目对你有帮助，请给它一个Star！