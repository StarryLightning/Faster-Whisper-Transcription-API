# 🎤 Faster-Whisper Transcription API

[https://img.shields.io/badge/Python-3.8%252B-blue](https://img.shields.io/badge/Python-3.8%2B-blue)
[https://img.shields.io/badge/FastAPI-0.100%252B-green](https://img.shields.io/badge/FastAPI-0.100%2B-green)
https://img.shields.io/badge/License-MIT-yellow

一个基于Faster-Whisper和Audio Slicer的高性能语音转录API服务，支持批量处理和长音频智能切片并行处理。

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
or
python main.py

# 生产模式（使用docker部署）
docker run -d -p 9898:9898 your-image
```
⚠️docker默认配置为多核心工作站配置，请根据自己个人电脑的配置调整环境变量！！！

### API请求示例

**批量转录多个音频文件**:

bash

```
curl -X 'POST' \
  'http://localhost:9898/api/fasterwhisper/transcribe?model_name=faster-whisper-small&beam_size=5&device=cpu&compute_type=int8&auto_slice=true&consider_system_load=true' \
    -H 'accept: application/json' \
    -H 'Content-Type: multipart/form-data' \
    -F 'files=@Google_TTS–Blonde_on_Blonde-en-US-Wavenet-J.wav;type=audio/wav' \
    -F 'files=@Wikipedia_-_2025_Canadian_boycott_of_the_United_States.mp3;type=audio/mpeg'
```

**转录长音频文件（智能切片）**:

bash

```
curl -X 'POST' \
  'http://localhost:9898/api/fasterwhisper/transcribe?model_name=faster-whisper-small&beam_size=5&device=cpu&compute_type=int8&auto_slice=true&consider_system_load=true' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'files=@De-Schallplatte_2-article.ogg;type=audio/ogg'
```

## 📚 API文档

启动服务后访问以下地址查看交互式API文档：

- **Swagger UI**: http://localhost:9898/docs
- **ReDoc**: http://localhost:9898/redoc

### 主要端点

| 端点                                    | 方法 | 描述        |
|:--------------------------------------| :--- |:----------|
| `/api/fasterwhisper/transcribe-batch` | POST | 处理音频文件    |
| `/health`                             | GET  | 服务健康检查    |
| `/models`                             | GET  | 获取支持的模型列表 |
| `/config`                             | GET  | 获取服务配置信息  |

## ⚙️ 配置选项

在 `config/settings.py` 中修改配置：

【注意事项】

faster-whisper官方默认自动从站点下载模型，但由于个人网络环境或其他原因，自动下载模型并非一个方便的选择，所以请在使用时自行提前准备模型，确保本地已存放模型文件，并将模型文件夹名称填入settings.py中的SUPPORTED_MODELS配置项

示例： 
SUPPORTED_MODELS = [
    "faster-whisper-small",
    "faster-whisper-large-v3-turbo",
]

DEFAULT_MODEL = os.getenv("MODEL_NAME", "faster-whisper-small")

DEFAULT_DEVICE = os.getenv("DEVICE", "cpu")

DEFAULT_COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8")

DEFAULT_BEAM_SIZE = _int_env("BEAM_SIZE", 5)

MODELS_DIR = os.getenv("MODELS_DIR", "./Models")

模型文件下载站点：https://huggingface.co/docs/hub/models-the-hub

#

```

## 🚀 性能表现

基于测试数据：

- **1h音频普通处理**: 约18min
- **切片并行处理**: 约14min（提升约22%，吞吐量提升约28.6%）
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
- [Audio Slicer](https://github.com/openvpi/audio-slicer) - 智能音频切片工具，为长音频处理提供核心技术支持
- [Librosa](https://librosa.org/) - 音频和音乐分析库
- [PyDub](http://pydub.com/) - 音频处理库

## 📞 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 [Issue](https://github.com/StarryLightning/Faster-Whisper-Transcription-API/issues)

------

⭐ 如果这个项目对你有帮助，请给它一个Star！